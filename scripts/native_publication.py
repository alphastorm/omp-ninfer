#!/usr/bin/env python3
"""Authenticate one published native component without credentials or a release tree.

Run after the component cut, retaining the output outside the immutable chain bundle:
native_publication.py --plan releases/VERSION/plan.json --lane LANE --bundle DIRECTORY
                     [--asset ROLE=FILE ...] --out RECORD [--as-of YYYY-MM-DD] [--check]

The injectable transport has three operations: api(path), tag(repository, tag), and
download(url, expected_size), yielding byte chunks. The default transport uses only
anonymous HTTPS, disables environment proxies and has socket and operation deadlines.
HTTP is permitted only for an explicitly injected loopback API origin in offline tests.
Check mode re-observes every public byte and writes nothing; comparison excludes only
as_of, published_at and authenticated_at_utc, after validating their formats.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import ipaddress
import json
import math
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterator
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bind_native_variant import LANE_VARIANTS
from qualification_bundle import (Bundle, BundleError, Inputs, decode, digest, field,
                                  json_bytes, public_scan, relative, require, sha)
from release_io import atomic_write
from verify_release import GA_PRODUCT_RELEASE_RE, GIT_SHA_RE

REPOSITORY = "alphastorm/ninfer"
REPOSITORY_URL = "https://github.com/" + REPOSITORY
EVIDENCE_CLASS = "anonymous-public-byte-downloads-and-matching-github-asset-digests"
CHUNK_BYTES = 256 * 1024
API_BYTES = 4 * 1024 * 1024


class HTTPTransport:
    """No tokens, cookies, credential helpers, authentication handlers or proxy credentials."""

    def __init__(self, api_origin: str = "https://api.github.com", *,
                 socket_timeout: float = 30, api_timeout: float = 60,
                 download_timeout: float = 600) -> None:
        for name, value in (("socket_timeout", socket_timeout), ("api_timeout", api_timeout),
                            ("download_timeout", download_timeout)):
            require(type(value) in (int, float) and math.isfinite(value) and value > 0,
                    "transport", "/" + name, "expected a finite positive timeout")
        self.api_origin = api_origin.rstrip("/")
        origin = urllib.parse.urlsplit(self.api_origin)
        require(not origin.path and not origin.query and not origin.fragment, "transport",
                "/api_origin", "expected an origin without a path")
        self.socket_timeout, self.api_timeout, self.download_timeout = socket_timeout, api_timeout, download_timeout
        self.validate_url(self.api_origin)
        transport = self

        class AnonymousRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, response, code, message, headers, new_url):
                transport.validate_url(new_url)
                return super().redirect_request(request, response, code, message, headers, new_url)

        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), AnonymousRedirect())
        self.opener.addheaders = []

    def validate_url(self, url: str) -> None:
        require(isinstance(url, str) and not any(character.isspace() for character in url),
                "transport", "/url", "expected an absolute public URL")
        parsed = urllib.parse.urlsplit(url)
        require(parsed.hostname is not None and parsed.username is None and parsed.password is None
                and not parsed.fragment, "transport", "/url", "credentials and fragments are forbidden")
        if parsed.scheme == "https":
            return
        try:
            loopback = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            loopback = False
        origin = urllib.parse.urlsplit(self.api_origin)
        require(parsed.scheme == "http" and loopback and parsed.netloc == origin.netloc,
                "transport", "/url", "HTTPS is required outside the injected loopback origin")

    def _chunks(self, url: str, *, label: str, maximum: int, timeout: float,
                exact: bool, accept: str = "application/octet-stream") -> Iterator[bytes]:
        self.validate_url(url)
        deadline = time.monotonic() + timeout
        request = urllib.request.Request(url, headers={
            "User-Agent": "omp-ninfer-public-authentication", "Accept": accept,
            "Accept-Encoding": "identity"})
        try:
            with self.opener.open(request, timeout=min(self.socket_timeout, timeout)) as response:
                length = response.headers.get("Content-Length")
                if length is not None:
                    require(length.isdecimal(), label, "/Content-Length", "expected a nonnegative byte count")
                    require(int(length) == maximum if exact else int(length) <= maximum,
                            label, "/Content-Length", "public response size differs")
                observed = 0
                while True:
                    require(time.monotonic() < deadline, label, "/timeout", "public read exceeded its deadline")
                    chunk = response.read1(CHUNK_BYTES)
                    require(time.monotonic() < deadline, label, "/timeout", "public read exceeded its deadline")
                    if not chunk:
                        break
                    observed += len(chunk)
                    require(observed <= maximum, label, "/bytes", "public response exceeds the declared size")
                    yield chunk
                require(not exact or observed == maximum, label, "/bytes", "public response is truncated")
        except urllib.error.HTTPError as error:
            error.close()
            raise BundleError(f"{label}#/http_status: public request returned {error.code}") from error
        except (OSError, urllib.error.URLError) as error:
            raise BundleError(f"{label}#/transport: anonymous public read failed ({type(error).__name__})") from error

    def api(self, path: str) -> dict[str, Any]:
        relative(path, "public API", "/path")
        data = b"".join(self._chunks(self.api_origin + "/" + path, label="public API",
                                     maximum=API_BYTES, timeout=self.api_timeout, exact=False,
                                     accept="application/vnd.github+json"))
        return decode(data, "public API")

    def tag(self, repository: str, tag: str) -> str:
        path = f"repos/{repository}/git/ref/tags/{urllib.parse.quote(tag, safe='')}"
        deadline = time.monotonic() + self.api_timeout
        seen = set()
        while True:
            require(time.monotonic() < deadline, "public tag", "/timeout", "tag lookup exceeded its deadline")
            value = self.api(path)
            target = field(value, "object", dict, "public tag")
            commit = field(target, "sha", str, "public tag", "/object")
            require(GIT_SHA_RE.fullmatch(commit), "public tag", "/object/sha", "expected a full git SHA")
            kind = target.get("type")
            if kind == "commit":
                return commit
            require(kind == "tag" and commit not in seen, "public tag", "/object/type",
                    "expected a commit or an acyclic annotated tag")
            seen.add(commit)
            path = f"repos/{repository}/git/tags/{commit}"

    def download(self, url: str, expected_size: int) -> Iterator[bytes]:
        yield from self._chunks(url, label="public asset", maximum=expected_size,
                                timeout=self.download_timeout, exact=True)


def load_bundle(plan: dict[str, Any], lane: str, directory: Path, inputs: Inputs,
                assets: dict[str, Path]) -> tuple[str, Bundle]:
    release = field(plan, "release", str, "plan")
    require(plan.get("artifact_type") == "omp_ninfer_release_plan"
            and type(plan.get("schema_version")) is int and plan["schema_version"] == 1
            and GA_PRODUCT_RELEASE_RE.fullmatch(release), "plan", "/", "expected a schema-1 GA release plan")
    require(lane in LANE_VARIANTS, "arguments", "/lane", "unknown native lane")
    rows = [row for row in field(plan, "components", list, "plan")
            if isinstance(row, dict) and row.get("id") == LANE_VARIANTS[lane]]
    require(len(rows) == 1, "plan", "/components/" + lane, "expected exactly one native lane")
    component = rows[0]
    require(component.get("disposition") == "recut", "plan", "/components/" + lane + "/disposition",
            "carried lanes cannot produce a new publication record")
    source = field(component, "source_commit", str, "plan", "/components/" + lane)
    require(GIT_SHA_RE.fullmatch(source), "plan", "/components/" + lane + "/source_commit", "expected a full git SHA")
    tag = field(component, "release_tag", str, "plan", "/components/" + lane)
    reference = inputs.load(directory / "bundle.json")
    edges = [edge for edge in field(reference, "inputs", list, directory / "bundle.json")
             if isinstance(edge, dict) and edge.get("role") == "assets"]
    require(len(edges) == 1, directory / "bundle.json", "/inputs/assets", "expected one closed asset set")
    sums_path = directory / relative(edges[0].get("path"), directory / "bundle.json", "/inputs/assets/path")
    receipt_path = sums_path.parent / "package-build-receipt.json"
    receipt = inputs.load(receipt_path)
    package = field(receipt, "package", dict, receipt_path)
    binaries = field(receipt, "binaries", dict, receipt_path)
    spec = inputs.load(directory / "release-spec.json")
    config = inputs.load(directory / "server-config.json")
    row = {
        "id": LANE_VARIANTS[lane], "release_tag": tag, "source_commit": source,
        "package_name": field(package, "filename", str, receipt_path, "/package"),
        "package_sha256": digest(package.get("sha256"), receipt_path, "/package/sha256"),
        "package_bytes": field(package, "bytes", int, receipt_path, "/package"),
        "server_binary_sha256": digest(binaries.get("server_sha256"), receipt_path, "/binaries/server_sha256"),
        "configuration_sha256": digest(receipt.get("config_sha256"), receipt_path, "/config_sha256"),
        "model_artifact_sha256": digest(receipt.get("model_sha256"), receipt_path, "/model_sha256"),
        "build_profile": field(spec, "build_profile", str, directory / "release-spec.json"),
        "runtime_shape": field(spec, "runtime_shape", dict, directory / "release-spec.json"),
        "maximum_context_tokens": field(field(config, "engine", dict, directory / "server-config.json"),
                                        "max_context", int, directory / "server-config.json", "/engine"),
        "checksums_sha256": digest(edges[0].get("sha256"), directory / "bundle.json", "/inputs/assets/sha256")}
    bundle = Bundle(directory, lane, row, inputs, release, assets)
    expected_roles = {edge["role"] for edge in bundle.reference["inputs"] if edge.get("external") is True}
    require(set(assets) == expected_roles, "arguments", "/asset", "external asset roles differ from the bundle")
    upstream = field(receipt, "upstream_base_sha", str, receipt_path)
    require(GIT_SHA_RE.fullmatch(upstream), receipt_path, "/upstream_base_sha", "expected a full git SHA")
    require(bundle.values[lane + ".json"]["identity"].get("upstream_base_sha") == upstream,
            directory / (lane + ".json"), "/identity/upstream_base_sha", "differs from the package receipt")
    require(field(spec, "model", dict, directory / "release-spec.json").get("sha256") == row["model_artifact_sha256"],
            directory / "release-spec.json", "/model/sha256", "differs from the measured native model")
    return release, bundle


def timestamp(value: Any, label: str, pointer: str) -> str:
    require(isinstance(value, str), label, pointer, "expected an offset-qualified timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise BundleError(f"{label}#{pointer}: invalid timestamp") from error
    require(parsed.utcoffset() is not None, label, pointer, "timestamp must include its UTC offset")
    return value


def iso_date(value: Any, label: str, pointer: str) -> str:
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value),
            label, pointer, "expected YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise BundleError(f"{label}#{pointer}: invalid calendar date") from error
    return value


def create_record(plan_path: Path, lane: str, directory: Path, *, assets: dict[str, Path] | None = None,
                  transport: Any = None, clock: Any = None, as_of: str | None = None) -> dict[str, Any]:
    if as_of is not None:
        iso_date(as_of, "arguments", "/as-of")
    inputs = Inputs()
    plan = inputs.load(plan_path)
    release, bundle = load_bundle(plan, lane, directory, inputs, assets or {})
    tag, source = bundle.row["release_tag"], bundle.row["source_commit"]
    transport = transport if transport is not None else HTTPTransport()
    peeled = transport.tag(REPOSITORY, tag)
    require(peeled == source, "public tag", "/peeled_commit", "differs from plan source_commit")
    api = transport.api(f"repos/{REPOSITORY}/releases/tags/{urllib.parse.quote(tag, safe='')}")
    require(api.get("tag_name") == tag, "public release", "/tag_name", "differs from plan release_tag")
    require(api.get("draft") is False, "public release", "/draft", "release must exist and not be a draft")
    release_url = REPOSITORY_URL + "/releases/tag/" + tag
    require(api.get("html_url") == release_url, "public release", "/html_url", "differs from the component repository and tag")
    published_at = timestamp(api.get("published_at"), "public release", "/published_at")
    now = (clock if clock is not None else lambda: datetime.now(timezone.utc))()
    require(isinstance(now, datetime) and now.utcoffset() is not None,
            "clock", "/", "expected an offset-qualified datetime")
    observed = now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    as_of = iso_date(as_of if as_of is not None else observed[:10], "arguments", "/as-of")
    sums_bytes = inputs.read(bundle.assets / "SHA256SUMS")
    expected = {**bundle.asset_hashes, "SHA256SUMS": sha(sums_bytes)}
    sizes = {name: path.stat().st_size for name, path in bundle.asset_paths.items()}
    sizes["SHA256SUMS"] = len(sums_bytes)
    rows = field(api, "assets", list, "public release")
    by_name = {}
    for index, row in enumerate(rows):
        pointer = f"/assets/{index}"
        name = field(row, "name", str, "public release", pointer)
        require(name in expected and name not in by_name and "/" not in name and "\\" not in name,
                "public release", pointer + "/name", "extra, duplicate or unsafe asset name")
        require(type(row.get("size")) is int and row["size"] == sizes[name],
                "public release", pointer + "/size", "differs from bundle asset size: " + name)
        require(row.get("digest") == "sha256:" + expected[name], "public release", pointer + "/digest",
                f"differs from bundle SHA-256: {name}: public {row.get('digest')!r}, "
                f"bundle 'sha256:{expected[name]}'")
        field(row, "browser_download_url", str, "public release", pointer)
        by_name[name] = row
    require(set(by_name) == set(expected), "public release", "/assets/name", "public asset set differs from bundle")
    for name, row in sorted(by_name.items()):
        hashed, count, outer = hashlib.sha256(), 0, bytearray()
        for chunk in transport.download(row["browser_download_url"], sizes[name]):
            require(isinstance(chunk, bytes), "public asset", "/" + name + "/bytes", "transport must yield byte chunks")
            count += len(chunk)
            require(count <= sizes[name], "public asset", "/" + name + "/bytes", "download exceeds bundle size")
            hashed.update(chunk)
            if name == "SHA256SUMS":
                outer.extend(chunk)
        require(count == sizes[name], "public asset", "/" + name + "/bytes", "download is truncated")
        require(hashed.hexdigest() == expected[name], "public asset", "/" + name + "/sha256",
                f"anonymous bytes differ from the API and bundle: public {hashed.hexdigest()}, "
                f"bundle {expected[name]}")
        if name == "SHA256SUMS":
            require(outer == sums_bytes, "public asset", "/SHA256SUMS", "outer checksum set differs from bundle")
    projected = {
        "lane": lane, "component_tag": tag, "tag_commit": peeled, "source_commit": source,
        "build_profile": bundle.row["build_profile"], "published": True, "published_at": published_at,
        "authenticated_at_utc": observed, "publication_evidence_class": EVIDENCE_CLASS,
        "release_url": release_url, "outer_checksums_sha256": expected["SHA256SUMS"],
        "outer_hashed_entries": len(bundle.asset_hashes), "total_distribution_files": len(expected),
        "assets": [{"name": name, "sha256": expected[name], "bytes": sizes[name]}
                   for name in sorted(bundle.asset_hashes)],
        "checksums_asset": {"name": "SHA256SUMS", "sha256": expected["SHA256SUMS"], "bytes": sizes["SHA256SUMS"]},
        "actual_hardware_qualification": {"repository_path": f"releases/{release}/qualification/{lane}.json",
                                          "sha256": sha(inputs.read(directory / (lane + ".json")))},
        "public_package_executed_during_qualification": False,
        "scope": "Authenticates published selected component bytes and the separately bound pre-cut hardware receipt; no product-route acceptance or publication authority."}
    result = {
        "artifact_type": "omp_ninfer_native_component_publication", "schema_version": 1,
        "release": release, "as_of": as_of, "status": "passed",
        "identity": {"repository": REPOSITORY_URL, "source_commit": source,
                     "upstream_commit": bundle.receipt["upstream_base_sha"],
                     "model_artifact_sha256": bundle.row["model_artifact_sha256"]},
        "lanes": [projected], "publication_authorized_by_this_receipt": False, "product_publication_authorized": False}
    public_scan(result, "publication record")
    inputs.check()
    return result


def without_timestamps(value: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(value)
    iso_date(value.get("as_of"), "publication record", "/as_of")
    rows = field(value, "lanes", list, "publication record")
    require(len(rows) == 1, "publication record", "/lanes", "expected exactly one lane")
    for row in rows:
        for name in ("published_at", "authenticated_at_utc"):
            timestamp(field(row, name, str, "publication record", "/lanes/0"),
                      "publication record", "/lanes/0/" + name)
            row.pop(name)
    value.pop("as_of")
    return value


def authenticate(plan_path: Path, lane: str, directory: Path, out: Path, *, check: bool = False,
                 assets: dict[str, Path] | None = None, transport: Any = None, clock: Any = None,
                 as_of: str | None = None) -> dict[str, Any]:
    require(not out.resolve().is_relative_to(directory.resolve()) and out.resolve() != plan_path.resolve(),
            "arguments", "/out", "record must not overwrite the plan or immutable bundle")
    existing = decode(out.read_bytes(), out) if check and out.is_file() else None
    require(not check or existing is not None, out, "/", "check requires an existing publication record")
    result = create_record(plan_path, lane, directory, assets=assets, transport=transport, clock=clock, as_of=as_of)
    if check:
        require(without_timestamps(existing) == without_timestamps(result), out, "/",
                "publication record differs from the public observation")
    else:
        atomic_write(out, json_bytes(result))
    return result


def main(argv: list[str] | None = None, *, transport: Any = None, clock: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--lane", choices=tuple(LANE_VARIANTS), required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--asset", action="append", default=[], metavar="ROLE=FILE")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--as-of", help="record date in YYYY-MM-DD form (default: observation UTC date)")
    parser.add_argument("--check", action="store_true",
                        help="recompute without writing; ignore as_of, published_at and authenticated_at_utc only")
    args = parser.parse_args(argv)
    try:
        assets = {}
        for argument in args.asset:
            role, separator, path = argument.partition("=")
            require(separator and role and path and role not in assets, "arguments", "/asset", "expected unique ROLE=FILE")
            assets[role] = Path(path)
        result = authenticate(args.plan, args.lane, args.bundle, args.out, check=args.check, assets=assets,
                              transport=transport, clock=clock, as_of=args.as_of)
    except (BundleError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"native publication refused: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"schema": 1, "release": result["release"], "lane": args.lane,
                      "status": "checked" if args.check else "authenticated"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
