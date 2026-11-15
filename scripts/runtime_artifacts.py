#!/usr/bin/env python3
"""Authenticate published runtime assets anonymously without executing a package.

runtime_artifacts.py --plan releases/VERSION/plan.json --stage-input FILE
    --runtime-publication FILE --runtime-build-identity FILE [--runtime-base FILE]
    --mirror DIRECTORY --out RECORD [--as-of YYYY-MM-DD] [--check]

Relative source_archive and checksums inputs resolve beside the stage input.
The mirror contains the six selected public assets, named as published. Downloads
use native_publication's bounded, credential-free transport. Archive members are
hashed as a stream, never extracted or executed. Refusal writes nothing; --check
re-observes every asset and compares the existing record except its as_of value.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile
from typing import Any
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_publication import HTTPTransport, REPOSITORY, REPOSITORY_URL, iso_date, timestamp
from qualification_bundle import (BundleError, Inputs, decode, digest, field, json_bytes,
                                  public_scan, relative, require, sha)
from release_io import atomic_write
from verify_release import GA_PRODUCT_RELEASE_RE, GIT_SHA_RE

MAX_TAR_MEMBERS = 10_000
METHOD = (
    "Compared the runtime mirror with published GitHub release API sizes and digests, "
    "then downloaded every selected asset anonymously and matched its SHA-256 and size. "
    "The runtime-base receipt matched the selected immutable receipt. Streamed and hashed "
    "every regular packaged file and authenticated the packaged server and build identity. "
    "No executable or container was run."
)


def package_files(path: Path, binary_sha: str, identity_sha: str) -> dict[str, str]:
    inventory, names = {}, set()
    try:
        with tarfile.open(path, mode="r|gz") as archive:
            for index, member in enumerate(archive):
                require(index < MAX_TAR_MEMBERS, path, "/archive", "archive exceeds the member cap")
                name = member.name.rstrip("/") if member.isdir() else member.name
                relative(name, path, "/archive/member")
                require(name not in names, path, "/archive/member", "duplicate archive member")
                names.add(name)
                if member.isfile():
                    stream = archive.extractfile(member)
                    require(stream is not None, path, "/archive/member", "missing regular member bytes")
                    with stream:
                        inventory[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    except (tarfile.TarError, EOFError, OSError) as error:
        raise BundleError(f"{path}#/archive: invalid or truncated runtime archive") from error
    for suffix, expected in (("/bin/ninfer-serve", binary_sha), ("/build-identity.json", identity_sha)):
        require([value for name, value in inventory.items() if name.endswith(suffix)] == [expected],
                path, "/package_files_sha256", "expected exactly one matching packaged " + suffix[1:])
    return dict(sorted(inventory.items()))


def create_record(plan_path: Path, stage_input: Path, runtime_publication: Path,
                  runtime_build_identity: Path, mirror: Path, *, runtime_base: Path | None = None,
                  transport: Any = None, clock: Any = None, as_of: str | None = None,
                  inputs: Inputs | None = None) -> dict[str, Any]:
    if as_of is not None:
        iso_date(as_of, "arguments", "/as-of")
    inputs = inputs if inputs is not None else Inputs()
    plan = inputs.load(plan_path)
    release = field(plan, "release", str, plan_path)
    require(plan.get("artifact_type") == "omp_ninfer_release_plan"
            and type(plan.get("schema_version")) is int and plan["schema_version"] == 1
            and GA_PRODUCT_RELEASE_RE.fullmatch(release),
            plan_path, "/", "expected a schema-1 GA release plan")
    rows = [row for row in field(plan, "components", list, plan_path)
            if isinstance(row, dict) and row.get("id") == "rtx5090-container"]
    require(len(rows) == 1, plan_path, "/components", "expected exactly one runtime lane")
    component = rows[0]
    require(component.get("disposition") == "recut", plan_path, "/components/rtx5090-container/disposition",
            "carried runtime cannot produce a new authentication record")
    source = field(component, "source_commit", str, plan_path)
    require(GIT_SHA_RE.fullmatch(source), plan_path, "/source_commit", "expected a full git SHA")
    tag = field(component, "release_tag", str, plan_path)
    stage = inputs.load(stage_input)
    binary_sha = digest(stage.get("binary_sha"), stage_input, "/binary_sha")
    archive_sha = digest(stage.get("archive_sha"), stage_input, "/archive_sha")
    sbom_sha = digest(stage.get("sbom_sha"), stage_input, "/sbom_sha")
    source_sha = digest(stage.get("source_archive_sha"), stage_input, "/source_archive_sha")
    image_digest = field(stage, "image_digest", str, stage_input)
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", image_digest),
            stage_input, "/image_digest", "expected a SHA-256 OCI digest")
    source_tag = field(stage, "source_tag", str, stage_input)
    runtime_tag = field(stage, "runtime_receipt_release", str, stage_input)
    publication_data = inputs.read(runtime_publication)
    publication = decode(publication_data, runtime_publication)
    require(publication.get("artifact_type") == "ninfer_runtime_image_publication_receipt"
            and publication.get("source_commit") == source and publication.get("release_tag") == tag
            and publication.get("runtime_release_tag") == runtime_tag
            and publication.get("binary_sha256") == archive_sha
            and publication.get("image_digest") == image_digest and publication.get("secret_free") is True,
            runtime_publication, "/", "runtime publication differs from the selected runtime")
    base_tag = field(publication, "runtime_base_receipt_release", str, runtime_publication)
    if runtime_base is None:
        root = plan_path.resolve().parent.parent.parent
        predecessor = field(plan, "predecessor", str, plan_path)
        require(GA_PRODUCT_RELEASE_RE.fullmatch(predecessor), plan_path, "/predecessor",
                "expected a GA predecessor release")
        predecessor_path = root / "releases" / predecessor / "qualification.json"
        qualification = inputs.load(predecessor_path)
        composition = field(qualification, "composition", dict, predecessor_path)
        packaging = field(composition, "local_release_packaging", dict, predecessor_path, "/composition")
        edge = field(packaging, "runtime_base_receipt", dict, predecessor_path,
                     "/composition/local_release_packaging")
        runtime_base = root / relative(edge.get("repository_path"), predecessor_path,
                                       "/composition/local_release_packaging/runtime_base_receipt/repository_path")
    base_data = inputs.read(runtime_base)
    require(sha(base_data) == publication.get("runtime_base_receipt_sha256"),
            runtime_publication, "/runtime_base_receipt_sha256",
            "differs from runtime base receipt; supply --runtime-base when the base changes")
    identity_data = inputs.read(runtime_build_identity)
    identity = decode(identity_data, runtime_build_identity)
    require(identity.get("artifact_type") == "ninfer_release_build_identity"
            and type(identity.get("schema_version")) is int and identity["schema_version"] == 1
            and identity.get("source_dirty") is False and identity.get("patch_stack_sha") == source
            and field(identity, "binaries", dict, runtime_build_identity).get("ninfer-serve") == binary_sha,
            runtime_build_identity, "/", "build identity differs from the selected runtime")
    paths = {}
    for name in ("source_archive", "checksums"):
        path = Path(field(stage, name, str, stage_input))
        paths[name] = path if path.is_absolute() else stage_input.parent / path
    inputs.authenticate(paths["source_archive"], source_sha)
    checksums_data = inputs.read(paths["checksums"])
    expected = {
        archive_sha: ("archive", tag, None),
        sbom_sha: ("sbom", tag, None),
        source_sha: ("source", source_tag, paths["source_archive"].stat().st_size),
        sha(checksums_data): ("checksums", tag, len(checksums_data)),
        sha(publication_data): ("publication", runtime_tag, len(publication_data)),
        sha(base_data): ("base", base_tag, len(base_data)),
    }
    require(len(expected) == 6, stage_input, "/digest", "selected asset digests must be distinct")
    require(mirror.is_dir() and not mirror.is_symlink(), mirror, "/", "expected a regular mirror directory")
    transport = transport if transport is not None else HTTPTransport()
    require(transport.tag(REPOSITORY, tag) == source,
            "public tag", "/peeled_commit", "differs from plan source_commit")
    selected, names = {}, set()
    for release_tag in dict.fromkeys((tag, source_tag, runtime_tag, base_tag)):
        require(release_tag and "/" not in release_tag and "\\" not in release_tag
                and not any(character.isspace() for character in release_tag),
                "public release", "/tag_name", "expected a portable release tag")
        api = transport.api(f"repos/{REPOSITORY}/releases/tags/{urllib.parse.quote(release_tag, safe='')}")
        require(api.get("tag_name") == release_tag, "public release", "/tag_name", "differs from selected tag")
        require(api.get("draft") is False, "public release", "/draft", "release must not be a draft")
        require(api.get("html_url") == REPOSITORY_URL + "/releases/tag/" + release_tag,
                "public release", "/html_url", "differs from the component repository and tag")
        timestamp(api.get("published_at"), "public release", "/published_at")
        for index, row in enumerate(field(api, "assets", list, "public release")):
            pointer = f"/assets/{index}"
            name = field(row, "name", str, "public release", pointer)
            relative(name, "public release", pointer + "/name")
            require("/" not in name and name not in names, "public release", pointer + "/name",
                    "duplicate or unsafe mirror asset name")
            names.add(name)
            api_digest = field(row, "digest", str, "public release", pointer)
            value = api_digest.removeprefix("sha256:")
            require(api_digest == "sha256:" + value and value in expected and value not in selected,
                    "public release", pointer + "/digest", "extra, duplicate or mismatched public asset digest")
            role, expected_tag, size = expected[value]
            require(release_tag == expected_tag, "public release", pointer + "/digest",
                    "asset digest belongs to a different selected release")
            count = field(row, "size", int, "public release", pointer)
            require(count > 0 and (size is None or count == size),
                    "public release", pointer + "/size", "differs from the selected input size")
            url = field(row, "browser_download_url", str, "public release", pointer)
            require(url == REPOSITORY_URL + "/releases/download/" + release_tag + "/" + name,
                    "public release", pointer + "/browser_download_url", "differs from the selected public asset")
            if role in ("publication", "base"):
                fixed = "ninfer-runtime-image-" + tag + ".json" if role == "publication" else "ninfer-runtime-base.json"
                require(name == fixed, "public release", pointer + "/name", "differs from the runtime receipt name")
            selected[value] = (role, release_tag, name, count, url)
    require(selected.keys() == expected.keys(), "public release", "/assets/digest",
            "public asset set differs from the selected runtime")
    assets, archive_path = [], None
    for value, (role, release_tag, name, size, url) in selected.items():
        path = mirror / name
        inputs.authenticate(path, value)
        require(path.stat().st_size == size, path, "/bytes", "mirror size differs from the public asset")
        hashed, count = hashlib.sha256(), 0
        for chunk in transport.download(url, size):
            require(isinstance(chunk, bytes), "public asset", "/" + name + "/bytes",
                    "transport must yield byte chunks")
            count += len(chunk)
            require(count <= size, "public asset", "/" + name + "/bytes", "download exceeds the declared size")
            hashed.update(chunk)
        require(count == size, "public asset", "/" + name + "/bytes", "download is truncated")
        require(hashed.hexdigest() == value, "public asset", "/" + name + "/sha256",
                "anonymous download differs from the API and mirror")
        assets.append({
            "release": release_tag, "asset": name, "bytes": size, "sha256": value,
            "public_api_size_digest_match": True, "local_mirror_match": True,
            "anonymous_download_match": True, "url": url})
        if role == "archive":
            archive_path = path
    require(archive_path is not None, mirror, "/archive", "missing runtime archive")
    inventory = package_files(archive_path, binary_sha, sha(identity_data))
    now = (clock if clock is not None else lambda: datetime.now(timezone.utc))()
    require(isinstance(now, datetime) and now.utcoffset() is not None,
            "clock", "/", "expected an offset-qualified datetime")
    result = {
        "artifact_type": "omp_ninfer_component_asset_authentication", "schema_version": 1,
        "as_of": as_of if as_of is not None else now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source_commit": source, "status": "passed", "method": METHOD,
        "assets": sorted(assets, key=lambda row: (row["release"], row["asset"])),
        "packaged_server_sha256": binary_sha, "package_files_sha256": inventory,
        "image_digest": image_digest, "runtime_base_receipt_sha256": sha(base_data),
        "raw_prompts_outputs_or_secrets_included": False,
    }
    public_scan(result, "runtime artifacts record")
    inputs.check()
    return result


def without_timestamps(value: dict[str, Any]) -> dict[str, Any]:
    value = value.copy()
    observed = field(value, "as_of", str, "runtime artifacts record")
    if len(observed) == 10:
        iso_date(observed, "runtime artifacts record", "/as_of")
    else:
        timestamp(observed, "runtime artifacts record", "/as_of")
    value.pop("as_of")
    return value


def authenticate(plan_path: Path, stage_input: Path, runtime_publication: Path,
                 runtime_build_identity: Path, mirror: Path, out: Path, *,
                 runtime_base: Path | None = None, check: bool = False,
                 transport: Any = None, clock: Any = None, as_of: str | None = None) -> dict[str, Any]:
    protected = (plan_path, stage_input, runtime_publication, runtime_build_identity, runtime_base)
    require(not out.resolve().is_relative_to(mirror.resolve())
            and all(out.resolve() != path.resolve() for path in protected if path is not None),
            "arguments", "/out", "record must not overwrite its inputs or mirror")
    existing = decode(out.read_bytes(), out) if check and out.is_file() else None
    require(not check or existing is not None, out, "/", "check requires an existing runtime artifacts record")
    inputs = Inputs()
    result = create_record(plan_path, stage_input, runtime_publication, runtime_build_identity,
                           mirror, runtime_base=runtime_base, transport=transport, clock=clock,
                           as_of=as_of, inputs=inputs)
    require(all(out.resolve() != path.resolve() for path in (*inputs.data, *inputs.hashes)),
            "arguments", "/out", "record must not overwrite an observed input")
    if check:
        require(without_timestamps(existing) == without_timestamps(result), out, "/",
                "runtime artifacts record differs from the public observation")
    else:
        atomic_write(out, json_bytes(result))
    return result


def main(argv: list[str] | None = None, *, transport: Any = None, clock: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "stage-input", "runtime-publication", "runtime-build-identity", "mirror", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--runtime-base", type=Path)
    parser.add_argument("--as-of", help="override the observation date with YYYY-MM-DD")
    parser.add_argument("--check", action="store_true", help="re-observe without writing; ignore as_of only")
    args = parser.parse_args(argv)
    try:
        result = authenticate(args.plan, args.stage_input, args.runtime_publication, args.runtime_build_identity,
                              args.mirror, args.out, runtime_base=args.runtime_base, check=args.check,
                              transport=transport, clock=clock, as_of=args.as_of)
    except (BundleError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"runtime artifacts refused: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"schema": 1, "source_commit": result["source_commit"],
                      "status": "checked" if args.check else "authenticated"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
