#!/usr/bin/env python3
"""Create resumable product-release commits without publishing or rewriting history."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_io import atomic_write, atomic_write_json, git
from release_plan import (COMPONENT_IDS, initial_plan, latest_ready_manifest, load_plan,
                          manifest_components, plan_errors)

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("stage", "lane-pin", "guide", "compose", "platform-pin", "acceptance-pin",
          "audit", "manifest-pin")
SUBJECTS = {
    "stage": "chore(release): stage {release} lane receipts",
    "lane-pin": "chore(release): pin {release} lane receipts",
    "guide": "docs(quickstart): retarget guide to {release}",
    "compose": "chore(release): compose {release} acceptance",
    "platform-pin": "chore(release): pin {release} platform receipts",
    "acceptance-pin": "chore(release): pin {release} composed acceptance",
    "audit": "chore(release): audit {release} receipts",
    "manifest-pin": "chore(release): pin {release} manifest evidence",
}
PIN_SOURCES = {"lane-pin": "stage", "platform-pin": "compose",
               "acceptance-pin": "platform-pin", "manifest-pin": "audit"}
ROUTES = ("rtx5090-container-host", "rtx5090-macos-client", "rtx5090-windows-client",
          "rtx4090-native", "rtx3090-native")
PATH_INPUTS = ("stage_input", "notes", "client_component", "runtime_publication",
               "window_root", "reviews", "values")
MAPPED_INPUTS = ("bundles", "lane_receipts", "assets", "native_publications")
STAGE_VALUE_OPTIONS = {
    "release_tag", "source_tag", "source_commit", "binary_sha", "archive_sha",
    "source_archive_sha", "source_archive", "checksums", "sbom_sha", "image_digest",
    "runtime_receipt_release", "archive_name", "profile_from", "config_sha", "upstream_commit",
    "model_revision", "model_sha256", "model_bytes", "profile_template_dir",
}
STAGE_FILE_OPTIONS = {"source_archive", "checksums", "profile_template_dir"}


class ReleaseError(ValueError):
    """A release input, history or tool invocation cannot safely proceed."""


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReleaseError(f"{path.name} must contain a JSON object")
    return value


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def input_hash(path: Path) -> Any:
    if path.is_file():
        return file_sha(path)
    if path.is_dir():
        return {child.relative_to(path).as_posix(): file_sha(child)
                for child in sorted(path.rglob("*")) if child.is_file()}
    raise ReleaseError(f"missing private input: {path}")


def dirty_paths(root: Path) -> set[str]:
    fields = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        paths.add(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            paths.add(fields[index])
            index += 1
    return paths


def group_commits(root: Path, release: str) -> dict[str, dict[str, str]]:
    """Read first-parent trailers; state cannot manufacture a completed group."""
    fields = git(root, "log", "--first-parent", "--reverse",
                 "--format=%H%x00%s%x00%(trailers:only,unfold=true)%x00").split("\0")
    records: dict[str, dict[str, str]] = {}
    for index in range(0, len(fields) - 2, 3):
        commit, subject, text = (field.strip() for field in fields[index:index + 3])
        trailers: dict[str, list[str]] = {}
        for line in text.splitlines():
            key, separator, value = line.partition(":")
            if separator:
                trailers.setdefault(key, []).append(value.strip())
        if release not in trailers.get("Release", []):
            continue
        if (subject == f"chore(release): plan {release}"
                and trailers == {"Release": [release]}):
            continue
        if trailers.get("Release") != [release] or len(trailers.get("Release-Step", [])) != 1:
            raise ReleaseError(f"invalid release trailers at {commit}")
        group = trailers["Release-Step"][0]
        if group not in GROUPS or group in records or group != GROUPS[len(records)]:
            raise ReleaseError(f"out-of-order or duplicate Release-Step at {commit}: {group}")
        if subject != SUBJECTS[group].format(release=release):
            raise ReleaseError(f"unexpected {group} subject at {commit}")
        source = PIN_SOURCES.get(group)
        expected = [records[source]["commit"]] if source else []
        if trailers.get("Pins", []) != expected:
            raise ReleaseError(f"{group} Pins trailer does not name its {source or 'absent'} input")
        records[group] = {"commit": commit, "pins": expected[0] if expected else ""}
    return records


def init_plan(root: Path, release: str, *, recut: list[str] | tuple[str, ...] = (),
              client_tag: str | None = None, decisions: list[str] | tuple[str, ...] = (),
              no_commit: bool = False) -> str | None:
    plan = initial_plan(root, release, recut=recut, client_tag=client_tag, decisions=decisions)
    path = Path(root) / "releases" / release / "plan.json"
    if path.exists():
        raise ReleaseError(f"plan init refuses an existing plan: releases/{release}/plan.json")
    dirty = dirty_paths(root)
    if dirty:
        raise ReleaseError("plan init requires a clean tree: " + ", ".join(sorted(dirty)))
    created = not path.parent.exists()
    atomic_write_json(path, plan)
    errors = plan_errors(root, release)
    if errors:
        path.unlink()
        if created:
            path.parent.rmdir()
        raise ReleaseError("plan init result failed plan check:\n" + "\n".join(errors))
    if no_commit:
        return None
    return commit_plan(root, release)


def commit_plan(root: Path, release: str) -> str:
    load_plan(root, release)
    path = f"releases/{release}/plan.json"
    foreign = dirty_paths(root) - {path}
    if foreign:
        raise ReleaseError("plan commit refuses other dirty paths: " + ", ".join(sorted(foreign)))
    errors = plan_errors(root, release)
    if errors:
        raise ReleaseError("plan commit failed plan check:\n" + "\n".join(errors))
    git(root, "add", "--", path)
    git(root, "commit", "-m", f"chore(release): plan {release}", "-m", f"Release: {release}")
    return git(root, "rev-parse", "HEAD").strip()


class ReleaseDriver:
    def __init__(self, root: Path, release: str, options: argparse.Namespace | None = None):
        self.root = Path(root).resolve()
        self.release = release
        self.plan = load_plan(self.root, release)
        self.plan_path = self.root / "releases" / release / "plan.json"
        self.plan_bytes = self.plan_path.read_bytes()
        self.plan_sha = hashlib.sha256(self.plan_bytes).hexdigest()
        self.local = self.root / ".release-state" / release
        self.state_path = self.root / ".release-state" / f"{release}.json"
        self.state = (read_json(self.state_path) if self.state_path.is_file() else
                      {"schema_version": 1, "release": release, "private": {}, "groups": {},
                       "options": {}})
        if self.state.get("schema_version") != 1 or self.state.get("release") != release:
            raise ReleaseError("local release state has the wrong schema or release")
        self.records = group_commits(self.root, release)
        for group, cached in self.state["groups"].items():
            commit = cached.get("commit")
            if commit and self.records.get(group, {}).get("commit") != commit:
                raise ReleaseError(f"rewritten history under recorded {group} commit {commit}")
        if options is not None:
            self.set_options(options)

    def set_options(self, options: argparse.Namespace) -> None:
        private = self.state["private"]
        for name in PATH_INPUTS:
            value = getattr(options, name, None)
            if value is not None:
                key = ("compose_notes" if name == "notes"
                       and getattr(options, "command", None) == "finalize" else name)
                private[key] = str(Path(value).resolve())
        for name in MAPPED_INPUTS:
            values = getattr(options, name, None)
            if values is not None:
                parsed = {}
                for item in values:
                    key, separator, value = item.partition("=")
                    if not separator or not key or not value or key in parsed:
                        raise ReleaseError(f"--{name.replace('_', '-')} requires unique NAME=PATH entries")
                    parsed[key] = str(Path(value).resolve())
                private[name] = parsed
        for name in ("as_of", "measurement_prefix"):
            value = getattr(options, name, None)
            if value is not None:
                self.state["options"][name] = value
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", self.prefix) is None:
            raise ReleaseError("--measurement-prefix must be a public filename prefix, not a path")
        from verify_release import PRIVATE_MARKERS
        if any(marker in self.prefix for marker in PRIVATE_MARKERS):
            raise ReleaseError("--measurement-prefix contains a private marker")
        date = self.state["options"].get("as_of")
        if date is not None:
            from datetime import date as calendar_date
            try:
                calendar_date.fromisoformat(date)
            except ValueError as error:
                raise ReleaseError("--as-of must be an ISO calendar date") from error

    @property
    def prefix(self) -> str:
        return self.state["options"].get("measurement_prefix", self.release.replace(".", ""))

    def save(self) -> None:
        self.state["plan_sha256"] = self.plan_sha
        atomic_write_json(self.state_path, self.state)

    def check_plan(self) -> None:
        errors = plan_errors(self.root, self.release)
        if errors:
            raise ReleaseError("invalid release plan:\n" + "\n".join(errors))

    def private_path(self, name: str) -> Path:
        value = self.state["private"].get(name)
        if value is None:
            raise ReleaseError(f"missing private input: --{name.replace('_', '-')}")
        path = Path(value)
        if not path.exists():
            raise ReleaseError(f"missing private input for --{name.replace('_', '-')}: {path}")
        return path

    def declared(self, group: str, path: str) -> bool:
        if group == "guide":
            return path == "docs/QUICKSTART.md"
        if path.startswith(f"releases/{self.release}/"):
            return True
        if group in ("lane-pin", "compose", "platform-pin"):
            if (path in ("compatibility.json", "docs/COMPATIBILITY.md",
                         "examples/manual-tunnel/start-ninfer.sh",
                         "examples/manual-tunnel/stop-ninfer.sh") or path.startswith("profiles/")):
                return True
        return group == "compose" and path.startswith(f"docs/measurements/{self.prefix}-")

    def check_dirty(self, group: str | None) -> set[str]:
        paths = dirty_paths(self.root)
        guide_input = ({"docs/QUICKSTART.md"} if group in ("stage", "lane-pin")
                       and "guide" not in self.records else set())
        foreign = sorted(path for path in paths if path not in guide_input
                         and (group is None or not self.declared(group, path)))
        if foreign:
            raise ReleaseError("dirty file outside declared paths: " + ", ".join(foreign))
        return paths - guide_input

    def restore(self, group: str, dirty: set[str]) -> None:
        """Restore only this group's paths, retaining the operator's current plan."""
        if not dirty:
            return
        head_paths = {}
        for entry in git(self.root, "ls-tree", "-r", "-z", "HEAD", "--", *sorted(dirty)).split("\0"):
            if entry:
                metadata, _, name = entry.partition("\t")
                head_paths[name] = metadata.split()[0]
        indexed = set(filter(None, git(self.root, "ls-files", "-z", "--",
                                       *sorted(dirty)).split("\0")))
        if indexed:
            git(self.root, "restore", "--source=HEAD", "--staged", "--", *sorted(indexed))
        for name in sorted(dirty):
            path = self.root / name
            if name in head_paths:
                data = subprocess.run(["git", "show", f"HEAD:{name}"], cwd=self.root,
                                      check=True, capture_output=True).stdout
                atomic_write(path, data)
                path.chmod(0o755 if head_paths[name] == "100755" else 0o644)
            elif path.is_file() or path.is_symlink():
                path.unlink()
        if group == "stage":
            atomic_write(self.plan_path, self.plan_bytes)

    def tools(self, group: str) -> list[str]:
        if group == "stage":
            tools = ["stage_release.py", "aggregate_qualification.py", "rebind_release.py", "receipt_audit.py"]
            if self.recut_native():
                tools += ["bind_native_variant.py"]
            return tools
        if group == "guide":
            return ["retarget_guide.py"]
        if group == "compose":
            return ["collect_route_evidence.py", "review_ledger.py", "compose_route_acceptance.py",
                    "rebind_release.py"]
        return ["receipt_audit.py"] if group == "audit" else ["rebind_release.py"]

    def require_tool(self, name: str) -> Path:
        path = self.root / "scripts" / name
        if not path.is_file():
            raise ReleaseError(f"missing release tool: scripts/{name}")
        return path

    def tool(self, name: str, *arguments: str, capture: bool = False) -> str:
        path = self.require_tool(name)
        result = subprocess.run([sys.executable, str(path), *map(str, arguments)], cwd=self.root,
                                stdout=subprocess.PIPE if capture else None, text=True,
                                encoding="utf-8")
        if result.returncode:
            raise ReleaseError(f"{name} failed (exit {result.returncode})")
        return result.stdout or ""

    def recut_native(self) -> list[dict[str, Any]]:
        return [row for row in self.plan["components"]
                if row["id"] != COMPONENT_IDS[0] and row["disposition"] == "recut"]

    def client_component_path(self) -> Path:
        if "client_component" in self.state["private"]:
            return self.private_path("client_component")
        if self.plan["client"]["disposition"] == "updated":
            raise ReleaseError("updated client requires --client-component")
        path = (self.root / "releases" / self.plan["predecessor"] / "qualification" / "client-components.json")
        if not path.is_file():
            raise ReleaseError("carried client requires predecessor descriptor: " + path.relative_to(self.root).as_posix())
        return path

    def stage_values(self) -> dict[str, Any]:
        runtime = read_json(self.root / "releases" / self.plan["predecessor"] / "manifest.json")[
            "components"]["ninfer"]
        values = {
            "release_tag": runtime["release_tag"], "source_commit": runtime["source_commit"],
            "source_tag": urlsplit(runtime["source_archive_url"]).path.split("/")[-2],
            "binary_sha": runtime["server_binary_sha256"],
            "archive_sha": runtime["binary_archive_sha256"],
            "source_archive_sha": runtime["source_archive_sha256"], "sbom_sha": runtime["sbom_sha256"],
            "image_digest": runtime["oci_manifest_digest"],
            "runtime_receipt_release": runtime["runtime_receipt_release"],
            "archive_name": runtime["binary_archive_url"].rsplit("/", 1)[-1],
            "keep_deployment_profile": True,
        }
        supplied = (read_json(self.private_path("stage_input"))
                    if "stage_input" in self.state["private"] else {})
        if set(supplied) - (STAGE_VALUE_OPTIONS | {"keep_deployment_profile", "require_clean_client"}):
            raise ReleaseError("--stage-input contains an unsupported stage_release.py option")
        runtime_plan = next(row for row in self.plan["components"] if row["id"] == COMPONENT_IDS[0])
        if runtime_plan["disposition"] == "recut":
            required = {"source_tag", "binary_sha", "archive_sha", "source_archive_sha", "sbom_sha",
                        "image_digest", "runtime_receipt_release", "source_archive", "checksums"}
            if required - set(supplied):
                raise ReleaseError("re-cut runtime requires --stage-input fields: "
                                   + ", ".join(sorted(required - set(supplied))))
            values.pop("archive_name")
        if "config_sha" in supplied:
            values.pop("keep_deployment_profile")
        values.update(supplied)
        values.update(release_tag=runtime_plan["release_tag"], source_commit=runtime_plan["source_commit"])
        for name in STAGE_FILE_OPTIONS & values.keys():
            path = Path(values[name])
            if not path.is_absolute():
                path = self.private_path("stage_input").parent / path
            values[name] = str(path.resolve())
        return values

    def inputs_digest(self, group: str, head: str) -> str:
        names = ({"stage_input", "notes", "client_component", "runtime_publication", "bundles",
                  "lane_receipts", "assets", "native_publications"} if group == "stage" else
                 {"window_root", "reviews", "values", "compose_notes"} if group == "compose" else set())
        private = {}
        for name in sorted(names & self.state["private"].keys()):
            value = self.state["private"][name]
            paths = value if isinstance(value, dict) else {"input": value}
            private[name] = {key: {"path": path, "sha256": input_hash(Path(path))}
                             for key, path in sorted(paths.items())}
        if group == "stage":
            self.validate_stage_inputs()
            values = self.stage_values()
            private["stage_files"] = {key: input_hash(Path(values[key]))
                                      for key in sorted(STAGE_FILE_OPTIONS & values.keys())}
            private["client_descriptor_sha256"] = file_sha(self.client_component_path())
        elif group == "guide":
            private["guide_sha256"] = file_sha(self.root / "docs" / "QUICKSTART.md")
        payload = {"plan_sha256": self.plan_sha, "HEAD": head, "private": private,
                   "options": self.state["options"],
                   "tools": {name: file_sha(self.require_tool(name)) for name in self.tools(group)}}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def validate_stage_inputs(self) -> None:
        private = self.state["private"]
        expected = {row["id"].split("-", 1)[0] for row in self.recut_native()}
        supplied = set(private.get("bundles", {}))
        if expected != supplied:
            raise ReleaseError("--bundle lanes disagree with plan: missing "
                               + ", ".join(sorted(expected - supplied)) + "; carried or unknown "
                               + ", ".join(sorted(supplied - expected)))
        publications = set(private.get("native_publications", {}))
        if expected != publications:
            raise ReleaseError("--native-publication lanes disagree with plan: missing "
                               + ", ".join(sorted(expected - publications)) + "; carried or unknown "
                               + ", ".join(sorted(publications - expected)))
        runtime = next(row for row in self.plan["components"] if row["id"] == COMPONENT_IDS[0])
        if runtime["disposition"] == "recut":
            if "runtime_publication" not in private:
                raise ReleaseError("re-cut rtx5090-container requires --runtime-publication")
            self.private_path("runtime_publication")
            if "rtx5090" not in private.get("lane_receipts", {}):
                raise ReleaseError("re-cut rtx5090-container requires --lane-receipt rtx5090=PATH")
        elif "runtime_publication" in private:
            raise ReleaseError("carried rtx5090-container refuses --runtime-publication")
        if set(private.get("lane_receipts", {})) - {"rtx5090"}:
            raise ReleaseError("--lane-receipt accepts only rtx5090; native receipts belong in bundles")
        self.client_component_path()

    def outputs(self, group: str) -> dict[str, str]:
        names = git(self.root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
        return {name: file_sha(self.root / name) for name in sorted(set(names))
                if name and self.declared(group, name) and (self.root / name).is_file()}

    def required_outputs(self, group: str) -> list[Path]:
        release_root = self.root / "releases" / self.release
        common = [release_root / name for name in ("manifest.json", "qualification.json", "compatibility.json")]
        if group == "guide":
            return [self.root / "docs" / "QUICKSTART.md"]
        if group in ("stage", "audit"):
            return common + [release_root / "qualification" / "receipt-audit.json"]
        if group == "compose":
            return common + [release_root / "review" / "runtime-ledger.json",
                             release_root / "acceptance" / "composed-external-installation.json",
                             release_root / "acceptance" / "documented-routes.json"]
        return common

    def check_ledger(self) -> None:
        path = self.root / "releases" / self.release / "review" / "runtime-ledger.json"
        if path.is_file() and read_json(path).get("product_tooling", {}).get("stage_commit") != self.records["guide"]["commit"]:
            raise ReleaseError("review ledger stage_commit is not the guide candidate")

    def stage(self) -> None:
        values = self.stage_values()
        arguments = ["--from", self.plan["predecessor"], "--release", self.release]
        for name, value in values.items():
            if name in ("keep_deployment_profile", "require_clean_client"):
                if type(value) is not bool:
                    raise ReleaseError(f"stage option {name} must be boolean")
                if value:
                    arguments.append("--" + name.replace("_", "-"))
            else:
                arguments += ["--" + name.replace("_", "-"), str(value)]
        receipts = self.state["private"].get("lane_receipts", {})
        if "rtx5090" in receipts:
            arguments += ["--lane-receipt", receipts["rtx5090"]]
        arguments += ["--omp-component", str(self.client_component_path())]
        if next(row for row in self.plan["components"] if row["id"] == COMPONENT_IDS[0])["disposition"] == "recut" and "rtx5090" not in receipts:
            raise ReleaseError("re-cut runtime requires --lane-receipt rtx5090=PATH")
        # The stager requires an absent directory. The plan is an input, not draft residue.
        try:
            self.plan_path.unlink()
            for directory in sorted(self.plan_path.parent.rglob("*"), reverse=True):
                if directory.is_dir() and not any(directory.iterdir()):
                    directory.rmdir()
            self.plan_path.parent.rmdir()
            self.tool("stage_release.py", *arguments)
        finally:
            atomic_write(self.plan_path, self.plan_bytes)
        ledger = self.plan_path.parent / "review" / "runtime-ledger.json"
        if ledger.is_file():
            ledger.unlink()  # A copied predecessor council cannot review this candidate.
        if "notes" in self.state["private"]:
            atomic_write(self.plan_path.parent / "NINFER_RELEASE_NOTES.md", self.private_path("notes").read_bytes())
        bundles = self.state["private"].get("bundles", {})
        expected = {row["id"].split("-", 1)[0] for row in self.recut_native()}
        if set(bundles) != expected:
            raise ReleaseError("--bundle lanes must equal the plan's re-cut native lanes")
        aggregate = ["--release", self.release, "--plan", str(self.plan_path.relative_to(self.root))]
        for lane, path in bundles.items():
            aggregate += ["--bundle", f"{lane}={path}"]
        for role, path in sorted(self.state["private"].get("assets", {}).items()):
            aggregate += ["--asset", f"{role}={path}"]
        try:
            admitted = json.loads(self.tool("aggregate_qualification.py", "admit", *aggregate, capture=True))
        except ValueError as error:
            raise ReleaseError("aggregate_qualification.py admit did not emit one JSON object") from error
        if (not isinstance(admitted, dict) or set(admitted) != {"schema", "lanes"}
                or type(admitted["schema"]) is not int or admitted["schema"] != 1
                or not isinstance(admitted["lanes"], dict) or set(admitted["lanes"]) != expected):
            raise ReleaseError("aggregate_qualification.py admit lanes disagree with the plan")
        for row in self.recut_native():
            lane = row["id"].split("-", 1)[0]
            admission = admitted["lanes"][lane]
            arguments = admission.get("binder_arguments") if isinstance(admission, dict) else None
            if (not isinstance(arguments, list) or not arguments
                    or not all(isinstance(value, str) and value for value in arguments)):
                raise ReleaseError(f"aggregate_qualification.py admit has invalid {lane} binder_arguments")
            for flag, expected_value in (("--release", self.release), ("--lane", lane)):
                if (arguments.count(flag) != 1 or arguments.index(flag) + 1 >= len(arguments)
                        or arguments[arguments.index(flag) + 1] != expected_value):
                    raise ReleaseError(f"aggregate_qualification.py admit {lane} has the wrong {flag}")
            self.tool("bind_native_variant.py", *arguments)
        self.tool("rebind_release.py", "--release", self.release, "--draft")
        publication = (["--runtime-publication", str(self.private_path("runtime_publication"))]
                       if "runtime_publication" in self.state["private"] else [])
        for lane, path in self.state["private"].get("native_publications", {}).items():
            publication += ["--native-publication", f"{lane}={path}"]
        self.tool("aggregate_qualification.py", "compose", *aggregate, *publication)
        self.tool("rebind_release.py", "--release", self.release, "--draft")
        self.audit("lane-stage")

    def audit(self, phase: str) -> None:
        arguments = ["--release", self.release, "--phase", phase]
        if phase == "lane-stage":
            # A staged draft still holds predecessor copies that no successor row binds. The
            # audit tool owns that definition: it removes exactly those and logs each one.
            arguments.append("--prune-unbound")
        if self.state["options"].get("as_of"):
            arguments += ["--as-of", self.state["options"]["as_of"]]
        self.tool("receipt_audit.py", *arguments)

    def _window_attempt_arguments(self) -> list[str]:
        root = self.private_path("window_root").resolve()
        index = root / "window-state.json"
        if not index.exists():
            return []
        state = read_json(index)

        def refuse(message: str) -> None:
            raise ReleaseError(f"window-state.json: {message}")

        if type(state.get("schema")) is not int or state["schema"] != 1:
            refuse("schema must be 1")
        if state.get("release") != self.release:
            refuse("release must match the selected release")
        if state.get("candidate") != self.records["guide"]["commit"]:
            refuse("candidate must equal the guide commit")
        components = manifest_components(read_json(self.plan_path.parent / "manifest.json"))
        expected = [component.split("-", 1)[0] for component in COMPONENT_IDS if component in components]
        lanes = state.get("lanes")
        if not isinstance(lanes, dict) or set(lanes) != set(expected):
            refuse("lanes must equal the manifest's declared lanes")
        arguments: list[str] = []
        for lane in expected:
            record = lanes[lane]
            if not isinstance(record, dict):
                refuse(f"{lane} must be an object")
            accepted = record.get("accepted")
            if type(accepted) is not int or accepted <= 0:
                refuse(f"{lane} accepted attempt must be a positive integer")
            attempts = record.get("attempts")
            if not isinstance(attempts, list):
                refuse(f"{lane} attempts must be an array")
            entries: dict[int, tuple[Path, str]] = {}
            for position, entry in enumerate(attempts):
                label = f"{lane}.attempts[{position}]"
                if not isinstance(entry, dict):
                    refuse(f"{label} must be an object")
                attempt = entry.get("attempt")
                if type(attempt) is not int or attempt <= 0 or attempt in entries:
                    refuse(f"{label} attempt must be a unique positive integer")
                status = entry.get("status")
                if status not in ("planned", "spent-failed", "passed", "retired"):
                    refuse(f"{label} status is invalid")
                directory = entry.get("directory")
                if (not isinstance(directory, str) or not directory or "\\" in directory
                        or PurePosixPath(directory).is_absolute()
                        or PureWindowsPath(directory).drive or PureWindowsPath(directory).root):
                    refuse(f"{label} directory must be a relative POSIX path")
                try:
                    path = (root / directory).resolve()
                except (OSError, RuntimeError) as error:
                    raise ReleaseError(f"window-state.json: {label} directory cannot be resolved") from error
                if not path.is_relative_to(root):
                    refuse(f"{label} directory escapes the window root")
                if not path.is_dir():
                    refuse(f"{label} directory must exist and be a directory")
                entries[attempt] = (path, status)
            if accepted not in entries:
                refuse(f"{lane} accepted attempt has no matching entry")
            path, status = entries[accepted]
            if status not in ("passed", "retired"):
                refuse(f"{lane} accepted attempt must be passed or retired")
            arguments += ["--lane-dir", f"{lane}={path}"]
            for attempt, (path, status) in sorted(entries.items()):
                if attempt < accepted and status == "spent-failed":
                    arguments += ["--corrected-attempt", f"{lane}={path}"]
        return arguments

    def compose(self) -> None:
        self.check_ledger()
        date = self.state["options"].get("as_of")
        if date is None:
            raise ReleaseError("compose requires --as-of (the acceptance completion date)")
        candidate = self.records["guide"]["commit"]
        evidence = self.local / "composition-evidence.json"
        receipts = self.local / "receipts"
        window_arguments = self._window_attempt_arguments()
        if "compose_notes" in self.state["private"]:
            atomic_write(self.plan_path.parent / "NINFER_RELEASE_NOTES.md",
                         Path(self.state["private"]["compose_notes"]).read_bytes())
        self.tool("collect_route_evidence.py", "--release", self.release, "--candidate", candidate,
                  "--window-root", str(self.private_path("window_root")), "--plan",
                  str(self.plan_path.relative_to(self.root)), "--output", str(evidence),
                  "--receipts-dir", str(receipts), *window_arguments)
        self.tool("review_ledger.py", "--release", self.release, "--candidate", candidate,
                  "--reviews", str(self.private_path("reviews")), "--values", str(self.private_path("values")))
        self.check_ledger()
        arguments = ["--release", self.release, "--candidate", candidate, "--as-of", date,
                     "--measurement-prefix", self.prefix, "--evidence", str(evidence)]
        declared = manifest_components(read_json(self.plan_path.parent / "manifest.json"))
        for lane in ROUTES:
            if lane.endswith("-native") and f"{lane.removesuffix('-native')}-windows-native" not in declared:
                continue
            arguments += ["--route", f"{lane}={receipts / (lane + '-run.json')}"]
        self.tool("compose_route_acceptance.py", *arguments)
        self.tool("rebind_release.py", "--release", self.release)

    def run_tools(self, group: str) -> None:
        if group == "stage":
            self.stage()
        elif group == "guide":
            self.tool("retarget_guide.py", "--from", self.plan["predecessor"], "--to", self.release)
        elif group == "compose":
            self.compose()
        elif group == "audit":
            self.audit("composed-final")
        else:
            self.tool("rebind_release.py", "--release", self.release, "--pin",
                      self.records[PIN_SOURCES[group]]["commit"], "--stage", group.removesuffix("-pin"))

    def commit(self, group: str, paths: set[str]) -> str:
        if paths:
            git(self.root, "add", "--", *sorted(paths))
        body = f"Release: {self.release}\nRelease-Step: {group}"
        if group in PIN_SOURCES:
            body += "\nPins: " + self.records[PIN_SOURCES[group]]["commit"]
        git(self.root, "commit", "--allow-empty", "-m", SUBJECTS[group].format(release=self.release), "-m", body)
        return git(self.root, "rev-parse", "HEAD").strip()

    def run_group(self, group: str) -> None:
        if group in self.records:
            self.state["groups"].setdefault(group, {})["commit"] = self.records[group]["commit"]
            self.save()
            return
        dirty = self.check_dirty(group)
        cached = self.state["groups"].get(group, {})
        if group in ("stage", "compose") and not cached and dirty:
            raise ReleaseError(f"first {group} run refuses dirty declared paths: "
                               + ", ".join(sorted(dirty))
                               + "; supply release notes with --notes, or commit or discard these edits explicitly")
        head = git(self.root, "rev-parse", "HEAD").strip()
        digest = self.inputs_digest(group, head)
        if group == "compose" and cached.get("tools_complete") is not False:
            self.check_ledger()
        complete = (bool(dirty) and cached.get("tools_complete") is True
                    and cached.get("inputs_sha256") == digest
                    and cached.get("outputs") == self.outputs(group)
                    and all(path.is_file() for path in self.required_outputs(group)))
        if not complete:
            if group != "guide":
                self.restore(group, dirty)
            self.check_plan()
            cached = {"inputs_sha256": digest, "attempts": cached.get("attempts", 0) + 1,
                      "tools_complete": False}
            self.state["groups"][group] = cached
            self.save()
            self.run_tools(group)
            self.check_plan()
            missing = [str(path.relative_to(self.root)) for path in self.required_outputs(group) if not path.is_file()]
            if missing:
                raise ReleaseError(f"{group} did not produce declared outputs: {', '.join(missing)}")
            self.check_dirty(group)
            if group == "guide":
                # An idempotent retarget's output is the authored input on a resumed attempt.
                cached["inputs_sha256"] = self.inputs_digest(group, head)
            cached.update(tools_complete=True, outputs=self.outputs(group))
            self.save()
        if group == "compose":
            self.check_ledger()
        if git(self.root, "rev-parse", "HEAD").strip() != head:
            raise ReleaseError("HEAD changed while the release group was running")
        commit = self.commit(group, self.check_dirty(group))
        cached["commit"] = commit
        self.records[group] = {"commit": commit, "pins": self.records[PIN_SOURCES[group]]["commit"]
                               if group in PIN_SOURCES else ""}
        self.save()

    def checks(self, *, ready: bool, no_suite: bool) -> None:
        self.check_dirty(None)
        if ready:
            self.tool("verify_release.py", "--release", self.release, "--require-ready", "--check-pins")
        else:
            self.tool("verify_release.py", "--release", self.release, "--require-installable")
            self.tool("verify_release.py", "--release", self.release, "--lint-ready", "--check-pins")
        if not no_suite:
            self.tool("run_tests.py")


def run_pipeline(driver: ReleaseDriver, *, finalize: bool, no_suite: bool = False,
                 through: str | None = None) -> None:
    """One execution path for CLI cuts and a disposable-clone rehearsal."""
    plan_path = driver.plan_path.relative_to(driver.root).as_posix()
    if not finalize and plan_path in dirty_paths(driver.root):
        raise ReleaseError(f"candidate requires a committed plan: {plan_path}; "
                           "use plan init for a new release, then plan commit for its authored inputs")
    if finalize and "guide" not in driver.records:
        raise ReleaseError("finalize requires the guide candidate commit")
    interrupted_stage = not finalize and "stage" not in driver.records and driver.state["groups"].get("stage")
    if not interrupted_stage:
        driver.check_plan()
    groups = GROUPS[3:] if finalize else GROUPS[:3]
    for group in groups:
        if group not in driver.records:
            for tool in driver.tools(group):
                driver.require_tool(tool)
    for group in groups:
        driver.run_group(group)
        if group == through:
            return
    driver.checks(ready=finalize, no_suite=no_suite)


def required_input(driver: ReleaseDriver, group: str) -> str:
    if group == "stage":
        items = ["plan"]
        if driver.recut_native():
            items += ["--bundle LANE=DIR", "--native-publication LANE=JSON", "--asset ROLE=PATH when external"]
        if any(row["id"] == COMPONENT_IDS[0] and row["disposition"] == "recut" for row in driver.plan["components"]):
            items += ["--stage-input JSON", "--lane-receipt rtx5090=PATH", "--runtime-publication JSON"]
        if driver.plan["client"]["disposition"] == "updated":
            items += ["--client-component JSON"]
        return ", ".join(items)
    if group == "compose":
        return "--window-root DIR, --reviews DIR, --values JSON, --as-of DATE"
    return "none (identities and pins come from the plan and trailers)"


def _rehearsal_guide_edit(root: Path, predecessor: str, release: str) -> None:
    """Apply only the authored link removals the real retarget tool requests."""
    from verify_release import MARKDOWN_LINK_RE

    guide = root / "docs" / "QUICKSTART.md"
    while True:
        result = subprocess.run(
            [sys.executable, str(root / "scripts" / "retarget_guide.py"),
             "--from", predecessor, "--to", release, "--check"],
            cwd=root, capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode == 0 or (
                result.returncode == 1 and not result.stderr and result.stdout.rstrip().endswith("would change")):
            return
        unbound = re.search(r": unbound evidence link: (.+)$", result.stderr, re.MULTILINE)
        if unbound is None:
            raise ReleaseError("retarget_guide.py: " + (result.stderr or result.stdout).strip())
        target = unbound[1].strip("<>")
        text = guide.read_text(encoding="utf-8")
        matches = [match for match in MARKDOWN_LINK_RE.finditer(text) if match[1].strip("<>") == target]
        if not matches:
            raise ReleaseError("retarget_guide.py reported a link that cannot be located")
        for match in reversed(matches):
            link = match[0]
            label = link[link.index("[") + 1:link.index("](")]
            text = text[:match.start()] + label + text[match.end():]
        atomic_write(guide, text)
        print(f"rehearsal: guide: removed unbound evidence link {target}; kept its label", flush=True)


def _rehearsal_negative_probe(root: Path, release: str, path: Path) -> None:
    original = path.read_bytes()
    try:
        atomic_write(path, original + b" ")
        result = subprocess.run(
            [sys.executable, str(root / "scripts" / "verify_release.py"),
             "--release", release, "--require-ready", "--check-pins"],
            cwd=root, capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode != 1:
            raise ReleaseError(f"{path.relative_to(root)} byte-change probe expected exit 1, "
                               f"got {result.returncode}: {result.stdout}{result.stderr}")
    finally:
        atomic_write(path, original)


def rehearse(root: Path = ROOT, *, keep: Path | None = None, suite: bool = False) -> int:
    """Exercise the real product tail at HEAD in an isolated, network-free clone."""
    root = Path(root).resolve()
    temporary = None

    def step(name: str, action):
        started = time.perf_counter()
        try:
            result = action()
        except Exception as error:
            detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
            print(f"rehearsal: {name}: failed ({time.perf_counter() - started:.3f}s): {detail}", flush=True)
            raise
        print(f"rehearsal: {name}: passed ({time.perf_counter() - started:.3f}s)", flush=True)
        return result

    def preflight():
        if git(root, "rev-parse", "--is-shallow-repository").strip() == "true":
            raise ReleaseError("rehearsal requires a full, non-shallow repository")
        dirty = dirty_paths(root)
        if dirty:
            raise ReleaseError("rehearsal requires a clean repository: " + ", ".join(sorted(dirty)))
        if keep is not None:
            destination = Path(keep).resolve()
            if destination.is_relative_to(root):
                raise ReleaseError("--keep must be outside the source repository")
            if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
                raise ReleaseError("--keep must name an absent or empty directory")
        previous = latest_ready_manifest(root)
        ready = tuple(map(int, previous["release"][1:].split(".")))
        versions = {path.name: tuple(map(int, path.name[1:].split(".")))
                    for path in (root / "releases").iterdir()
                    if path.is_dir() and re.fullmatch(r"v\d+\.\d+\.\d+", path.name)}
        later = sorted((name for name, version in versions.items() if version > ready),
                       key=versions.__getitem__)
        return git(root, "rev-parse", "HEAD").strip(), previous, later

    try:
        head, previous, later = step("preflight", preflight)
        if later:
            # A release newer than the latest ready one is being cut on this tree. Its own
            # lint and ready checks are the proof here; a synthetic successor would collide.
            print(f"rehearsal: skipped: release {later[-1]} is in progress on this tree", flush=True)
            return 0
        version = tuple(map(int, previous["release"][1:].split(".")))
        release = f"v{version[0]}.{version[1] + 1}.0"
        if keep is None:
            temporary = tempfile.TemporaryDirectory(prefix="release-rehearsal-")
            clone = Path(temporary.name) / "product"
        else:
            clone = Path(keep).resolve()

        def clone_head():
            clone.parent.mkdir(parents=True, exist_ok=True)
            git(root, "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(root), str(clone))
            for key, value in (("user.name", "Release rehearsal"), ("user.email", "release@example.invalid"),
                               ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
                git(clone, "config", key, value)
            git(clone, "checkout", "--quiet", "--detach", head)
            git(clone, "remote", "remove", "origin")

        step("clone", clone_head)
        step("plan init", lambda: init_plan(clone, release))
        inputs = clone / ".release-state" / "rehearsal"
        staged_notes = inputs / "stage-notes.md"
        final_notes = inputs / "final-notes.md"

        def notes():
            title = f"# OMP NInfer {release}\n\n"
            atomic_write(staged_notes, title + "Synthetic host-free release-tooling rehearsal.\n"
                         "Runtime identities and support limits come from the ready predecessor.\n"
                         "This exercises tooling, not real hardware qualification or publication authority.\n")
            atomic_write(final_notes, title + "Synthetic host-free release-tooling rehearsal.\n"
                         "Documented-route fixture acceptance passed for every declared route.\n"
                         "This exercises tooling, not real hardware qualification or publication authority.\n")

        step("notes", notes)
        predecessor = previous["release"]
        candidate_driver = ReleaseDriver(clone, release, argparse.Namespace(
            command="candidate", notes=staged_notes,
            client_component=clone / "releases" / predecessor / "qualification" / "client-components.json"))
        step("candidate lanes", lambda: run_pipeline(candidate_driver, finalize=False,
                                                     no_suite=True, through="lane-pin"))
        step("guide evidence", lambda: _rehearsal_guide_edit(clone, predecessor, release))
        step("candidate", lambda: run_pipeline(candidate_driver, finalize=False, no_suite=True))
        candidate = candidate_driver.records["guide"]["commit"]
        windows = inputs / "windows"

        def fixtures():
            path = clone / "tests" / "acceptance_fixtures.py"
            if not path.is_file():
                raise ReleaseError("missing release tool: tests/acceptance_fixtures.py")
            result = subprocess.run(
                [sys.executable, str(path), "write", "--release", release, "--candidate", candidate,
                 "--out", str(windows)], cwd=clone, check=True, capture_output=True,
                text=True, encoding="utf-8", env={**os.environ, "PYTHONPATH": str(clone / "tests")},
            )
            return json.loads(result.stdout)

        fixture = step("fixtures", fixtures)
        qualification = read_json(clone / "releases" / predecessor / "qualification.json")
        final_driver = ReleaseDriver(clone, release, argparse.Namespace(
            command="finalize", notes=final_notes, window_root=Path(fixture["window_root"]),
            reviews=Path(fixture["reviews"]), values=Path(fixture["values"]),
            as_of=qualification["as_of"]))
        step("finalize", lambda: run_pipeline(final_driver, finalize=True, no_suite=True))

        def ready_gate():
            final_driver.tool("verify_release.py", "--release", release, "--require-ready", "--check-pins")

        step("ready gate", ready_gate)

        def status():
            if tuple(group_commits(clone, release)) != GROUPS:
                raise ReleaseError("rehearsal did not complete all eight commit groups")
            if main(["status", "--release", release], root=clone) != 0:
                raise ReleaseError("release status failed")

        step("status", status)
        release_root = clone / "releases" / release
        step("negative receipt audit", lambda: _rehearsal_negative_probe(
            clone, release, release_root / "qualification" / "receipt-audit.json"))
        step("negative pinned evidence", lambda: _rehearsal_negative_probe(
            clone, release, release_root / "qualification.json"))
        step("restored gate", ready_gate)
        if suite:
            step("suite", lambda: final_driver.tool("run_tests.py"))
        print("rehearsal: passed", flush=True)
        return 0
    except Exception:
        return 1
    finally:
        if temporary is not None:
            temporary.cleanup()


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    plan = subcommands.add_parser("plan").add_subparsers(dest="plan_command", required=True)
    plan.add_parser("check").add_argument("--release", required=True)
    initialize = plan.add_parser("init", help="write and commit the release's opening plan")
    initialize.add_argument("--release", required=True)
    initialize.add_argument("--recut", action="append", default=[], metavar="COMPONENT=TAG@COMMIT40")
    initialize.add_argument("--client-tag")
    initialize.add_argument("--decision", action="append", default=[], metavar="ID:KIND:SHA256")
    initialize.add_argument("--no-commit", action="store_true", help="leave the seeded plan for non-interactive author edits")
    plan.add_parser("commit", help="validate and commit an authored opening plan").add_argument("--release", required=True)
    rehearsal = subcommands.add_parser("rehearse", help="prove the real release tail without hosts or network")
    rehearsal.add_argument("--keep", type=Path, help="retain the clone in an absent or empty directory")
    rehearsal.add_argument("--suite", action="store_true", help="also run the contract suite at the ready state")
    for name in ("status", "next", "candidate", "finalize", "publish"):
        command = subcommands.add_parser(name)
        command.add_argument("--release", required=True)
        if name in ("candidate", "finalize"):
            command.add_argument("--no-suite", action="store_true", help="skip only the contract suite")
            for option in PATH_INPUTS:
                command.add_argument("--" + option.replace("_", "-"), type=Path)
            for option, flag in (("bundles", "bundle"), ("lane_receipts", "lane-receipt"),
                                 ("assets", "asset"), ("native_publications", "native-publication")):
                command.add_argument("--" + flag, dest=option, action="append", metavar="NAME=PATH")
            command.add_argument("--as-of")
            command.add_argument("--measurement-prefix")
        if name == "publish":
            command.add_argument("--preflight", action="store_true", required=True)
            command.add_argument("--pr", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "rehearse":
            return rehearse(root, keep=args.keep, suite=args.suite)
        if args.command == "plan":
            if args.plan_command == "init":
                commit = init_plan(root, args.release, recut=args.recut, client_tag=args.client_tag,
                                   decisions=args.decision, no_commit=args.no_commit)
                if commit is None:
                    print(f"release plan {args.release}: seeded; edit releases/{args.release}/plan.json, "
                          f"then run scripts/release.py plan commit --release {args.release}")
                else:
                    print(f"release plan {args.release}: initialized at {commit}")
                return 0
            if args.plan_command == "commit":
                commit = commit_plan(root, args.release)
                print(f"release plan {args.release}: committed at {commit}")
                return 0
            errors = plan_errors(root, args.release)
            if errors:
                raise ReleaseError("\n".join(errors))
            print(f"release plan {args.release}: valid")
            return 0
        driver = ReleaseDriver(root, args.release, args)
        if args.command == "status":
            for group in GROUPS:
                record = driver.records.get(group)
                print(f"{group}\t{'done' if record else 'pending'}\t"
                      f"{record['commit'] if record else '-'}\t{record['pins'] if record else '-'}")
        elif args.command == "next":
            group = next((group for group in GROUPS if group not in driver.records), None)
            print(f"{group}: {required_input(driver, group)}" if group else "complete: publication preflight")
        elif args.command in ("candidate", "finalize"):
            run_pipeline(driver, finalize=args.command == "finalize", no_suite=args.no_suite)
        else:
            driver.check_plan()
            driver.check_dirty(None)
            if "manifest-pin" not in driver.records:
                raise ReleaseError("publication preflight requires the manifest-pin commit")
            if args.pr <= 0:
                raise ReleaseError("--pr must be a positive pull request number")
            path = driver.require_tool("hosts/publish-product-release.sh")
            result = subprocess.run(["bash", str(path), "--release", args.release, "--commit",
                                     git(root, "rev-parse", "HEAD").strip(), "--pr", str(args.pr)], cwd=root)
            if result.returncode:
                raise ReleaseError(f"publish-product-release.sh failed (exit {result.returncode})")
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        print(f"release: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
