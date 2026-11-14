"""Validate the closed native-chain projection consumed by the release aggregate.

Each lane directory contains the eight projection files, ``projection-proof.json``,
``SHA256SUMS`` and ``bundle.json``. The manifest is a schema-1
``omp_ninfer_qualification_bundle`` with ``release``, ``lane`` and ``inputs``.
Each input has ``role``, ``path``, ``sha256`` and ``bytes``. A path ending in
``SHA256SUMS`` binds a closed directory, including nested relative filenames.
The public distribution uses the role ``assets``. Only its large package may
instead be external: ``role``, ``external: true``, ``name``, ``sha256``, ``bytes``;
the caller supplies that role's path explicitly. All other paths are relative,
and every bundle file must be covered. No reference is copied into public output.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bind_native_variant import LANE_VARIANTS, parse_checksums
from compose_native_qualification import native_build_profile, native_runtime_configuration
from verify_release import (NATIVE_IDENTITY_FIELDS, PRIVATE_MARKERS, effective_native_model,
                            native_package_component_tag, predecessor_manifest, unchanged_native_variant)

PROJECTION_FILES = ("agent-parity.json", "fit.json", "release-spec.json",
                    "server-config.json", "speed.json", "upgrade.json")
REFERENCE_FILE = "bundle.json"
IDENTITY_FIELDS = ("package_sha256", *NATIVE_IDENTITY_FIELDS)
SHA256 = re.compile(r"[0-9a-f]{64}")


class BundleError(ValueError):
    """An input violates the chain-to-product contract."""


def require(condition: Any, file: Path | str, pointer: str, message: str) -> None:
    if not condition:
        raise BundleError(f"{file}#{pointer or '/'}: {message}")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def decode(data: bytes, file: Path | str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, file, "/", f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise BundleError(f"{file}#/: nonfinite JSON number {value}")

    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs,
                           parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"{file}#/: invalid JSON: {error}") from error
    require(isinstance(value, dict), file, "/", "expected an object")
    return value


def field(value: Any, name: str, kind: type, file: Path | str,
          pointer: str = "") -> Any:
    require(isinstance(value, dict), file, pointer, "expected an object")
    result = value.get(name)
    require(type(result) is kind, file, f"{pointer}/{name}", f"expected {kind.__name__}")
    return result


def keys(value: Any, expected: set[str], file: Path | str, pointer: str = "") -> None:
    require(isinstance(value, dict) and set(value) == expected, file, pointer,
            f"expected exactly {sorted(expected)}")


def digest(value: Any, file: Path | str, pointer: str) -> str:
    require(isinstance(value, str) and SHA256.fullmatch(value), file, pointer,
            "expected a lowercase SHA-256")
    return value


def relative(value: Any, file: Path | str, pointer: str) -> Path:
    require(isinstance(value, str) and value and "\\" not in value and ":" not in value,
            file, pointer, "expected a portable relative path")
    path = Path(value)
    require(not path.is_absolute() and all(part not in ("", ".", "..")
                                         for part in value.split("/")),
            file, pointer, "path must stay inside its root")
    return path


def public_scan(value: Any, file: Path | str, pointer: str = "") -> None:
    if isinstance(value, dict):
        for name, child in value.items():
            public_scan(name, file, pointer)
            escaped = name.replace("~", "~0").replace("/", "~1")
            public_scan(child, file, f"{pointer}/{escaped}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            public_scan(child, file, f"{pointer}/{index}")
    elif isinstance(value, str):
        require(not any(marker in value for marker in PRIVATE_MARKERS),
                file, pointer, "contains a private marker")


class Inputs:
    """Snapshot small inputs, stream large assets, and recheck before any write."""

    def __init__(self) -> None:
        self.data: dict[Path, bytes] = {}
        self.hashes: dict[Path, str] = {}
        self.directories: dict[Path, frozenset[str]] = {}

    def read(self, path: Path, expected: str | None = None) -> bytes:
        path = Path(path).absolute()
        require(path.is_file() and not path.is_symlink(), path, "/", "expected a regular file")
        data = path.read_bytes()
        require(path not in self.data or self.data[path] == data, path, "/", "input changed")
        if expected is not None:
            require(sha(data) == digest(expected, path, "/sha256"), path, "/", "SHA-256 mismatch")
        self.data[path] = data
        return data

    def load(self, path: Path, expected: str | None = None) -> dict[str, Any]:
        return decode(self.read(path, expected), path)

    def authenticate(self, path: Path, expected: str) -> None:
        path = Path(path).absolute()
        require(path.is_file() and not path.is_symlink(), path, "/", "expected a regular file")
        with path.open("rb") as stream:
            observed = hashlib.file_digest(stream, "sha256").hexdigest()
        require(observed == digest(expected, path, "/sha256"), path, "/", "SHA-256 mismatch")
        require(path not in self.hashes or self.hashes[path] == observed,
                path, "/", "input changed")
        self.hashes[path] = observed

    def listing(self, directory: Path, expected: set[str]) -> None:
        directory = Path(directory).absolute()
        require(directory.is_dir() and not directory.is_symlink(), directory, "/",
                "expected a regular directory")
        names = frozenset(path.name for path in directory.iterdir())
        require(names == expected, directory, "/",
                f"closed set differs: missing={sorted(expected - names)}, extra={sorted(names - expected)}")
        self.directories[directory] = names
        for name in names:
            path = directory / name
            require(path.is_file() and not path.is_symlink(), path, "/", "expected a regular file")

    def tree(self, directory: Path, expected: set[str]) -> None:
        require(directory.is_dir() and not directory.is_symlink(), directory, "/", "expected a regular directory")
        observed = set()
        for path in directory.rglob("*"):
            require(not path.is_symlink(), path, "/", "symlinks are not bundle inputs")
            if path.is_file():
                observed.add(path.relative_to(directory).as_posix())
            else:
                require(path.is_dir() and any(path.iterdir()), path, "/", "unexpected empty directory")
        require(observed == expected, directory, "/",
                f"closed set differs: missing={sorted(expected - observed)}, extra={sorted(observed - expected)}")
        self.directories[directory.absolute()] = frozenset(expected)

    def binding(self, root: Path, edge: Any, file: Path | str,
                pointer: str = "") -> dict[str, Any]:
        name = field(edge, "repository_path", str, file, pointer)
        path = root / relative(name, file, f"{pointer}/repository_path")
        require(path.resolve().is_relative_to(root.resolve()), file, pointer,
                "binding escapes repository")
        return self.load(path, digest(edge.get("sha256"), file, f"{pointer}/sha256"))

    def check(self) -> None:
        for path, data in self.data.items():
            require(path.is_file() and not path.is_symlink() and path.read_bytes() == data,
                    path, "/", "input changed during aggregation")
        for path, expected in self.hashes.items():
            self.authenticate(path, expected)
        for path, names in self.directories.items():
            self.tree(path, set(names))


def native_rows(manifest: dict[str, Any], file: Path | str) -> dict[str, dict[str, Any]]:
    rows = field(field(manifest, "components", dict, file), "ninfer_variants", list,
                 file, "/components")
    result = {}
    for index, row in enumerate(rows):
        identifier = field(row, "id", str, file, f"/components/ninfer_variants/{index}")
        require(identifier in LANE_VARIANTS.values(), file,
                f"/components/ninfer_variants/{index}/id", "unknown native lane")
        lane = identifier.split("-")[0]
        require(lane not in result, file, "/components/ninfer_variants", "duplicate native lane")
        result[lane] = row
    return result


def dispositions(root: Path, release: str, manifest: dict[str, Any],
                 plan: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str], dict[str, Any]]:
    file = f"releases/{release}/plan.json"
    require(plan.get("artifact_type") == "omp_ninfer_release_plan"
            and type(plan.get("schema_version")) is int and plan["schema_version"] == 1
            and plan.get("release") == release, file, "/", "expected this release's schema-1 plan")
    predecessor = predecessor_manifest(root, release)
    require(predecessor is not None and plan.get("predecessor") == predecessor["release"],
            file, "/predecessor", "must name the latest ready predecessor")
    rows = native_rows(manifest, f"releases/{release}/manifest.json")
    previous = native_rows(predecessor, f"releases/{predecessor['release']}/manifest.json")
    planned = field(plan, "components", list, file)
    by_id = {}
    for index, item in enumerate(planned):
        identifier = field(item, "id", str, file, f"/components/{index}")
        require(identifier not in by_id, file, f"/components/{index}/id", "duplicate component")
        by_id[identifier] = item
    expected = {"rtx5090-container", *(row["id"] for row in rows.values())}
    require(set(by_id) == expected, file, "/components", "component set differs from manifest")
    recut = set()
    runtime = manifest["components"]["ninfer"]
    previous_runtime = predecessor["components"]["ninfer"]
    all_rows = {"rtx5090-container": runtime, **{row["id"]: row for row in rows.values()}}
    for identifier, row in all_rows.items():
        item = by_id[identifier]
        lane = identifier.split("-")[0]
        carried = (all(row.get(name) == previous_runtime.get(name) for name in (
            "release_tag", "oci_manifest_digest", "server_binary_sha256", "source_commit"))
            if identifier == "rtx5090-container" else unchanged_native_variant(row, previous.get(lane)))
        expected_disposition = "carried" if carried else "recut"
        require(item.get("disposition") == expected_disposition, file,
                f"/components/{planned.index(item)}/disposition", "differs from manifest carry-by-identity")
        for name in ("release_tag", "source_commit"):
            require(item.get(name) == row.get(name), file,
                    f"/components/{planned.index(item)}/{name}", "differs from manifest")
        if carried:
            old_row = previous_runtime if identifier == "rtx5090-container" else previous[lane]
            require(row.get("source_commit") == old_row.get("source_commit"), file,
                    f"/components/{planned.index(item)}/source_commit", "carried source differs from predecessor")
        if not carried and identifier != "rtx5090-container":
            recut.add(lane)
    return rows, recut, predecessor


def decisions(inputs: Inputs, root: Path, release: str, plan: dict[str, Any],
              qualification: dict[str, Any]) -> dict[str, dict[str, Any]]:
    file = f"releases/{release}/plan.json"
    result = {}
    seen = set()
    gates = field(qualification, "observed_gates", dict, f"releases/{release}/qualification.json")
    for index, item in enumerate(field(plan, "decisions", list, file)):
        pointer = f"/decisions/{index}"
        identifier = field(item, "id", str, file, pointer)
        require(re.fullmatch(r"[a-z][a-z0-9-]*", identifier) and identifier not in seen,
                file, pointer + "/id", "expected a unique decision filename stem")
        seen.add(identifier)
        require(item.get("kind") in ("component-cut", "scope", "waiver"),
                file, pointer + "/kind", "unknown decision kind")
        name = f"releases/{release}/qualification/{identifier}.json"
        edges = [(gate, edge) for gate, edge in gates.items()
                 if isinstance(edge, dict) and edge.get("repository_path") == name]
        require(len(edges) == 1, file, pointer + "/id", "decision must have exactly one qualification binding")
        gate, edge = edges[0]
        require(edge.get("sha256") == digest(item.get("sha256"), file, pointer + "/sha256"),
                file, pointer + "/sha256", "decision binding differs from plan")
        value = inputs.binding(root, edge, file, pointer)
        require(value.get("release") == release and value.get("schema_version") == 1
                and "status" not in value and "binding_requirements" not in value,
                name, "/", "draft or wrong-release decision")
        public_scan(value, name)
        result[gate] = value
    return result


class Bundle:
    def __init__(self, directory: Path, lane: str, row: dict[str, Any],
                 inputs: Inputs, release: str, assets: dict[str, Path] | None = None) -> None:
        self.directory, self.lane, self.row, self.inputs = Path(directory).absolute(), lane, row, inputs
        require(self.directory.is_dir() and not self.directory.is_symlink(), self.directory, "/",
                "expected a regular bundle directory")
        for path in self.directory.rglob("*"):
            require(not path.is_symlink(), path, "/", "symlinks are not bundle inputs")
        proof_path = self.directory / "projection-proof.json"
        self.proof = inputs.load(proof_path)
        files = field(self.proof, "files", dict, proof_path)
        admissions = set(files) & {"identity-proof.json", "quality-screen.json"}
        require(len(admissions) == 1, proof_path, "/files", "expected exactly one quality admission")
        self.admission = next(iter(admissions))
        expected = {*PROJECTION_FILES, lane + ".json", self.admission}
        require(set(files) == expected, proof_path, "/files", "expected exactly the eight projection files")
        require(self.proof.get("status") == "passed"
                and self.proof.get("lead_staging_required") is True
                and self.proof.get("publication_authorized") is False,
                proof_path, "/", "expected a passed, staging-only projection")
        self.values = {}
        for name, expected_sha in files.items():
            self.values[name] = inputs.load(self.directory / name,
                                           digest(expected_sha, proof_path, f"/files/{name}"))
        checksums = self.directory / "SHA256SUMS"
        inputs.read(checksums)
        try:
            entries = parse_checksums(checksums)
        except RuntimeError as error:
            raise BundleError(f"{checksums}#/: {error}") from error
        require(entries == {**files, "projection-proof.json": sha(inputs.read(proof_path))},
                checksums, "/", "must bind exactly the proof and its eight files")
        self.reference_path = self.directory / REFERENCE_FILE
        self.reference = inputs.load(self.reference_path)
        keys(self.reference, {"artifact_type", "schema_version", "release", "lane", "inputs"},
             self.reference_path)
        require(self.reference["artifact_type"] == "omp_ninfer_qualification_bundle"
                and type(self.reference["schema_version"]) is int and self.reference["schema_version"] == 1
                and self.reference["release"] == release and self.reference["lane"] == lane,
                self.reference_path, "/", "expected this lane's schema-1 bundle reference")
        self.evidence_paths = {}
        self.role_directories = {}
        self.external = {}
        roles = set()
        covered = expected | {"projection-proof.json", "SHA256SUMS", REFERENCE_FILE}
        for index, edge in enumerate(field(self.reference, "inputs", list, self.reference_path)):
            pointer = f"/inputs/{index}"
            role = field(edge, "role", str, self.reference_path, pointer)
            require(re.fullmatch(r"[a-z][a-z0-9_-]*", role) and role not in roles,
                    self.reference_path, pointer + "/role", "expected a unique named role")
            roles.add(role)
            size = field(edge, "bytes", int, self.reference_path, pointer)
            require(size >= 0, self.reference_path, pointer + "/bytes", "negative input size")
            expected_sha = digest(edge.get("sha256"), self.reference_path, pointer + "/sha256")
            if edge.get("external") is True:
                keys(edge, {"role", "external", "name", "sha256", "bytes"}, self.reference_path, pointer)
                name = field(edge, "name", str, self.reference_path, pointer)
                require(role == lane + "-package" and name == row.get("package_name"),
                        self.reference_path, pointer, "only this lane's package may be external")
                require(role in (assets or {}), self.reference_path, pointer + "/role", "external asset not supplied")
                path = Path(assets[role])
                self.external[name] = path
            else:
                keys(edge, {"role", "path", "sha256", "bytes"}, self.reference_path, pointer)
                name = field(edge, "path", str, self.reference_path, pointer)
                path = self.directory / relative(name, self.reference_path, pointer + "/path")
                require(name not in covered, self.reference_path, pointer + "/path", "input overlaps another binding")
                covered.add(name)
                self.evidence_paths[role] = path
            require(path.is_file() and path.stat().st_size == size, self.reference_path, pointer,
                    f"role {role!r} path {name!r} is missing or has the wrong size")
            inputs.authenticate(path, expected_sha)
            if path.name == "SHA256SUMS" and edge.get("external") is not True:
                entries = self.directory_checksums(path)
                self.role_directories[role] = path.parent
                for member, member_sha in entries.items():
                    local = path.parent / relative(member, path, "/")
                    external = self.external.get(member)
                    if external is None and role == "assets" and member == row.get("package_name"):
                        external_edge = next((item for item in self.reference["inputs"]
                                              if item.get("external") is True and item.get("name") == member), None)
                        if external_edge is not None:
                            external = (assets or {}).get(external_edge["role"])
                            require(external is not None, self.reference_path, pointer,
                                    "external package role not supplied")
                    if external is not None:
                        require(not local.exists(), path, "/", "external package must not also be bundled")
                        inputs.authenticate(Path(external), member_sha)
                    else:
                        inputs.authenticate(local, member_sha)
                        relative_name = local.relative_to(self.directory).as_posix()
                        require(relative_name not in covered, path, "/", "overlapping input bindings")
                        covered.add(relative_name)
        require("assets" in self.role_directories, self.reference_path, "/inputs", "missing closed public assets role")
        self.assets = self.role_directories["assets"]
        self.asset_hashes = self.directory_checksums(self.assets / "SHA256SUMS")
        self.asset_paths = {name: self.external.get(name, self.assets / name) for name in self.asset_hashes}
        self.receipt = inputs.load(self.assets / "package-build-receipt.json")
        inputs.tree(self.directory, covered)
        authenticated = set(inputs.hashes.values()) | {sha(data) for data in inputs.data.values()}
        for original_name, expected_sha in field(self.proof, "input_sha256", dict, proof_path).items():
            require(expected_sha in authenticated, proof_path, "/input_sha256",
                    "projection input is not covered by the bundle: " + original_name)
        consumers = field(self.proof, "consumer_sha256", dict, proof_path)
        require(set(consumers) == {"compose_native_qualification.py", "verify_release.py", "speed_gate.py"},
                proof_path, "/consumer_sha256", "unexpected projection consumer set")
        require("tooling" in self.role_directories, self.reference_path, "/inputs/tooling",
                "missing chain consumer tooling")
        for name, expected_sha in consumers.items():
            inputs.authenticate(self.role_directories["tooling"] / name, expected_sha)
        self.validate_identity()

    def directory_checksums(self, path: Path) -> dict[str, str]:
        result = {}
        for number, line in enumerate(self.inputs.read(path).decode("utf-8").splitlines(), 1):
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            require(match is not None, path, f"/lines/{number}", "malformed checksum line")
            member_sha, name = match.groups()
            relative(name, path, f"/lines/{number}")
            require(name not in result and name != "SHA256SUMS", path, f"/lines/{number}", "duplicate or self checksum")
            result[name] = member_sha
        require(result, path, "/", "empty checksum set")
        return result

    def evidence(self, name: str) -> dict[str, Any]:
        require(name in self.evidence_paths, self.reference_path, f"/inputs/{name}",
                "missing retained evidence reference")
        return self.inputs.load(self.evidence_paths[name])

    def validate_identity(self) -> None:
        row, lane, receipt = self.row, self.lane, self.receipt
        file = self.assets / "package-build-receipt.json"
        require(receipt.get("artifact_type") == "ninfer_windows_package_build_receipt"
                and receipt.get("lane") == lane, file, "/lane", "wrong package receipt lane")
        package = field(receipt, "package", dict, file)
        require(native_package_component_tag(row.get("package_name", "")) == row.get("release_tag"),
                file, "/package/filename", "package component tag differs from manifest")
        for name, expected in (("sha256", row.get("package_sha256")),
                               ("filename", row.get("package_name")), ("bytes", row.get("package_bytes"))):
            require(package.get(name) == expected, file, "/package/" + name, "differs from manifest")
        require(self.asset_hashes.get(package["filename"]) == row.get("package_sha256")
                and self.asset_paths[package["filename"]].stat().st_size == row.get("package_bytes"),
                file, "/package", "package differs from the closed asset set")
        require(sha(self.inputs.read(self.assets / "SHA256SUMS")) == row.get("checksums_sha256"),
                self.assets / "SHA256SUMS", "/", "public asset checksum identity differs from manifest")
        for name in ("patch_stack_sha", "runtime_source_sha", "package_source_sha"):
            require(receipt.get(name) == row.get("source_commit"), file, "/" + name, "differs from manifest")
        for observed, expected, pointer in (
            (receipt.get("binaries", {}).get("server_sha256"), row.get("server_binary_sha256"), "/binaries/server_sha256"),
            (receipt.get("config_sha256"), row.get("configuration_sha256"), "/config_sha256"),
            (receipt.get("model_sha256"), row.get("model_artifact_sha256"), "/model_sha256"),
            (receipt.get("build_profile"), row.get("build_profile"), "/build_profile"),
        ):
            require(observed == expected, file, pointer, "differs from manifest")
        native = self.values[lane + ".json"]
        file = self.directory / (lane + ".json")
        require(native.get("status") == "passed" and (native.get("beta_qualified") is True
                or native.get("qualification_class") == "public-release-qualification"),
                file, "/status", "native qualification did not pass")
        identity = field(native, "identity", dict, file)
        for key, alias in (("server_binary_sha256", "binary_sha256"),
                           ("source_commit", "source_commit"), ("build_profile", "build_profile"),
                           ("configuration_sha256", "configuration_sha256"),
                           ("model_artifact_sha256", "model_artifact_sha256")):
            require(identity.get(alias) == row.get(key), file, "/identity/" + alias, "differs from manifest")
        require(identity.get("source_dirty") is False, file, "/identity/source_dirty", "dirty native source")
        require(native.get("package", {}).get("sha256") == row.get("package_sha256"),
                file, "/package/sha256", "differs from manifest")
        expected_identity = {key: row.get(key) for key in IDENTITY_FIELDS}
        require(self.values["fit.json"].get("identity") == expected_identity,
                self.directory / "fit.json", "/identity", "differs from manifest")
        require(sha(self.inputs.read(self.directory / "server-config.json")) == row.get("configuration_sha256"),
                self.directory / "server-config.json", "/", "configuration differs from manifest")
        spec, config = self.values["release-spec.json"], self.values["server-config.json"]
        try:
            native_build_profile(spec, row.get("build_profile"))
            self.configuration = native_runtime_configuration(spec, config)
        except ValueError as error:
            raise BundleError(f"{self.directory / 'release-spec.json'}#/: {error}") from error
        require(spec.get("lane") == lane and spec.get("build_profile") == row.get("build_profile")
                and spec.get("runtime_shape") == row.get("runtime_shape"),
                self.directory / "release-spec.json", "/", "packaged policy differs from manifest")


def load_bundles(root: Path, release: str, plan: dict[str, Any], manifest: dict[str, Any],
                 qualification: dict[str, Any], directories: dict[str, Path],
                 inputs: Inputs | None = None, assets: dict[str, Path] | None = None) -> tuple[dict[str, Bundle], dict[str, Any]]:
    inputs = inputs if inputs is not None else Inputs()
    rows, recut, _ = dispositions(root, release, manifest, plan)
    require(set(directories) == recut, f"releases/{release}/plan.json", "/components",
            f"bundle lanes must equal re-cut native lanes {sorted(recut)}")
    model = effective_native_model(manifest).get("artifact_sha256")
    for lane, row in rows.items():
        require(row.get("model_artifact_sha256") == model, f"releases/{release}/manifest.json",
                f"/components/ninfer_variants/{lane}/model_artifact_sha256", "differs from native model")
    bound = decisions(inputs, root, release, plan, qualification)
    bundles = {lane: Bundle(directory, lane, rows[lane], inputs, release, assets)
               for lane, directory in sorted(directories.items())}
    external_roles = {edge["role"] for bundle in bundles.values() for edge in bundle.reference["inputs"]
                      if edge.get("external") is True}
    require(set(assets or {}) == external_roles, "arguments", "/asset",
            "external asset roles differ from bundle declarations")
    return bundles, bound
