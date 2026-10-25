#!/usr/bin/env python3
"""Named-cause, read-only preflight for container and native NInfer routes.

Run on the inference host before starting its lane. --offline performs only local
file/profile checks, never Docker, WSL, GPU or network probes. --running checks an
already-started loopback route rather than requiring the port to be free.
Container staging uses an ephemeral --pull=never container and read-only mounts;
no existing container is started/stopped. Native --profile and --release-spec are
server-config.json and release-spec.json from the verified native package.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import socket
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(argv):
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=45)
    # Windows wsl.exe can emit UTF-16LE even when redirected; never publish raw output.
    encoding = "utf-16le" if b"\x00" in result.stdout else "utf-8-sig"
    if result.returncode:
        raise RuntimeError("probe command failed")
    return result.stdout.decode(encoding, errors="replace").strip()


def powershell(source):
    return run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", source])


def thresholds(profile, spec=None):
    host = profile.get("runtime_host", {})
    arguments = profile.get("server", {}).get("arguments", [])
    kv = (int(arguments[arguments.index("--host-kv-mib") + 1]) if "--host-kv-mib" in arguments
          else profile.get("context_cache", {}).get("host_kv_mib", 0))
    return {"ram_total_mib": host.get("minimum_runtime_memory_mib", 0),
            "ram_free_mib": host.get("minimum_free_memory_mib", kv),
            "vram_total_mib": host.get("minimum_vram_mib", 0),
            "vram_free_mib": host.get("minimum_free_vram_mib", 0),
            # Native installer requires Spec.gpu.minimum_driver_major. Container profiles
            # can declare a higher floor; 580 is the CUDA 13 major compatibility floor.
            "driver_major": (spec or {}).get("gpu", {}).get("minimum_driver_major",
                             host.get("minimum_driver_major", 580))}


def assess_gpu(rows, expected_name, uuid, limits, running=False):
    matches = [row for row in rows if row["name"] == expected_name and (not uuid or row["uuid"] == uuid)]
    if len(matches) != 1:
        return [("gpu_selection", False, "no unique GPU matches the lane and optional UUID",
                 "Select the lane GPU with --gpu-uuid; do not hide devices with CUDA_VISIBLE_DEVICES.", None)]
    row = matches[0]
    checks = [("driver_floor", int(row["driver"].split(".")[0]) >= limits["driver_major"],
               "NVIDIA driver is older than the profile/toolkit floor", "Update the host NVIDIA driver, then restart WSL/Docker if used.",
               {"observed": row["driver"], "minimum_major": limits["driver_major"]})]
    for key, column in (("vram_total_mib", "total"), ("vram_free_mib", "free")):
        floor = limits[key]
        if floor and not (running and key == "vram_free_mib"):
            checks.append((key, row[column] >= floor, "GPU memory is below the profile floor",
                           "Release other GPU workloads with their owner's approval; do not reduce the qualified profile.",
                           {"observed_mib": row[column], "minimum_mib": floor}))
    checks.append(("gpu_memory_observed", True, "", "", {"total_mib": row["total"], "free_mib": row["free"]}))
    return checks


def parse_gpu(text):
    return [{"uuid": row[0].strip(), "name": row[1].strip(), "driver": row[2].strip(),
             "total": float(row[3]), "free": float(row[4])}
            for row in csv.reader(text.splitlines()) if len(row) == 5]


def memory_info(text):
    fields = dict(re.findall(r"^(MemTotal|MemAvailable):\s+(\d+)\s+kB", text, re.MULTILINE))
    return {"total": int(fields["MemTotal"]) // 1024, "free": int(fields["MemAvailable"]) // 1024}


def bearer_private(path):
    if path.is_symlink() or not path.is_file() or not path.stat().st_size:
        return False
    if os.name != "nt":
        info = path.stat()
        return info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) & 0o077 == 0
    # Use SIDs, not localized account names. Permit owner, SYSTEM and Administrators only,
    # and reject inherited access; the native state protector follows this ACL boundary.
    quoted = str(path.resolve()).replace("'", "''")
    result = powershell("$a=Get-Acl -LiteralPath '" + quoted + "'; "
        "$owner=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value; "
        "$bad=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | "
        "Where-Object {$_.AccessControlType -eq 'Allow' -and ($_.IsInherited -or "
        "($_.IdentityReference.Value -notin @($owner,'S-1-5-18','S-1-5-32-544')))}); "
        "ConvertTo-Json -Compress ($bad.Count -eq 0 -and $a.AreAccessRulesProtected)")
    return json.loads(result) is True


def listener_addresses(port):
    if os.name == "nt":
        text = powershell("ConvertTo-Json -Compress -InputObject @(Get-NetTCPConnection -State Listen "
                          f"-LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty LocalAddress)")
        return json.loads(text)
    if platform.system() == "Linux":
        text = run(["ss", "-H", "-ltn"])
        return [parts[3].rsplit(":", 1)[0].strip("[]") for line in text.splitlines()
                if len(parts := line.split()) >= 4 and parts[3].rsplit(":", 1)[-1] == str(port)]
    # macOS is useful for checking the client-side loopback/tunnel, not runtime qualification.
    result = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fn"],
                            capture_output=True, text=True, timeout=15)
    if result.returncode not in (0, 1):
        raise RuntimeError("listener inventory failed")
    return [line[1:].rsplit(":", 1)[0].strip("[]") for line in result.stdout.splitlines() if line.startswith("n")]


def loopback_only(addresses):
    try:
        return all(ipaddress.ip_address(value).is_loopback for value in addresses)
    except ValueError:
        return False


def inspect_network(document, port):
    host = document.get("HostConfig", {})
    mappings = host.get("PortBindings") or {}
    bindings = [binding for group in mappings.values() for binding in (group or [])
                if binding.get("HostPort") == str(port)]
    return (host.get("NetworkMode") != "host" and bool(bindings)
            and all(binding.get("HostIp") == "127.0.0.1" for binding in bindings))


def pinned_client(manifest_path, platform_id):
    manifest = load(manifest_path)
    omp = manifest["components"]["omp"]
    if omp.get("platform") == platform_id:
        return omp["binary_sha256"]
    # The release's descriptor contains all three stock assets, not just its primary one.
    descriptor = load(manifest_path.parent / "qualification/client-components.json")
    return descriptor["platforms"][platform_id]["binary_sha256"]


def diagnose(args):
    checks = []
    def add(name, passed, cause, remedy, evidence=None):
        checks.append({"name": name, "status": "pass" if passed else "fail",
                       "cause": "" if passed else cause, "remediation": "" if passed else remedy,
                       **({"evidence": evidence} if evidence is not None else {})})
    def skip(name, reason):
        checks.append({"name": name, "status": "skipped", "cause": reason, "remediation": ""})
    def attempt(name, operation, remedy):
        try:
            return operation()
        except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError):
            add(name, False, "probe unavailable or returned invalid data", remedy)
            return None
    manifest_path = args.manifest.resolve()
    manifest = load(manifest_path)
    native = args.lane != "rtx5090"
    profile_path = args.profile or (manifest_path.parent / manifest["product"]["profile"])
    if native and not args.profile:
        add("native_profile", False, "native server-config.json was not supplied",
            "Pass --profile and --release-spec from the verified native package.")
        profile = {}
    else:
        profile = load(profile_path)
    spec = load(args.release_spec) if args.release_spec else None
    if native:
        add("native_spec", bool(spec and spec.get("lane") == args.lane), "native release-spec.json is missing or belongs to another lane",
            "Pass the selected native package's --release-spec; do not substitute the container profile.")
    limits = thresholds(profile, spec)
    port = 18082 if native else 18089
    listen = profile.get("listen", {}) if native else profile.get("transport", {})
    configured_host = listen.get("host" if native else "runtime_bind_host")
    configured_port = listen.get("port" if native else "runtime_port")
    add("loopback_profile", configured_host == "127.0.0.1" and configured_port == port,
        "profile is not bound to the documented loopback port",
        f"Use 127.0.0.1:{port} from the pinned lane profile; do not publish on 0.0.0.0.")
    if not native:
        server = profile.get("server", {})
        add("docker_network_mode", server.get("container_network_mode") == "bridge"
            and server.get("published_bind_host") == "127.0.0.1" and server.get("published_port") == port,
            "Docker host networking or a non-loopback publication bypasses the documented route (issue #15)",
            "Use bridge networking with -p 127.0.0.1:18089:8080; --network host targets the Docker VM, not Windows.")
    model = manifest["components"].get("native_model", manifest["components"]["model"]) if native else manifest["components"]["model"]
    if args.model:
        actual_bytes = attempt("model_file", lambda: args.model.stat().st_size,
                               "Stage the exact lane model from its pinned release URL.")
        if actual_bytes is not None:
            add("model_bytes", args.model.is_file() and actual_bytes == model["artifact_bytes"], "model file has the wrong byte count",
                "Resume/re-download the pinned artifact for this lane; container and native models differ.",
                {"observed": actual_bytes, "expected": model["artifact_bytes"]})
        if args.hash_model:
            actual = attempt("model_sha256", lambda: digest(args.model), "Make the staged model readable, then retry --hash-model.")
            if actual:
                add("model_sha256", actual == model["artifact_sha256"], "model SHA-256 differs from the pinned release",
                    "Replace only the failed model with the lane's pinned artifact.", {"observed": actual, "expected": model["artifact_sha256"]})
        else:
            skip("model_sha256", "opt-in full model hashing; pass --hash-model")
    elif args.offline:
        skip("model_file", "offline: no model supplied")
    else:
        add("model_file", False, "model file was not supplied", "Pass --model pointing at the staged lane artifact.")
    if args.key_file:
        private = attempt("bearer_permissions", lambda: bearer_private(args.key_file), "Make the bearer file readable only by its owner (native: protected owner/SYSTEM/Administrators ACL).")
        if private is not None:
            add("bearer_permissions", private, "bearer file is empty, a symlink, not owner-owned, or grants other access",
                "POSIX: chmod 600 on an owner-owned file; Windows: use the native Protect-StateRoot.ps1 ACL procedure.")
    elif args.offline:
        skip("bearer_permissions", "offline: no bearer file supplied")
    else:
        add("bearer_permissions", False, "bearer file was not supplied", "Pass --key-file; never paste the token into a command or receipt.")
    if args.omp:
        identity = attempt("omp_hash", lambda: (digest(args.omp), pinned_client(manifest_path, args.client_platform)),
                           "Install the exact stock client from the selected release and select --client-platform.")
        if identity:
            add("omp_hash", identity[0] == identity[1], "OMP binary SHA-256 differs from the pinned release",
                "Reinstall the checksummed stock binary; omp update or a Homebrew binary is not the pinned asset.",
                {"observed": identity[0], "expected": identity[1]})
    elif args.offline:
        skip("omp_hash", "offline: no OMP binary supplied")
    else:
        add("omp_hash", False, "OMP binary was not supplied", "Pass --omp and --client-platform for the installed stock binary.")
    if args.offline:
        for name in ("docker_wsl" if not native else "native_host", "driver_floor", "memory", "loopback_listener"):
            skip(name, "offline: hardware/network commands disabled")
    else:
        memory = None
        gpu_rows = None
        if native:
            add("native_host", os.name == "nt", "native lane requires Windows", "Run doctor on the native Windows inference host.")
            if os.name == "nt":
                memory = attempt("ram_probe", lambda: json.loads(powershell("$m=Get-CimInstance Win32_OperatingSystem; "
                    "@{total=[math]::Floor($m.TotalVisibleMemorySize/1024);free=[math]::Floor($m.FreePhysicalMemory/1024)}|ConvertTo-Json -Compress")),
                    "Allow local CIM queries and run on the inference host.")
                gpu_rows = attempt("gpu_probe", lambda: parse_gpu(run(["nvidia-smi", "--query-gpu=uuid,name,driver_version,memory.total,memory.free", "--format=csv,noheader,nounits"])),
                                   "Install the NVIDIA driver and expose nvidia-smi on PATH.")
        else:
            info = attempt("docker_reachability", lambda: json.loads(run(["docker", "info", "--format", "{{json .}}"])),
                           "Start Docker Desktop with WSL2/Linux containers and enable integration for the model's WSL distro.")
            if info is not None:
                add("docker_reachability", info.get("OSType") == "linux", "Docker is not serving Linux containers", "Switch Docker Desktop to Linux containers/WSL2.")
            if os.name == "nt":
                wsl = attempt("wsl2_reachability", lambda: run(["wsl.exe", "--list", "--verbose"]),
                              "Enable WSL2, start the model-owning distro, then restart Docker Desktop while it is running.")
                if wsl is not None:
                    add("wsl2_reachability", bool(re.search(r"\s2\s*$", wsl, re.MULTILINE)), "no WSL2 distro is visible",
                        "Convert the model-owning distro to WSL2 and enable Docker integration.")
            elif "microsoft" in platform.release().lower():
                add("wsl2_reachability", "wsl2" in platform.release().lower(), "WSL kernel is not WSL2",
                    "Convert this distro to WSL2, then enable Docker integration.")
            if args.container:
                inspected = attempt("container_network", lambda: json.loads(run(["docker", "inspect", args.container]))[0],
                                    "Select the documented container name; inspect ownership before changing anything.")
                if inspected:
                    add("container_network", inspect_network(inspected, port), "container uses host networking or lacks the exact loopback publication (issue #15)",
                        "Recreate only your owned lane via start-ninfer.sh using bridge and 127.0.0.1:18089:8080.")
            image = manifest["components"]["ninfer"]["oci_reference"]
            if info is not None and info.get("OSType") == "linux":
                base = ["docker", "run", "--rm", "--pull=never", "--network", "none", "--read-only"]
                gpu_rows = attempt("docker_gpu", lambda: parse_gpu(run([*base, "--gpus", "all", "--entrypoint", "nvidia-smi", image,
                    "--query-gpu=uuid,name,driver_version,memory.total,memory.free", "--format=csv,noheader,nounits"])),
                    "Pull the pinned release image explicitly and enable NVIDIA Container Toolkit/Docker GPU support.")
                mounts = []
                if args.model and args.key_file and args.model.is_file() and args.key_file.is_file():
                    for source, target in ((args.model, "/model"), (args.key_file, "/key")):
                        mounts += ["--mount", f"type=bind,source={source.resolve()},target={target},readonly"]
                script = 'cat /proc/meminfo; '
                if mounts:
                    script += 'printf "model_bytes="; wc -c < /model; printf "key_bytes="; wc -c < /key'
                staged = attempt("docker_staging", lambda: run([*base, *mounts, "--entrypoint", "/bin/sh", image, "-c", script]),
                                 "Start the WSL distro owning model/key paths, restart Docker Desktop while it runs, and retry the read-only staging probe.")
                if staged:
                    memory = attempt("ram_probe", lambda: memory_info(staged), "Make /proc/meminfo readable inside the pinned image.")
                    if mounts:
                        counts = dict(re.findall(r"(model_bytes|key_bytes)=\s*(\d+)", staged))
                        add("docker_bind_mounts", int(counts.get("model_bytes", -1)) == args.model.stat().st_size
                            and int(counts.get("key_bytes", 0)) == args.key_file.stat().st_size,
                            "Docker cannot see the host's staged model/key bytes", "Start the owning WSL distro and restart Docker Desktop; do not reuse stale bind mounts.")
        if gpu_rows is not None:
            expected = (spec or {}).get("gpu", {}).get("name", profile.get("runtime_host", {}).get("gpu"))
            for row in assess_gpu(gpu_rows, expected, args.gpu_uuid, limits, args.running):
                add(*row)
            if not limits["vram_free_mib"]:
                skip("vram_free_floor", "profile declares no free-VRAM floor; observed free memory is reported, not a fabricated threshold")
        if memory is not None:
            for name, column in (("ram_total_mib", "total"), ("ram_free_mib", "free")):
                floor = limits[name]
                if floor and not (args.running and column == "free"):
                    add(name, memory[column] >= floor, "runtime-host RAM is below the profile/pinned-host-KV floor",
                        "Free other workloads with permission; for WSL set memory=32GB under [wsl2] in .wslconfig, then wsl --shutdown and restart Docker.",
                        {"observed_mib": memory[column], "minimum_mib": floor})
            add("ram_observed", True, "", "", memory)
        addresses = attempt("loopback_listener", lambda: listener_addresses(port), "Run on the runtime host with ss (Linux), lsof (Mac) or Get-NetTCPConnection (Windows).")
        if addresses is not None:
            add("loopback_bind", loopback_only(addresses), "listener is exposed beyond loopback", f"Bind only 127.0.0.1:{port}; do not open firewall ports.")
            if args.running:
                connected = attempt("loopback_reachability", lambda: socket.create_connection(("127.0.0.1", port), timeout=3),
                                    "Start the lane or repair the SSH tunnel; Docker Desktop must publish bridge ports, not --network host.")
                if connected:
                    connected.close()
                    add("loopback_reachability", True, "", "")
            else:
                add("loopback_port_free", not addresses, "documented port is already in use",
                    "Inspect the owner; stop only your owned lane before starting another. Native lanes share port 18082.")
    failed = any(check["status"] == "fail" for check in checks)
    return {"artifact_type": "omp_ninfer_doctor", "schema_version": 1, "receipt_class": "preflight",
            "mode": "offline" if args.offline else "running" if args.running else "pre-start",
            "lane": args.lane, "qualification_claimed": False, "hardware_checked": not args.offline,
            "status": "failed" if failed else "offline" if args.offline else "passed", "checks": checks,
            "thresholds": limits}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mac-tunnel", action="store_true",
                        help="check only the managed Mac client tunnel, never the remote GPU/WSL host")
    parser.add_argument("--lane", choices=("rtx5090", "rtx4090", "rtx3090"), default="rtx5090")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--release-spec", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--hash-model", action="store_true")
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--omp", type=Path)
    parser.add_argument("--client-platform", choices=("darwin-arm64", "linux-x64", "windows-x64"),
                        default={"Darwin": "darwin-arm64", "Windows": "windows-x64"}.get(platform.system(), "linux-x64"))
    parser.add_argument("--gpu-uuid")
    parser.add_argument("--container")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--running", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.hash_model and not args.model:
        parser.error("--hash-model requires --model")
    if args.mac_tunnel:
        if platform.system() != "Darwin":
            parser.error("--mac-tunnel must run on the Mac client, not the inference host")
        import mac_tunnel
        receipt = mac_tunnel.diagnose(args.offline)
        if args.json:
            print(json.dumps(receipt, indent=2))
        else:
            for check in receipt["checks"]:
                print(f"{check['status'].upper()} {check['name']}: {check['cause']}")
                if check["remediation"]:
                    print("  Remedy: " + check["remediation"])
            print("status=" + receipt["status"] + " (client transport only; never qualification)")
        return 1 if receipt["status"] == "failed" else 0
    if args.manifest is None:
        args.manifest = ROOT / "releases" / load(ROOT / "compatibility.json")["product_release"] / "manifest.json"
    try:
        receipt = diagnose(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        receipt = {"artifact_type": "omp_ninfer_doctor", "status": "failed", "checks": [{"name": "profile_input",
            "status": "fail", "cause": "missing or malformed manifest/profile/specification",
            "remediation": "Use the selected release manifest and verified package JSON files; no profile thresholds are guessed."}]}
    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        for check in receipt["checks"]:
            print(f"{check['status'].upper()} {check['name']}" + (": " + check["cause"] if check["cause"] else ""))
            if check["remediation"]:
                print("  Remedy: " + check["remediation"])
        print("status=" + receipt["status"] + " (preflight only; never qualification)")
    return 1 if receipt["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
