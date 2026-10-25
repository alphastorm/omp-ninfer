#!/usr/bin/env python3
"""Build a deterministic CycloneDX 1.5 dependency SBOM from native build inputs.

No downloads, dependency resolution, or guessed versions/licenses. --vcpkg-lock is
an explicit resolved snapshot: {"builtin-baseline": SHA40, "packages": [{"name":
NAME, "version": VERSION, "license": SPDX_EXPRESSION, "dependencies": [NAME]}]}.
The build owner collects it from the installed vcpkg versions and port licenses;
it is not vcpkg's filesystem mutex file, nor the manifest's version constraints.
CUDA inventory is {"dlls": [{"path": "bin/cudart64_13.dll", "version": VERSION,
"eula": HTTPS_URL}]}; obtain versions from the packaged DLLs' VersionInfo.
Optional --runtime-inventory is {"dlls": [{"name": DLL_NAME, "component": "msvc-crt"
or "directstorage", "version": VERSION, "bytes": BYTES, "sha256": SHA256}],
"licenses": {COMPONENT: {"name": LICENSE_NAME, "url": HTTPS_URL or
"file": RELATIVE_EVIDENCE_FILE, "package_version": VERSION, "package_sha256": SHA256}}}.
License files are relative to that inventory's directory; package pins are an optional pair.
Vendored inventory is {"sources": [{"path": "nlohmann", "name": NAME,
"version": VERSION, "license": SPDX_EXPRESSION, "license_file": "LICENSE.MIT"}]}.
Paths are relative to the package or source tree's third_party directory.

Example (all inventories describe the exact build being packaged):
  python3 scripts/generate_native_sbom.py --package-dir package --source-dir source \\
    --source-commit <40-hex> --vcpkg-lock vcpkg-resolved.json \\
    --cuda-inventory cuda-runtime.json --third-party-inventory third-party.json \\
    --output native-dependencies.cdx.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlparse

COMMIT_RE = re.compile(r"[0-9a-f]{40}")
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
CUDA_DLL_RE = re.compile(r"(?:cudart|cublas|cufft|curand|cusolver|cusparse|nvrtc|nvjitlink|nvfatbin|npp).*\.dll", re.I)
REDIST_DLL_RE = re.compile(r"(?:concrt|msvcp|vccorlib|vcruntime|dstorage).*\.dll", re.I)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def text(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()) and value == value.strip(),
            f"{label} must be a nonempty string")
    return value


def load(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(result, dict), f"{path.name} must contain an object")
    return result


def rows(document: dict, key: str) -> list[dict]:
    result = document.get(key)
    require(isinstance(result, list) and all(isinstance(row, dict) for row in result),
            f"{key} must be an array of objects")
    return result


def relative_file(root: Path, value: Any, label: str, *, directory: bool = False) -> tuple[Path, str]:
    name = text(value, label)
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and ".." not in relative.parts
            and "\\" not in name and ":" not in name and relative.as_posix() == name
            and name != ".", f"{label} must be a normalized relative POSIX path")
    target = root.joinpath(*relative.parts).resolve()
    require(target.is_relative_to(root.resolve()), f"{label} escapes its tree")
    require(target.is_dir() if directory else target.is_file(), f"{label} does not exist: {name}")
    return target, name


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def property_(name: str, value: str) -> dict:
    return {"name": "ninfer:" + name, "value": value}


def build_sbom(*, package_dir: Path, source_dir: Path, source_commit: str,
               vcpkg_manifest: Path, vcpkg_lock: Path, cuda_inventory: Path,
               third_party_inventory: Path, runtime_inventory: Path | None = None,
               runtime_binary: str = "bin/ninfer-serve.exe") -> dict:
    require(COMMIT_RE.fullmatch(source_commit) is not None, "source commit must be 40 lower-case hex characters")
    binary, binary_path = relative_file(package_dir, runtime_binary, "runtime binary")
    manifest, lock = load(vcpkg_manifest), load(vcpkg_lock)
    baseline = manifest.get("builtin-baseline")
    require(isinstance(baseline, str) and COMMIT_RE.fullmatch(baseline) is not None,
            "vcpkg manifest must pin builtin-baseline")
    require(lock.get("builtin-baseline") == baseline, "vcpkg lock baseline must match the manifest")
    direct = manifest.get("dependencies")
    require(isinstance(direct, list), "vcpkg manifest dependencies must be an array")
    direct_names = []
    for dependency in direct:
        name = dependency.get("name") if isinstance(dependency, dict) else dependency
        require(isinstance(name, str) and NAME_RE.fullmatch(name) is not None, "invalid vcpkg dependency name")
        direct_names.append(name)
    packages = rows(lock, "packages")
    by_name: dict[str, dict] = {}
    for row in packages:
        name = text(row.get("name"), "vcpkg package name")
        require(NAME_RE.fullmatch(name) is not None, "invalid vcpkg package name")
        require(name not in by_name, f"duplicate vcpkg package: {name}")
        text(row.get("version"), f"{name} version")
        text(row.get("license"), f"{name} license")
        dependencies = row.get("dependencies")
        require(isinstance(dependencies, list) and all(isinstance(item, str) for item in dependencies),
                f"{name} dependencies must be a name array (including transitive dependencies)")
        by_name[name] = row
    for name in direct_names + [item for row in packages for item in row["dependencies"]]:
        require(name in by_name, f"vcpkg lock is missing dependency: {name}")
    reachable: set[str] = set()
    pending = list(direct_names)
    while pending:
        name = pending.pop()
        if name not in reachable:
            reachable.add(name)
            pending.extend(by_name[name]["dependencies"])
    require(reachable == set(by_name), "vcpkg lock contains packages outside the manifest dependency closure")

    runtime_ref = "runtime:" + binary_path
    runtime = {"type": "application", "bom-ref": runtime_ref, "name": binary.name,
               "version": source_commit,
               "hashes": [{"alg": "SHA-256", "content": digest(binary)}],
               "properties": [property_("source_commit", source_commit), property_("package_path", binary_path)]}
    components: list[dict] = []
    edges: dict[str, list[str]] = {}
    root_dependencies = {"vcpkg:" + name for name in direct_names}
    for name, row in sorted(by_name.items()):
        ref = "vcpkg:" + name
        components.append({"type": "library", "bom-ref": ref, "name": name, "version": row["version"],
                           "purl": f"pkg:vcpkg/{quote(name)}@{quote(row['version'], safe='')}",
                           "licenses": [{"expression": row["license"]}]})
        edges[ref] = sorted({"vcpkg:" + item for item in row["dependencies"]})

    dll_paths: set[str] = set()
    for row in rows(load(cuda_inventory), "dlls"):
        dll, path = relative_file(package_dir, row.get("path"), "CUDA DLL path")
        require(dll.suffix.lower() == ".dll", "CUDA inventory entries must be DLLs")
        require(path.casefold() not in dll_paths, f"duplicate CUDA DLL: {path}")
        dll_paths.add(path.casefold())
        version = text(row.get("version"), f"{dll.name} version")
        eula = text(row.get("eula"), f"{dll.name} EULA")
        url = urlparse(eula)
        require(url.scheme == "https" and bool(url.netloc) and not url.username and not url.password,
                f"{dll.name} EULA must be an HTTPS URL")
        ref = "cuda:" + path
        components.append({"type": "library", "bom-ref": ref, "name": dll.name, "version": version,
                           "hashes": [{"alg": "SHA-256", "content": digest(dll)}],
                           "licenses": [{"license": {"name": "NVIDIA CUDA Toolkit EULA", "url": eula}}],
                           "properties": [property_("package_path", path)]})
        root_dependencies.add(ref)
        edges[ref] = []
    for dll in package_dir.rglob("*"):
        if dll.is_file() and CUDA_DLL_RE.fullmatch(dll.name):
            require(dll.relative_to(package_dir).as_posix().casefold() in dll_paths,
                    f"CUDA inventory is missing packaged DLL: {dll.name}")

    if runtime_inventory is not None:
        inventory = load(runtime_inventory)
        licenses = inventory.get("licenses")
        require(isinstance(licenses, dict), "runtime redistributable licenses must be an object")
        redist_paths: set[str] = set()
        for row in rows(inventory, "dlls"):
            name = text(row.get("name"), "runtime DLL name")
            require(PurePosixPath(name).name == name and name.lower().endswith(".dll"),
                    "runtime DLL name must be a filename")
            dll, path = relative_file(package_dir, "bin/" + name, "runtime DLL path")
            require(path.casefold() not in redist_paths and path.casefold() not in dll_paths,
                    f"duplicate runtime DLL: {path}")
            redist_paths.add(path.casefold())
            component = row.get("component")
            require(component in ("msvc-crt", "directstorage"), "unknown runtime redistributable component")
            version = text(row.get("version"), f"{name} version")
            require(type(row.get("bytes")) is int and row["bytes"] > 0
                    and row["bytes"] == dll.stat().st_size, f"{name} byte count mismatch")
            dll_sha = digest(dll)
            require(row.get("sha256") == dll_sha, f"{name} SHA-256 mismatch")
            license_ = licenses.get(component)
            require(isinstance(license_, dict), f"{component} license is missing")
            license_value = {"name": text(license_.get("name"), f"{component} license name")}
            properties = [property_("package_path", path), property_("redistributable_component", component)]
            require("url" in license_ or "file" in license_, f"{component} license needs URL or file evidence")
            if "url" in license_:
                url = text(license_["url"], f"{component} license URL")
                parsed = urlparse(url)
                require(parsed.scheme == "https" and bool(parsed.netloc)
                        and not parsed.username and not parsed.password,
                        f"{component} license URL must be HTTPS")
                license_value["url"] = url
            if "file" in license_:
                evidence, relative = relative_file(
                    runtime_inventory.parent, license_["file"], f"{component} license file")
                properties.extend([property_("license_file", relative),
                                   property_("license_sha256", digest(evidence))])
            if "package_version" in license_ or "package_sha256" in license_:
                package_version = text(license_.get("package_version"), f"{component} package version")
                package_sha = license_.get("package_sha256")
                require(isinstance(package_sha, str) and re.fullmatch(r"[0-9a-f]{64}", package_sha) is not None,
                        f"{component} package SHA-256 is invalid")
                properties.extend([property_("redistributable_package_version", package_version),
                                   property_("redistributable_package_sha256", package_sha)])
            ref = "redist:" + path
            components.append({"type": "library", "bom-ref": ref, "name": name, "version": version,
                               "hashes": [{"alg": "SHA-256", "content": dll_sha}],
                               "licenses": [{"license": license_value}], "properties": properties})
            root_dependencies.add(ref)
            edges[ref] = []
        for dll in package_dir.rglob("*"):
            if dll.is_file() and REDIST_DLL_RE.fullmatch(dll.name):
                require(dll.relative_to(package_dir).as_posix().casefold() in redist_paths,
                        f"runtime inventory is missing packaged DLL: {dll.name}")

    third_party = source_dir / "third_party"
    require(third_party.is_dir(), "source tree must contain third_party")
    source_paths: set[str] = set()
    for row in rows(load(third_party_inventory), "sources"):
        source, path = relative_file(third_party, row.get("path"), "third_party path", directory=True)
        require("/" not in path, "third_party inventory must name each top-level source directory")
        require(path.casefold() not in source_paths, f"duplicate third_party source: {path}")
        source_paths.add(path.casefold())
        name = text(row.get("name"), f"{path} name")
        version = text(row.get("version"), f"{path} version")
        license_ = text(row.get("license"), f"{path} license")
        license_file, license_path = relative_file(source, row.get("license_file"), f"{path} license file")
        ref = "third_party:" + path
        components.append({"type": "library", "bom-ref": ref, "name": name, "version": version,
                           "licenses": [{"expression": license_}],
                           "properties": [property_("source_path", "third_party/" + path),
                                          property_("license_file", license_path),
                                          property_("license_sha256", digest(license_file))]})
        root_dependencies.add(ref)
        edges[ref] = []
    actual_sources = {path.name.casefold() for path in third_party.iterdir() if path.is_dir() and not path.name.startswith(".")}
    require(source_paths == actual_sources, "third_party inventory must cover every source directory")
    edges[runtime_ref] = sorted(root_dependencies)
    inputs = [("vcpkg_manifest", vcpkg_manifest), ("vcpkg_lock", vcpkg_lock),
              ("cuda_inventory", cuda_inventory), ("third_party_inventory", third_party_inventory)]
    if runtime_inventory is not None:
        inputs.append(("runtime_inventory", runtime_inventory))
    return {"$schema": "http://cyclonedx.org/schema/bom-1.5.schema.json", "bomFormat": "CycloneDX",
            "specVersion": "1.5", "version": 1,
            "metadata": {"component": runtime, "properties": [property_("vcpkg_baseline", baseline),
                *[property_(f"input:{name}:sha256", digest(path)) for name, path in inputs]]},
            "components": sorted(components, key=lambda item: item["bom-ref"]),
            "dependencies": [{"ref": ref, "dependsOn": targets} for ref, targets in sorted(edges.items())]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--package-dir", type=Path, required=True, help="unpacked native Windows package root")
    parser.add_argument("--source-dir", type=Path, required=True, help="source tree used for the build")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--vcpkg-manifest", type=Path, help="default: <source-dir>/vcpkg.json")
    parser.add_argument("--vcpkg-lock", type=Path, required=True, help="resolved versions/licenses/dependency snapshot")
    parser.add_argument("--cuda-inventory", type=Path, required=True)
    parser.add_argument("--third-party-inventory", type=Path, required=True)
    parser.add_argument("--runtime-inventory", type=Path,
                        help="optional exact CRT/DirectStorage DLL and license inventory")
    parser.add_argument("--runtime-binary", default="bin/ninfer-serve.exe")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        document = build_sbom(package_dir=args.package_dir, source_dir=args.source_dir,
            source_commit=args.source_commit, vcpkg_manifest=args.vcpkg_manifest or args.source_dir / "vcpkg.json",
            vcpkg_lock=args.vcpkg_lock, cuda_inventory=args.cuda_inventory,
            third_party_inventory=args.third_party_inventory, runtime_inventory=args.runtime_inventory,
            runtime_binary=args.runtime_binary)
        args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"generate_native_sbom: {error}", file=sys.stderr)
        return 1
    print(f"{args.output.name}: {digest(args.output)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
