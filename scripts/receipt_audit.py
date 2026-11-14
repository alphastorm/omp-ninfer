#!/usr/bin/env python3
"""Generate or check a release's lane-stage or composed-final receipt inventory.

``--at`` reads immutable git inputs instead of the working tree. ``--check`` never
writes; without it, the audit and its qualification binding are replaced atomically.
The audit inventories its own path without hashing its output, and omits the
qualification receipt_audit edge from the scalar inventory.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_io import atomic_write, atomic_write_json, git

ROOT = Path(__file__).resolve().parents[1]
AUDIT = "qualification/receipt-audit.json"
PHASES = ("lane-stage", "composed-final")
GENERATED = {"manifest.json", "qualification.json", "compatibility.json", "COMPATIBILITY.md", AUDIT}
MUTABLE = GENERATED | {"NINFER_RELEASE_NOTES.md", "acceptance/composed-external-installation.json"}


class Refusal(ValueError):
    """The input tree does not admit a truthful receipt inventory."""


def _bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _Tree:
    def __init__(self, root: Path, at: str | None = None):
        self.root = Path(root)
        self.at = git(self.root, "rev-parse", "--verify", f"{at}^{{commit}}").strip() if at else None
        self.cache: dict[str, bytes] = {}
        if self.at:
            listing = subprocess.run(
                ["git", "ls-tree", "-r", "-z", "--name-only", self.at, "--", "releases"],
                cwd=self.root, check=True, capture_output=True,
            ).stdout
            self.paths = [path.decode("utf-8") for path in listing.split(b"\0") if path]
        else:
            self.paths = [path.relative_to(self.root).as_posix()
                          for path in (self.root / "releases").rglob("*") if path.is_file()]

    def read(self, path: str) -> bytes:
        if path not in self.cache:
            if path not in self.paths:
                raise Refusal(f"missing release input: {path}")
            if self.at:
                self.cache[path] = subprocess.run(
                    ["git", "show", f"{self.at}:{path}"], cwd=self.root,
                    check=True, capture_output=True,
                ).stdout
            else:
                self.cache[path] = (self.root / path).read_bytes()
        return self.cache[path]

    def document(self, path: str) -> dict[str, Any]:
        value = json.loads(self.read(path))
        if not isinstance(value, dict):
            raise Refusal(f"release input must be an object: {path}")
        return value

    def files(self, release: str) -> dict[str, str]:
        prefix = f"releases/{release}/"
        return {path.removeprefix(prefix): _sha(self.read(path))
                for path in self.paths if path.startswith(prefix) and path != prefix + AUDIT}


def _predecessor(tree: _Tree, release: str) -> tuple[str, dict[str, Any]]:
    # Import lazily: the verifier also imports ready_errors from this module.
    from verify_release import ga_release, product_version

    current = product_version(release)
    if current is None:
        raise Refusal(f"invalid product release: {release}")
    candidates = []
    for path in sorted(tree.paths):
        parts = path.split("/")
        if len(parts) != 3 or parts[-1] != "manifest.json":
            continue
        version = product_version(parts[1])
        if not ga_release(parts[1]) or version is None or version >= current:
            continue
        manifest = tree.document(path)
        if manifest.get("status") == "ready":
            candidates.append((version, parts[1], manifest))
    if not candidates:
        raise Refusal(f"no earlier ready GA predecessor for {release}")
    _, name, manifest = max(candidates, key=lambda row: row[0])
    return name, manifest


def _references(qualification: dict[str, Any]) -> Iterator[tuple[str, tuple[str, str]]]:
    if isinstance(qualification.get("summary"), str):
        yield "summary", (qualification["summary"], qualification["sha256"])
    for field, value in qualification.items():
        if isinstance(value, dict) and isinstance(value.get("path"), str):
            yield field, (value["path"], value["sha256"])


def _carried(tree: _Tree, release: str, predecessor: str, manifest: dict[str, Any],
             previous: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], list[str]]:
    from verify_release import PRODUCT_RAW_URL_RE, unchanged_native_variant

    old_prefix, new_prefix = f"releases/{predecessor}/", f"releases/{release}/"
    old_rows = {row["id"]: row for row in previous.get("components", {}).get("ninfer_variants", [])}
    carried, in_place, policies = {}, {}, []
    for row in manifest.get("components", {}).get("ninfer_variants", []):
        old = old_rows.get(row["id"])
        if not unchanged_native_variant(row, old):
            continue
        expected = copy.deepcopy(old)
        qualification = row.get("qualification", {})
        expected_qualification = expected.get("qualification", {})
        for field in ("summary", "release_spec", "server_config"):
            before = expected_qualification.get(field)
            after = qualification.get(field)
            if field != "summary" and isinstance(before, dict) and isinstance(after, dict):
                before, after = before.get("path"), after.get("path")
            if isinstance(before, str) and before.startswith(old_prefix):
                relocated = new_prefix + before.removeprefix(old_prefix)
                if after == relocated:
                    if field == "summary":
                        expected_qualification[field] = after
                    else:
                        expected_qualification[field]["path"] = after
        if qualification.get("public_url") is not None:
            url = qualification.get("public_url")
            match = PRODUCT_RAW_URL_RE.fullmatch(url) if isinstance(url, str) else None
            if match is None or match[2] != qualification.get("summary"):
                raise Refusal(f"{row['id']}: carried summary URL must bind its summary")
            expected_qualification["public_url"] = url
        if row != expected:
            raise Refusal(f"{row['id']}: carried manifest row must remain byte-identical except relocation")

        tag = row["release_tag"]
        reason_prefix = f"Carried component, unchanged since {predecessor}"
        reason = (f"{reason_prefix}: {tag} (source {row['source_commit'][:8]}) keeps its "
                  "byte-identical published row and qualification; no fresh hardware qualification, "
                  "bounded pressure saves or new-client/product-route acceptance is claimed.")
        old_references = dict(_references(old.get("qualification", {})))
        references = [(old_references[field], value) for field, value in _references(qualification)]
        if row.get("checksums_sha256") is not None:
            name = f"qualification/{row['id']}.SHA256SUMS"
            references.append(((old_prefix + name, old["checksums_sha256"]),
                               (new_prefix + name, row["checksums_sha256"])))
        for (old_path, old_sha), (path, digest) in references:
            data = tree.read(path)
            if _sha(data) != digest or old_sha != digest or data != tree.read(old_path):
                raise Refusal(f"carried file is not byte-identical to {predecessor}: {path}")
            if path.startswith(new_prefix):
                carried[path.removeprefix(new_prefix)] = reason
            elif path.startswith(old_prefix):
                in_place[path.removeprefix(old_prefix)] = (
                    f"{reason_prefix}: bound in place at {path} by the carried {tag} "
                    "row (hash unchanged); not copied into this release.")
        lane = row["id"].removesuffix("-windows-native")
        label = re.sub(r"([a-zA-Z]+)([0-9]+)", lambda m: m[1].upper() + " " + m[2], lane)
        channel = re.search(r"-(beta\.[0-9]+|preview\.[0-9]+)$", tag)
        label += " " + (channel[1] if channel else tag)
        policies.append(f"The carried {label} component keeps its byte-identical {predecessor} "
                        "row and qualification as kept files.")
    return carried, in_place, policies


def _leaves(value: Any, pointer: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaves(child, pointer + "/" + key.replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _leaves(child, pointer + "/" + str(index))
    else:
        yield pointer, value


def _date(value: str | None) -> str:
    if value is None:
        return datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise Refusal("audit as_of must be an ISO date")
    datetime.date.fromisoformat(value)
    return value


def generate_audit(root: Path, release: str, *, phase: str, as_of: str | None = None,
                   at: str | None = None) -> dict[str, Any]:
    """Recompute an inventory without writing either authority."""
    if phase not in PHASES:
        raise Refusal("audit phase must be lane-stage or composed-final")
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", release):
        raise Refusal(f"invalid product release: {release}")
    tree = _Tree(root, at)
    predecessor, previous = _predecessor(tree, release)
    old_prefix, new_prefix = f"releases/{predecessor}/", f"releases/{release}/"
    manifest = tree.document(new_prefix + "manifest.json")
    if manifest.get("release") != release:
        raise Refusal("manifest release must match the requested release")
    carried, in_place, policies = _carried(tree, release, predecessor, manifest, previous)
    before, after = tree.files(predecessor), tree.files(release)
    # Its path is inventoried, but the output cannot compare or bind its own bytes.
    if old_prefix + AUDIT in tree.paths:
        before[AUDIT] = _sha(tree.read(old_prefix + AUDIT))
    after[AUDIT] = ""
    rows = []
    for name in sorted(before.keys() | after.keys()):
        disposition = ("added" if name not in before else "dropped" if name not in after else
                       "kept" if before[name] == after[name] else "replaced")
        if disposition == "kept" and name not in GENERATED:
            if name != "qualification/runtime-base.json" and name not in carried:
                raise Refusal(f"unadmitted predecessor bytes: {name}")
            reason = carried.get(name, "Same immutable base receipt; current component-cut ancestry "
                                 "and image binding admit reuse, not prior runtime execution.")
        elif name in carried:
            raise Refusal(f"carried file is not byte-identical to {predecessor}: {name}")
        elif disposition == "dropped":
            reason = in_place.get(name, "Predecessor evidence is not a current successor result, "
                                  "waiver or review approval.")
        else:
            reason = ("Current successor identity, authored prose or evidence; its admitted producer "
                      "retains its actual subject and scope.")
        row = {"file": name, "disposition": disposition, "reason": reason}
        if name in before:
            row["predecessor_sha256"] = before[name]
        if name in after and name not in MUTABLE:
            row["staged_sha256"] = after[name]
        elif name in after:
            row["binding"] = ("Mutable release state/prose: bound by the evidence hash chain and later "
                              "immutable pin stages, not a retained-byte audit snapshot.")
        rows.append(row)
    bindings = []
    for name in ("manifest.json", "qualification.json", "compatibility.json"):
        old, new = ({key: value for key, value in _leaves(tree.document(prefix + name))
                     if key != "/receipt_audit" and not key.startswith("/receipt_audit/")}
                    for prefix in (old_prefix, new_prefix))
        for pointer in sorted(old.keys() | new.keys()):
            disposition = ("added" if pointer not in old else "dropped" if pointer not in new else
                           "kept" if old[pointer] == new[pointer] else "replaced")
            row = {"file": name, "pointer": pointer, "disposition": disposition,
                   "reason": "Scalar identity/schema/policy inventory; file receipts retain their "
                             "own exact execution subjects."}
            for field, values in (("predecessor_value_sha256", old), ("staged_value_sha256", new)):
                if pointer in values:
                    row[field] = _sha(json.dumps(values[pointer], sort_keys=True,
                                                separators=(",", ":")).encode("utf-8"))
            bindings.append(row)
    policy = ["No predecessor runtime/native/client execution, waiver or review approval transfers.",
              *policies, "Generated authorities and the inventory have no self-referential retained-byte hash."]
    return {"artifact_type": "omp_ninfer_release_receipt_audit", "schema_version": 1,
            "release": release, "source_release": predecessor, "status": phase,
            "as_of": _date(as_of), "policy": " ".join(policy), "files": rows, "bindings": bindings}


def ready_errors(root: Path, release: str, *, phase: str, check_pins: bool) -> list[str]:
    """Require a staged audit, and with pins prove its exact committed input tree."""
    from verify_release import product_version

    if (product_version(release) or (0, 0, 0)) < (0, 20, 0) or phase == "draft":
        return []
    label = f"releases/{release}/{AUDIT}"
    try:
        if phase not in ("candidate", "acceptance"):
            raise Refusal("receipt audit ready phase must be candidate or acceptance")
        path = Path(root) / label
        if not path.is_file():
            raise Refusal(f"{label} is required")
        data = path.read_bytes()
        audit = json.loads(data)
        if not isinstance(audit, dict) or audit.get("artifact_type") != "omp_ninfer_release_receipt_audit" \
                or audit.get("schema_version") != 1 or audit.get("release") != release:
            raise Refusal(f"{label} must be a schema-1 receipt audit for {release}")
        statuses = PHASES if phase == "candidate" else ("composed-final",)
        if audit.get("status") not in statuses:
            raise Refusal(f"{label}.status must be {' or '.join(statuses)}")
        if check_pins:
            try:
                shallow = git(root, "rev-parse", "--is-shallow-repository").strip()
                commit = git(root, "log", "-1", "--format=%H", "--", label).strip()
            except subprocess.CalledProcessError as error:
                raise Refusal("receipt audit recomputation requires its committed git history") from error
            if shallow != "false":
                raise Refusal("receipt audit recomputation requires complete git history")
            if not commit:
                raise Refusal("receipt audit recomputation requires its committed git history")
            committed = _Tree(root, commit).read(label)
            regenerated = _bytes(generate_audit(root, release, phase=audit["status"],
                                               as_of=_date(audit.get("as_of")), at=commit))
            if committed != data or regenerated != committed:
                raise Refusal(f"{label} recomputation mismatch at its last-changing commit")
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        return [f"receipt audit: {error}"]
    return []


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument("--as-of")
    parser.add_argument("--at")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        tree = _Tree(root, args.at)
        path = f"releases/{args.release}/{AUDIT}"
        as_of = args.as_of
        if args.check and as_of is None:
            as_of = tree.document(path).get("as_of")
        audit = generate_audit(root, args.release, phase=args.phase, as_of=as_of, at=tree.at)
        data = _bytes(audit)
        if args.check:
            if tree.read(path) != data:
                raise Refusal("committed receipt audit differs from recomputation")
        else:
            qualification_path = f"releases/{args.release}/qualification.json"
            qualification = tree.document(qualification_path)
            qualification["receipt_audit"] = {"repository_path": path, "sha256": _sha(data)}
            atomic_write(Path(root) / path, data)
            atomic_write_json(Path(root) / qualification_path, qualification)
        print(json.dumps({"release": args.release, "phase": args.phase,
                          "files": len(audit["files"]), "scalar_bindings": len(audit["bindings"])}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"receipt audit: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
