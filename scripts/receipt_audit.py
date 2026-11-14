#!/usr/bin/env python3
"""Generate or check a release's lane-stage or composed-final receipt inventory.

``--at`` reads immutable git inputs instead of the working tree. ``--check`` never
writes; without it, the audit and its qualification binding are replaced atomically.
The audit inventories its own path without hashing its output, and omits the
qualification receipt_audit edge from the scalar inventory. ``unadmitted_kept``
returns every unbound predecessor copy for staging tools without writing.
``--prune-unbound`` plans lane-stage deletions and the resulting audit together,
never removes release notes or currently referenced files, and logs each removal.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlsplit

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


def _references(value: Any, pointer: str = "") -> Iterator[tuple[str, tuple[str, str]]]:
    if isinstance(value, dict):
        for field in ("summary", "path", "repository_path"):
            path = value.get(field)
            if isinstance(path, str) and (path.startswith("releases/")
                                          or isinstance(value.get("sha256"), str)):
                digest = value.get("sha256")
                if not isinstance(digest, str):
                    raise Refusal(f"component reference must bind sha256: {path}")
                yield pointer + "/" + field, (path, digest)
        for field, child in value.items():
            yield from _references(child, pointer + "/" + field)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _references(child, pointer + "/" + str(index))


def _reference_path(value: str, directory: str) -> str | None:
    parsed = urlsplit(value.replace("\\", "/"))
    if parsed.scheme or parsed.netloc:
        return None
    path = posixpath.normpath(unquote(parsed.path))
    if not path.startswith("releases/"):
        path = posixpath.normpath(directory + "/" + path)
    if not path.startswith("releases/"):
        raise Refusal(f"component file reference must stay inside releases: {value}")
    return path


def _component_rows(manifest: dict[str, Any]) -> dict[str, tuple[dict[str, Any], bool]]:
    rows = {}
    for component, value in manifest.get("components", {}).items():
        candidates = value if isinstance(value, list) else [value]
        for row in candidates:
            if not isinstance(row, dict):
                continue
            name = row["id"] if isinstance(value, list) else component
            if name in rows:
                raise Refusal(f"ambiguous component row: {name}")
            rows[name] = row, component == "ninfer_variants"
    return rows


def _relocated(before: Any, after: Any, old_prefix: str, new_prefix: str) -> Any:
    """Allow only release-local path movement and its matching immutable URL."""
    from verify_release import PRODUCT_RAW_URL_RE

    if isinstance(before, dict) and isinstance(after, dict):
        expected = {}
        for key, value in before.items():
            current = after.get(key)
            if key in ("summary", "path", "repository_path") and isinstance(value, str) \
                    and value.startswith(old_prefix) \
                    and current == new_prefix + value.removeprefix(old_prefix):
                expected[key] = current
            elif key in ("public_url", "url") and isinstance(current, str):
                match = PRODUCT_RAW_URL_RE.fullmatch(current)
                target = next((after.get(field) for field in ("summary", "path", "repository_path")
                               if isinstance(after.get(field), str)), None)
                old_target = next((before.get(field) for field in ("summary", "path", "repository_path")
                                   if isinstance(before.get(field), str)), None)
                allowed = (old_target, new_prefix + old_target.removeprefix(old_prefix)) \
                    if isinstance(old_target, str) and old_target.startswith(old_prefix) else ()
                expected[key] = current if match and match[2] == target and target in allowed else value
            else:
                expected[key] = _relocated(value, current, old_prefix, new_prefix)
        return expected
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [_relocated(old, new, old_prefix, new_prefix) for old, new in zip(before, after)]
    return before


def _component_references(tree: _Tree, prefix: str, name: str,
                          row: dict[str, Any]) -> dict[str, tuple[str, str]]:
    references = dict(_references(row))
    if name == "ninfer":
        # The container component predates row-local qualification bindings. Its
        # behavioral and packaging evidence live in these schema-owned sections.
        composition = tree.document(prefix + "qualification.json").get("composition", {})
        for field in ("behavioral_qualification", "local_release_packaging"):
            references.update(_references(composition.get(field), "/composition/" + field))
    result = {}
    for field, (path, digest) in references.items():
        local = _reference_path(path, prefix.rstrip("/"))
        if local is not None:
            result[field] = local, digest
    return result


def _carried(tree: _Tree, release: str, predecessor: str, manifest: dict[str, Any],
             previous: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], list[str], bool]:
    from verify_release import PRODUCT_RAW_URL_RE, unchanged_native_variant

    old_prefix, new_prefix = f"releases/{predecessor}/", f"releases/{release}/"
    old_rows = _component_rows(previous)
    carried, in_place, policies = {}, {}, []
    runtime_carried = False
    for name, (row, native) in _component_rows(manifest).items():
        old = old_rows.get(name, (None, False))[0]
        if old is None or native and not unchanged_native_variant(row, old):
            continue
        expected = _relocated(old, row, old_prefix, new_prefix)
        qualification = row.get("qualification", {})
        if native and qualification.get("public_url") is not None:
            url = qualification.get("public_url")
            match = PRODUCT_RAW_URL_RE.fullmatch(url) if isinstance(url, str) else None
            if match is None or match[2] != qualification.get("summary"):
                raise Refusal(f"{name}: carried summary URL must bind its summary")
        if row != expected:
            if native:
                raise Refusal(f"{name}: carried manifest row must remain byte-identical except relocation")
            continue
        runtime_carried |= name == "ninfer"
        old_references = _component_references(tree, old_prefix, name, old)
        new_references = _component_references(tree, new_prefix, name, row)
        if not new_references:
            continue
        tag = row.get("release_tag") or row.get("upstream_tag") or row.get("revision") or name
        source = row.get("source_commit") or row.get("upstream_commit") or row.get("revision")
        subject = tag + (f" (source {source[:8]})" if source else "")
        reason_prefix = f"Carried component, unchanged since {predecessor}"
        reason = (f"{reason_prefix}: {subject} keeps its "
                  "byte-identical published row and qualification; no fresh hardware qualification "
                  "or new-client/product-route acceptance is claimed.")
        references = []
        for field, value in new_references.items():
            if field not in old_references:
                raise Refusal(f"{name}: carried binding has no predecessor: {field}")
            references.append((old_references[field], value))
        if native and row.get("checksums_sha256") is not None:
            checksum = f"qualification/{name}.SHA256SUMS"
            references.append(((old_prefix + checksum, old["checksums_sha256"]),
                               (new_prefix + checksum, row["checksums_sha256"])))
        local_binding = False
        # Forward reachability is a least fixpoint seeded only by unchanged
        # component rows. References in unadmitted copies never become roots.
        visited = set()
        while references:
            (old_path, old_sha), (path, digest) = references.pop()
            data = tree.read(path)
            if _sha(data) != digest or old_sha != digest or data != tree.read(old_path):
                raise Refusal(f"carried file is not byte-identical to {predecessor}: {path}")
            if (old_path, path) in visited:
                continue
            visited.add((old_path, path))
            if path.startswith(new_prefix):
                carried[path.removeprefix(new_prefix)] = reason
                local_binding = True
            elif path.startswith(old_prefix):
                in_place[path.removeprefix(old_prefix)] = (
                    f"{reason_prefix}: bound in place at {path} by the carried {tag} "
                    "row (hash unchanged); not copied into this release.")
            if path.endswith(".json"):
                for _, (reference, sha) in _references(json.loads(data)):
                    old_child = _reference_path(reference, posixpath.dirname(old_path))
                    child = _reference_path(reference, posixpath.dirname(path))
                    if old_child is not None and child is not None:
                        references.append(((old_child, sha), (child, sha)))
        if native:
            lane = name.removesuffix("-windows-native")
            label = re.sub(r"([a-zA-Z]+)([0-9]+)", lambda m: m[1].upper() + " " + m[2], lane)
            channel = re.search(r"-(beta\.[0-9]+|preview\.[0-9]+)$", tag)
            label += " " + (channel[1] if channel else tag)
        else:
            label = name + " " + tag
        binding = "as kept files." if local_binding else "bound in place."
        policies.append(f"The carried {label} component keeps its byte-identical {predecessor} "
                        f"row and qualification {binding}")
    return carried, in_place, policies, runtime_carried


def _inventory(tree: _Tree, release: str) -> tuple[
    str, dict[str, str], dict[str, str], list[str], dict[str, str], dict[str, str], bool,
]:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", release):
        raise Refusal(f"invalid product release: {release}")
    predecessor, previous = _predecessor(tree, release)
    old_prefix, new_prefix = f"releases/{predecessor}/", f"releases/{release}/"
    manifest = tree.document(new_prefix + "manifest.json")
    if manifest.get("release") != release:
        raise Refusal("manifest release must match the requested release")
    carried, in_place, policies, runtime_carried = _carried(tree, release, predecessor, manifest, previous)
    before, after = tree.files(predecessor), tree.files(release)
    if old_prefix + AUDIT in tree.paths:
        before[AUDIT] = _sha(tree.read(old_prefix + AUDIT))
    # Its path is inventoried, but the output cannot compare or bind its own bytes.
    after[AUDIT] = ""
    return predecessor, carried, in_place, policies, before, after, runtime_carried


def _unadmitted(before: dict[str, str], after: dict[str, str], carried: dict[str, str],
                runtime_carried: bool) -> list[str]:
    return sorted(name for name in before.keys() & after.keys()
                  if before[name] == after[name] and name not in GENERATED and name not in carried
                  and (name != "qualification/runtime-base.json" or runtime_carried))


def unadmitted_kept(root: Path, release: str) -> list[str]:
    """Return all unbound predecessor copies, release-relative, without writing.

    A re-cut runtime may reuse the independently admitted immutable base receipt.
    A fully carried runtime must bind its retained files like any other component.
    """
    _, carried, _, _, before, after, runtime_carried = _inventory(_Tree(root), release)
    return _unadmitted(before, after, carried, runtime_carried)


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


def _generate_audit(tree: _Tree, release: str, *, phase: str,
                    as_of: str | None = None) -> dict[str, Any]:
    if phase not in PHASES:
        raise Refusal("audit phase must be lane-stage or composed-final")
    predecessor, carried, in_place, policies, before, after, runtime_carried = _inventory(tree, release)
    old_prefix, new_prefix = f"releases/{predecessor}/", f"releases/{release}/"
    unadmitted = _unadmitted(before, after, carried, runtime_carried)
    if unadmitted:
        raise Refusal("unadmitted predecessor bytes: " + ", ".join(unadmitted))
    rows = []
    for name in sorted(before.keys() | after.keys()):
        disposition = ("added" if name not in before else "dropped" if name not in after else
                       "kept" if before[name] == after[name] else "replaced")
        if disposition == "kept" and name not in GENERATED:
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
    # The audit binds itself into qualification.json, so the manifest's hash of that document
    # is downstream of the audit and cannot be part of what the audit inventories. Audits up to
    # v0.19.0 recorded it (from the tree before their own binding existed) and stay reproducible
    # as published; from v0.20.0 it is excluded, like the binding itself, so the hash chain can
    # be closed in the same commit that carries the audit.
    from verify_release import product_version
    self_referential = ({"manifest.json": {"/qualification/summary_sha256"}}
                        if (product_version(release) or (0, 0, 0)) >= (0, 20, 0) else {})
    bindings = []
    for name in ("manifest.json", "qualification.json", "compatibility.json"):
        old, new = ({key: value for key, value in _leaves(tree.document(prefix + name))
                     if key != "/receipt_audit" and not key.startswith("/receipt_audit/")
                     and key not in self_referential.get(name, ())}
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


def generate_audit(root: Path, release: str, *, phase: str, as_of: str | None = None,
                   at: str | None = None) -> dict[str, Any]:
    """Recompute an inventory without writing either authority."""
    return _generate_audit(_Tree(root, at), release, phase=phase, as_of=as_of)


def _prune_references(tree: _Tree, release: str, names: list[str]) -> list[str]:
    prefix = f"releases/{release}/"
    targets = {prefix + name for name in names}
    references = []
    for name in ("manifest.json", "qualification.json", "compatibility.json"):
        document = prefix + name
        for pointer, value in _leaves(tree.document(document)):
            if not isinstance(value, str):
                continue
            parsed = urlsplit(value.replace("\\", "/"))
            if parsed.scheme or parsed.netloc:
                path = unquote(parsed.path)
                matches = [target for target in targets if path.endswith("/" + target)]
            else:
                path = posixpath.normpath(unquote(parsed.path))
                if not path.startswith("releases/"):
                    path = posixpath.normpath(prefix + path)
                matches = [path] if path in targets else []
            for target in targets:
                if target in matches:
                    continue
                relative = target.removeprefix(prefix)
                if re.search(r"(?<![\w./-])(?:" + re.escape(target) + "|" + re.escape(relative)
                             + r")(?![\w./-])", value):
                    matches.append(target)
            for target in matches:
                references.append(f"{target} referenced by {document}#{pointer}")
    return sorted(references)


def _plan_pruning(tree: _Tree, release: str, as_of: str | None) -> tuple[
    dict[str, Any], list[tuple[str, str]],
]:
    _, carried, _, _, before, after, runtime_carried = _inventory(tree, release)
    names = [name for name in _unadmitted(before, after, carried, runtime_carried)
             if name != "NINFER_RELEASE_NOTES.md"]
    references = _prune_references(tree, release, names)
    if references:
        raise Refusal("cannot prune referenced files: " + "; ".join(references))
    excluded = {f"releases/{release}/{name}" for name in names}
    tree.paths = [path for path in tree.paths if path not in excluded]
    for path in excluded:
        tree.cache.pop(path, None)
    # Complete the audit, including dates and scalar inventories, against the
    # planned tree before the first filesystem effect. Notes still refuse here.
    audit = _generate_audit(tree, release, phase="lane-stage", as_of=as_of)
    reasons = {row["file"]: row["reason"] for row in audit["files"]}
    return audit, [(name, reasons[name]) for name in names]


def _apply_pruning(root: Path, release: str, deletions: list[tuple[str, str]]) -> None:
    directory = Path(root) / "releases" / release
    parents = set()
    for name, reason in deletions:
        path = directory / name
        path.unlink()
        print(f"pruned releases/{release}/{name}: {reason}")
        parent = path.parent
        while parent != directory:
            parents.add(parent)
            parent = parent.parent
    for parent in sorted(parents, key=lambda path: (-len(path.parts), path.as_posix())):
        if not any(parent.iterdir()):
            parent.rmdir()


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
    parser.add_argument("--prune-unbound", action="store_true",
                        help="plan and log removal of unbound lane-stage copies; never remove notes")
    args = parser.parse_args(argv)
    try:
        if args.prune_unbound and (args.check or args.at is not None or args.phase != "lane-stage"):
            raise Refusal("--prune-unbound requires lane-stage without --check or --at")
        tree = _Tree(root, args.at)
        path = f"releases/{args.release}/{AUDIT}"
        as_of = args.as_of
        if args.check and as_of is None:
            as_of = tree.document(path).get("as_of")
        deletions = []
        if args.prune_unbound:
            audit, deletions = _plan_pruning(tree, args.release, as_of)
        else:
            audit = _generate_audit(tree, args.release, phase=args.phase, as_of=as_of)
        data = _bytes(audit)
        if args.check:
            if tree.read(path) != data:
                raise Refusal("committed receipt audit differs from recomputation")
        else:
            qualification_path = f"releases/{args.release}/qualification.json"
            qualification = tree.document(qualification_path)
            qualification["receipt_audit"] = {"repository_path": path, "sha256": _sha(data)}
            # Finish serializing both writes before deleting any planned copy.
            _bytes(qualification)
            _apply_pruning(root, args.release, deletions)
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
