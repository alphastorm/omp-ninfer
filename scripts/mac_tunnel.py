#!/usr/bin/env python3
"""Preview macOS LaunchAgent for the documented loopback SSH route.

install stages a disabled agent; start enables it (including at login); stop
unloads and disables it. No server lifecycle, SSH configuration, credentials or
OMP configuration are changed. Status is transport evidence, not qualification.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

LABEL = "com.alphastorm.omp-ninfer.tunnel"
SCHEMA = 1


class TunnelError(RuntimeError):
    """Only fixed, privacy-safe messages cross the CLI boundary."""


def paths(home=None):
    home = Path.home() if home is None else Path(home)
    root = home / "Library/Application Support/omp-ninfer/tunnel"
    return {"root": root, "config": root / "config.json", "worker": root / "mac_tunnel.py",
            "runtime": root / "runtime.json", "status": root / "status.json",
            "plist": home / "Library/LaunchAgents" / (LABEL + ".plist")}


def private_file(path):
    if path.is_symlink() or not path.is_file():
        return False
    info = path.stat()
    return info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) & 0o077 == 0


def private_root(p):
    p["root"].mkdir(parents=True, exist_ok=True, mode=0o700)
    info = p["root"].lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise TunnelError("state directory must be owner-owned, private and not a symlink")


def atomic(path, data):
    fd, temporary = tempfile.mkstemp(prefix=".tunnel-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def save(path, value):
    atomic(path, (json.dumps(value, indent=2) + "\n").encode())


def load_config(p):
    if not private_file(p["config"]):
        raise TunnelError("managed configuration missing or not private; run install")
    config = json.loads(p["config"].read_text())
    if config.get("label") != LABEL or config.get("schema_version") != SCHEMA:
        raise TunnelError("unrecognized managed configuration")
    validate(config)
    return config


def validate(config):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+@[A-Za-z0-9_.:-]+", config["destination"]):
        raise TunnelError("destination must be an explicit user@hostname or user@IP, not an SSH alias")
    for key in ("local_port", "remote_port", "ssh_port"):
        if type(config[key]) is not int or not 1 <= config[key] <= 65535:
            raise TunnelError("ports must be integers from 1 through 65535")
    for key in ("key_file", "identity_file"):
        if config.get(key) is not None and not Path(config[key]).is_absolute():
            raise TunnelError("credential file references must be absolute paths")


def ssh_command(config):
    # Ignore user/system SSH configuration: it may add forwards, proxy commands,
    # a shell command, multiplexing, or a non-loopback GatewayPorts setting.
    command = ["/usr/bin/ssh", "-F", "/dev/null", "-NT", "-S", "none",
               "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "ControlMaster=no", "-o", "ControlPersist=no",
               "-o", "ExitOnForwardFailure=yes", "-o", "GatewayPorts=no",
               "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
               "-o", "ConnectTimeout=10", "-o", "ConnectionAttempts=1",
               "-o", "PermitLocalCommand=no", "-o", "RequestTTY=no",
               "-p", str(config["ssh_port"]),
               "-L", f"127.0.0.1:{config['local_port']}:127.0.0.1:{config['remote_port']}"]
    if config.get("identity_file"):
        command += ["-o", "IdentitiesOnly=yes", "-i", config["identity_file"]]
    return command + [config["destination"]]


def plist(p):
    return {"Label": LABEL, "ProgramArguments": [str(Path(sys.executable).resolve()),
            str(p["worker"]), "_run"], "RunAtLoad": True, "KeepAlive": True,
            "ThrottleInterval": 10, "ExitTimeOut": 15, "Umask": 0o077,
            "ProcessType": "Background", "StandardOutPath": "/dev/null",
            "StandardErrorPath": "/dev/null"}


def launchctl(*arguments):
    return subprocess.run(["/bin/launchctl", *arguments], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=20)


def domain():
    return f"gui/{os.getuid()}"


def job():
    result = launchctl("print", domain() + "/" + LABEL)
    if result.returncode:
        # A missing GUI domain must not masquerade as a successfully stopped job.
        if launchctl("print", domain()).returncode:
            raise TunnelError("GUI login domain unavailable; run as the logged-in Mac user without sudo")
        return {"loaded": False, "pid": None}
    match = re.search(r"^\s*pid = (\d+)\s*$", result.stdout, re.MULTILINE)
    return {"loaded": True, "pid": int(match[1]) if match else None}


def checked(*arguments):
    if launchctl(*arguments).returncode:
        raise TunnelError("launchctl operation failed; inspect the logged-in user's LaunchAgent state")


def owned_plist(p):
    if not private_file(p["plist"]):
        raise TunnelError("LaunchAgent missing, non-private or not owned by this installation")
    value = plistlib.loads(p["plist"].read_bytes())
    if (value.get("Label") != LABEL or value.get("ProgramArguments", [])[1:] != [str(p["worker"]), "_run"]):
        raise TunnelError("refusing to replace or unload an unrelated LaunchAgent")


@contextlib.contextmanager
def lock(p, name):
    private_root(p)
    fd = os.open(p["root"] / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise TunnelError("another lifecycle operation is active") from None
        yield
    finally:
        os.close(fd)


def install(p, config):
    validate(config)
    if p["plist"].exists() or p["plist"].is_symlink():
        owned_plist(p)
    if job()["loaded"]:
        raise TunnelError("stop the managed agent before installing or changing its destination")
    checked("disable", domain() + "/" + LABEL)
    p["plist"].parent.mkdir(parents=True, exist_ok=True)
    atomic(p["worker"], Path(__file__).read_bytes())
    save(p["config"], config)
    atomic(p["plist"], plistlib.dumps(plist(p)))
    p["runtime"].unlink(missing_ok=True)


def start(p):
    load_config(p)
    owned_plist(p)
    checked("enable", domain() + "/" + LABEL)
    if not job()["loaded"]:
        checked("bootstrap", domain(), str(p["plist"]))


def stop(p):
    owned_plist(p)
    checked("disable", domain() + "/" + LABEL)
    if job()["loaded"]:
        checked("bootout", domain() + "/" + LABEL)
    deadline = time.monotonic() + 15
    while job()["loaded"]:
        if time.monotonic() >= deadline:
            raise TunnelError("LaunchAgent did not unload; uninstall refused")
        time.sleep(0.1)
    p["runtime"].unlink(missing_ok=True)


def uninstall(p):
    if p["plist"].exists() or p["plist"].is_symlink():
        stop(p)
        p["plist"].unlink()
    elif job()["loaded"]:
        raise TunnelError("loaded agent has no owned plist; refusing blind unload")
    # Never remove a tree recursively, a bearer file, an SSH identity, or client config.
    for name in ("config", "worker", "runtime", "status"):
        p[name].unlink(missing_ok=True)
    (p["root"] / "worker.lock").unlink(missing_ok=True)


def listener_owned(port, pid):
    result = subprocess.run(["/usr/sbin/lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fpn"],
                            capture_output=True, text=True, timeout=10)
    if result.returncode not in (0, 1):
        raise TunnelError("listener inventory unavailable")
    owner, listeners = None, []
    for line in result.stdout.splitlines():
        if line.startswith("p"):
            owner = int(line[1:])
        elif line.startswith("n"):
            listeners.append((owner, line[1:]))
    return bool(listeners) and all(item == (pid, f"127.0.0.1:{port}") for item in listeners)


def snapshot(p, offline=False):
    config = load_config(p)
    owned_plist(p)
    state = {"artifact_type": "omp_ninfer_mac_tunnel", "schema_version": SCHEMA,
             "receipt_class": "preflight", "qualification_claimed": False,
             "updated_unix": time.time(), "local_port": config["local_port"],
             "remote_port": config["remote_port"], "status": "offline" if offline else "stopped",
             "loaded": False, "listener_owned": False}
    if offline:
        return state
    current = job()
    state["loaded"] = current["loaded"]
    if current["loaded"]:
        state["status"] = "starting"
        try:
            runtime = json.loads(p["runtime"].read_text())
        except (OSError, ValueError):
            runtime = {}
        # A prior launch's last good status never proves current readiness.
        if runtime.get("supervisor_pid") == current["pid"] and current["pid"] is not None:
            for key in ("status", "ssh_pid", "retry_seconds", "last_exit_code"):
                if key in runtime:
                    state[key] = runtime[key]
            if runtime.get("ssh_pid"):
                state["listener_owned"] = listener_owned(config["local_port"], runtime["ssh_pid"])
            if state["status"] == "forwarding" and not state["listener_owned"]:
                state["status"] = "connecting"
    return state


def authenticated_endpoint(config):
    path = Path(config["key_file"])
    if not private_file(path) or not path.stat().st_size:
        raise TunnelError("bearer file must be nonempty, owner-owned, private and not a symlink")
    token = path.read_text().strip()
    if not token or any(c.isspace() for c in token):
        raise TunnelError("bearer file must contain one nonempty token")
    request = urllib.request.Request(f"http://127.0.0.1:{config['local_port']}/v1/models",
                                     headers={"Authorization": "Bearer " + token})
    # A redirect or environment proxy must never carry the bearer off loopback.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=5) as response:
        body = json.loads(response.read(1024 * 1024))
        return (response.status == 200 and isinstance(body, dict)
                and isinstance(body.get("data"), list) and bool(body["data"]))


def diagnose(offline=False, p=None):
    p = paths() if p is None else p
    checks = []
    def add(name, passed, cause, remedy):
        checks.append({"name": name, "status": "pass" if passed else "fail",
                       "cause": "" if passed else cause, "remediation": "" if passed else remedy})
    try:
        config = load_config(p)
        state = snapshot(p, offline)
        add("mac_tunnel_install", True, "", "")
        if offline:
            checks.append({"name": "mac_tunnel_transport", "status": "skipped",
                           "cause": "offline: launchd, listener and endpoint probes disabled", "remediation": ""})
        else:
            add("mac_tunnel_listener", state["listener_owned"], "managed SSH does not own the loopback listener",
                "Run mac_tunnel.py start; close only your manual tunnel if it owns this port. Check SSH authentication and the pinned host key interactively.")
            if state["listener_owned"]:
                try:
                    ready = authenticated_endpoint(config)
                except (OSError, ValueError, TunnelError):
                    ready = False
                add("mac_tunnel_endpoint", ready, "authenticated loopback /v1/models is unavailable",
                    "Check the existing bearer file permissions and remote loopback service; a live SSH transport alone does not prove NInfer readiness.")
    except (OSError, ValueError, KeyError, TypeError, TunnelError, subprocess.SubprocessError):
        add("mac_tunnel_install", False, "managed tunnel is missing, malformed or unavailable",
            "Install the agent as the logged-in user; use mac_tunnel.py status and never run with sudo.")
    return {"artifact_type": "omp_ninfer_doctor", "schema_version": SCHEMA, "receipt_class": "preflight",
            "lane": "rtx5090-macos-client", "mode": "offline" if offline else "mac-tunnel",
            "qualification_claimed": False, "hardware_checked": False,
            "status": "failed" if any(c["status"] == "fail" for c in checks) else "offline" if offline else "passed",
            "checks": checks}


def retry_delay(previous, lifetime):
    return 1 if lifetime >= 60 else min(previous * 2, 60)


def supervise(p):
    config = load_config(p)
    stopping = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stopping.set())
    delay = 1
    child = None
    def record(status, **fields):
        save(p["runtime"], {"supervisor_pid": os.getpid(), "status": status,
                            "updated_unix": time.time(), **fields})
    with lock(p, "worker.lock"):
        try:
            while not stopping.is_set():
                began = time.monotonic()
                record("connecting")
                child = subprocess.Popen(ssh_command(config), stdin=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                record("forwarding", ssh_pid=child.pid)
                while child.poll() is None and not stopping.wait(0.25):
                    pass
                if stopping.is_set():
                    break
                lifetime = time.monotonic() - began
                if lifetime >= 60:
                    delay = 1
                record("backoff", last_exit_code=child.returncode, retry_seconds=delay)
                if stopping.wait(delay):
                    break
                delay = retry_delay(delay, lifetime)
        finally:
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            record("stopped")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "start", "stop", "status", "doctor", "uninstall", "_run"))
    parser.add_argument("--destination", help="explicit user@host (SSH config aliases are not read)")
    parser.add_argument("--local-port", type=int, default=18089)
    parser.add_argument("--remote-port", type=int, default=18089)
    parser.add_argument("--ssh-port", type=int, default=22)
    parser.add_argument("--identity-file", type=Path, help="existing SSH key; referenced, never copied")
    parser.add_argument("--key-file", type=Path, default=Path.home() / ".omp/agent/ninfer-beta.key")
    parser.add_argument("--offline", action="store_true", help="doctor only: no launchd/network probes")
    args = parser.parse_args(argv)
    if args.action == "install" and not args.destination:
        parser.error("install requires --destination user@host")
    if args.offline and args.action != "doctor":
        parser.error("--offline applies only to doctor")
    try:
        if platform.system() != "Darwin" or os.getuid() == 0:
            raise TunnelError("run as the logged-in macOS user, without sudo")
        p = paths()
        if args.action == "_run":
            supervise(p)
            return 0
        if args.action == "doctor":
            result = diagnose(args.offline, p)
        else:
            with lock(p, "lifecycle.lock"):
                if args.action == "install":
                    config = {"label": LABEL, "schema_version": SCHEMA, "destination": args.destination,
                              "local_port": args.local_port, "remote_port": args.remote_port, "ssh_port": args.ssh_port,
                              "key_file": str(args.key_file.expanduser().absolute()),
                              "identity_file": str(args.identity_file.expanduser().absolute()) if args.identity_file else None}
                    install(p, config)
                elif args.action in ("start", "stop", "uninstall"):
                    globals()[args.action](p)
                if args.action == "uninstall":
                    result = {"status": "uninstalled", "qualification_claimed": False}
                else:
                    result = snapshot(p)
                    save(p["status"], result)
        print(json.dumps(result, indent=2))
        return 1 if result["status"] == "failed" else 0
    except (OSError, ValueError, KeyError, TypeError, TunnelError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, TunnelError) else "operation unavailable or invalid managed state"
        print(json.dumps({"status": "failed", "cause": message, "qualification_claimed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
