"""Offline native publication authentication, including the real HTTP transport."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import unittest
from unittest import mock
import urllib.error
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("native_publication", ROOT / "scripts/native_publication.py")
assert SPEC is not None and SPEC.loader is not None
PUBLICATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PUBLICATION)
from release_io import atomic_write, atomic_write_json
from test_qualification_bundle import SyntheticBundle, load

CLOCK = datetime(2026, 11, 13, 18, 42, 32, tzinfo=timezone.utc)


class OfflineTestCase(unittest.TestCase):
    def setUp(self):
        original = socket.getaddrinfo

        def loopback_only(host, *args, **kwargs):
            try:
                allowed = ipaddress.ip_address(host).is_loopback
            except ValueError:
                allowed = False
            if not allowed:
                raise AssertionError("test attempted a non-loopback network lookup")
            return original(host, *args, **kwargs)

        patch = mock.patch.object(socket, "getaddrinfo", side_effect=loopback_only)
        patch.start()
        self.addCleanup(patch.stop)


class FakeTransport:
    """Serve declared observations and retained bytes, never the internet."""

    def __init__(self, api, tag, files):
        self.observation, self.commit, self.files = deepcopy(api), tag, files
        self.calls = []
        self.overrides = {}

    def api(self, path):
        self.calls.append(("api", path))
        expected = f"repos/{PUBLICATION.REPOSITORY}/releases/tags/{self.observation['tag_name']}"
        if path != expected:
            raise AssertionError("unexpected public API path: " + path)
        return deepcopy(self.observation)

    def tag(self, repository, tag):
        self.calls.append(("tag", repository, tag))
        if repository != PUBLICATION.REPOSITORY or tag != self.observation["tag_name"]:
            raise AssertionError("unexpected tag lookup")
        if self.commit is None:
            raise PUBLICATION.BundleError("public tag#/http_status: not found")
        return self.commit

    def download(self, url, expected_size):
        self.calls.append(("download", url, expected_size))
        if url not in self.files:
            raise AssertionError("unexpected anonymous asset URL: " + url)
        value = self.overrides.get(url, self.files[url])
        if isinstance(value, bytes):
            for offset in range(0, len(value), 7):
                yield value[offset:offset + 7]
        else:
            with value.open("rb") as stream:
                while chunk := stream.read(PUBLICATION.CHUNK_BYTES):
                    yield chunk


class PublicationFixture:
    def __init__(self, root):
        self.fixture = SyntheticBundle(root)
        fixture = self.fixture
        path = fixture.assets / "package-build-receipt.json"
        receipt = load(path)
        receipt["upstream_base_sha"] = load(fixture.directory / "rtx3090.json")["identity"]["upstream_base_sha"]
        atomic_write_json(path, receipt)
        fixture.reseal_assets()
        # No release tree is available to this producer: only the plan survives.
        shutil.rmtree(root / "releases")
        self.plan_path = root / "releases" / fixture.release / "plan.json"
        atomic_write_json(self.plan_path, fixture.plan)
        self.out = root / "observed/publication.json"
        self.tag = fixture.row["release_tag"]
        self.api = {
            "tag_name": self.tag, "draft": False, "prerelease": True,
            "html_url": PUBLICATION.REPOSITORY_URL + "/releases/tag/" + self.tag,
            "published_at": "2026-11-13T18:42:26Z", "assets": []}
        self.files = {}
        for path in sorted(fixture.assets.iterdir()):
            name = path.name
            url = PUBLICATION.REPOSITORY_URL + "/releases/download/" + self.tag + "/" + name
            self.api["assets"].append({"name": name, "size": path.stat().st_size,
                                      "digest": "sha256:" + PUBLICATION.sha(path.read_bytes()),
                                      "browser_download_url": url})
            self.files[url] = path
        self.transport = FakeTransport(self.api, fixture.row["source_commit"], self.files)

    def run(self, **kwargs):
        return PUBLICATION.authenticate(self.plan_path, "rtx3090", self.fixture.directory, self.out,
                                        transport=self.transport, clock=lambda: CLOCK, **kwargs)


class NativePublicationTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = PublicationFixture(self.root)

    def test_derives_every_identity_without_a_release_tree(self):
        result = self.fixture.run()
        row = result["lanes"][0]
        self.assertFalse((self.fixture.plan_path.parent / "manifest.json").exists())
        self.assertEqual(result, load(self.fixture.out))
        self.assertEqual(result["release"], self.fixture.fixture.release)
        self.assertEqual(result["identity"]["source_commit"], self.fixture.fixture.row["source_commit"])
        self.assertEqual(row["build_profile"], self.fixture.fixture.row["build_profile"])
        self.assertEqual(row["actual_hardware_qualification"], {
            "repository_path": f"releases/{self.fixture.fixture.release}/qualification/{self.fixture.fixture.lane}.json",
            "sha256": PUBLICATION.sha((self.fixture.fixture.directory / "rtx3090.json").read_bytes())})
        self.assertEqual(row["outer_hashed_entries"] + 1, row["total_distribution_files"])
        self.assertFalse(result["publication_authorized_by_this_receipt"])
        self.assertFalse(result["product_publication_authorized"])
        self.assertEqual(len([call for call in self.fixture.transport.calls if call[0] == "download"]),
                         len(self.fixture.api["assets"]))

    def test_missing_and_mismatched_public_tag_refuse(self):
        for commit in (None, "a" * 40):
            with self.subTest(commit=commit):
                self.fixture.transport.commit = commit
                with self.assertRaisesRegex(PUBLICATION.BundleError, "public tag#/"):
                    self.fixture.run()
        self.assertFalse(self.fixture.out.exists())

    def test_release_identity_and_draft_refuse_with_field(self):
        for name, value in (("draft", True), ("published_at", None), ("html_url", "https://example.invalid/")):
            with self.subTest(field=name):
                changed = deepcopy(self.fixture.api)
                changed[name] = value
                self.fixture.transport.observation = changed
                with self.assertRaisesRegex(PUBLICATION.BundleError, "/" + name):
                    self.fixture.run()

    def test_release_tag_mismatch_refuses(self):
        transport = self.fixture.transport
        with mock.patch.object(transport, "api", return_value={**self.fixture.api, "tag_name": "different"}):
            with self.assertRaisesRegex(PUBLICATION.BundleError, "/tag_name"):
                self.fixture.run()

    def test_release_asset_closure_size_and_api_digest_refuse(self):
        mutations = [
            ("name", lambda api: api["assets"].pop()),
            ("name", lambda api: api["assets"].append(deepcopy(api["assets"][0]))),
            ("name", lambda api: api["assets"][0].update(name="extra")),
            ("size", lambda api: api["assets"][0].update(size=api["assets"][0]["size"] + 1)),
            ("size", lambda api: api["assets"][0].update(size=True)),
            ("digest", lambda api: api["assets"][0].update(digest="sha256:" + "a" * 64)),
        ]
        for field, change in mutations:
            with self.subTest(field=field):
                value = deepcopy(self.fixture.api)
                change(value)
                self.fixture.transport.observation = value
                with self.assertRaisesRegex(PUBLICATION.BundleError, "/" + field):
                    self.fixture.run()

    def test_anonymous_bytes_refuse_short_long_and_same_size_tampering(self):
        url, path = next(iter(self.fixture.files.items()))
        data = path.read_bytes()
        for replacement, field in ((data[:-1], "bytes"), (data + b"x", "bytes"),
                                   (bytes([data[0] ^ 1]) + data[1:], "sha256")):
            with self.subTest(field=field):
                self.fixture.transport.overrides[url] = replacement
                with self.assertRaisesRegex(PUBLICATION.BundleError, "/" + field):
                    self.fixture.run()

    def test_outer_checksum_bytes_are_downloaded_and_authenticated(self):
        url = next(url for url, path in self.fixture.files.items() if path.name == "SHA256SUMS")
        data = self.fixture.files[url].read_bytes()
        self.fixture.transport.overrides[url] = b"0" + data[1:]
        with self.assertRaisesRegex(PUBLICATION.BundleError, r"SHA256SUMS/sha256"):
            self.fixture.run()

    def test_refusal_leaves_existing_record_byte_identical(self):
        atomic_write(self.fixture.out, b"retained record\n")
        self.fixture.transport.commit = "a" * 40
        with self.assertRaises(PUBLICATION.BundleError):
            self.fixture.run()
        self.assertEqual(self.fixture.out.read_bytes(), b"retained record\n")

    def test_check_reobserves_all_assets_and_only_ignores_timestamps(self):
        self.fixture.run()
        before = self.fixture.out.read_bytes()
        self.fixture.transport.calls.clear()
        self.fixture.transport.observation["published_at"] = "2026-11-14T00:00:00Z"
        PUBLICATION.authenticate(self.fixture.plan_path, "rtx3090", self.fixture.fixture.directory,
                                  self.fixture.out, check=True, transport=self.fixture.transport,
                                  clock=lambda: datetime(2026, 11, 15, tzinfo=timezone.utc))
        self.assertEqual(self.fixture.out.read_bytes(), before)
        self.assertEqual(len([call for call in self.fixture.transport.calls if call[0] == "download"]),
                         len(self.fixture.api["assets"]))
        value = load(self.fixture.out)
        value["lanes"][0]["tag_commit"] = "a" * 40
        atomic_write_json(self.fixture.out, value)
        with self.assertRaisesRegex(PUBLICATION.BundleError, "record differs"):
            self.fixture.run(check=True)

    def test_check_requires_existing_record_and_valid_timestamps(self):
        with self.assertRaisesRegex(PUBLICATION.BundleError, "existing publication record"):
            self.fixture.run(check=True)
        self.fixture.run()
        value = load(self.fixture.out)
        value["lanes"][0].pop("authenticated_at_utc")
        atomic_write_json(self.fixture.out, value)
        with self.assertRaisesRegex(PUBLICATION.BundleError, "/authenticated_at_utc"):
            self.fixture.run(check=True)

    def test_date_override_is_recorded_and_invalid_date_refuses_before_network(self):
        self.assertEqual(self.fixture.run(as_of="2026-11-14")["as_of"], "2026-11-14")
        self.fixture.transport.calls.clear()
        with self.assertRaisesRegex(PUBLICATION.BundleError, "/as-of"):
            self.fixture.run(as_of="2026-02-30")
        self.assertEqual(self.fixture.transport.calls, [])

    def test_carried_lane_refuses_before_network(self):
        plan = load(self.fixture.plan_path)
        next(row for row in plan["components"] if row["id"] == "rtx3090-windows-native")["disposition"] = "carried"
        atomic_write_json(self.fixture.plan_path, plan)
        with self.assertRaisesRegex(PUBLICATION.BundleError, "/disposition"):
            self.fixture.run()
        self.assertEqual(self.fixture.transport.calls, [])

    def test_unbound_external_asset_refuses_before_network(self):
        with self.assertRaisesRegex(PUBLICATION.BundleError, "/asset"):
            self.fixture.run(assets={"unbound": self.root / "unused"})
        self.assertEqual(self.fixture.transport.calls, [])

    def test_output_cannot_reopen_the_bundle_or_overwrite_plan(self):
        for out in (self.fixture.fixture.directory / "publication.json", self.fixture.plan_path):
            with self.subTest(out=out.name):
                with self.assertRaisesRegex(PUBLICATION.BundleError, "/out"):
                    PUBLICATION.authenticate(self.fixture.plan_path, "rtx3090", self.fixture.fixture.directory,
                                              out, transport=self.fixture.transport, clock=lambda: CLOCK)

    def test_cli_prints_one_json_and_check_failure_goes_to_stderr(self):
        args = ["--plan", str(self.fixture.plan_path), "--lane", "rtx3090", "--bundle",
                str(self.fixture.fixture.directory), "--out", str(self.fixture.out)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(PUBLICATION.main(args, transport=self.fixture.transport, clock=lambda: CLOCK), 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "authenticated")
        self.assertEqual(stderr.getvalue(), "")
        value = load(self.fixture.out)
        value["product_publication_authorized"] = True
        atomic_write_json(self.fixture.out, value)
        before = self.fixture.out.read_bytes()
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(PUBLICATION.main(args + ["--check"], transport=self.fixture.transport, clock=lambda: CLOCK), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("record differs", stderr.getvalue())
        self.assertEqual(self.fixture.out.read_bytes(), before)


class HTTPTransportTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = PublicationFixture(Path(temporary.name))
        self.requests = []
        test = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                return

            def do_GET(self):
                test.requests.append((self.path, dict(self.headers)))
                root = f"/repos/{PUBLICATION.REPOSITORY}"
                if self.path.startswith(root + "/git/ref/tags/"):
                    payload = json.dumps({"object": {"type": "tag", "sha": "c" * 40}}).encode()
                elif self.path == root + "/git/tags/" + "c" * 40:
                    payload = json.dumps({"object": {"type": "commit", "sha": test.fixture.fixture.row["source_commit"]}}).encode()
                elif self.path.startswith(root + "/releases/tags/"):
                    payload = json.dumps(test.api).encode()
                elif self.path.startswith("/assets/"):
                    name = urllib.parse.unquote(self.path.removeprefix("/assets/"))
                    payload = (test.fixture.fixture.assets / name).read_bytes()
                elif self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", test.origin + "/assets/SHA256SUMS")
                    self.end_headers()
                    return
                elif self.path == "/oversize":
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"12345")
                    return
                elif self.path == "/truncated":
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"123")
                    return
                elif self.path == "/large-api":
                    self.send_response(200)
                    self.send_header("Content-Length", str(PUBLICATION.API_BYTES + 1))
                    self.end_headers()
                    return
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Set-Cookie", "not-an-authentication-cookie=test")
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.origin = "http://127.0.0.1:" + str(self.server.server_port)
        self.api = deepcopy(self.fixture.api)
        for asset in self.api["assets"]:
            asset["browser_download_url"] = self.origin + "/assets/" + urllib.parse.quote(asset["name"])
        self.transport = PUBLICATION.HTTPTransport(self.origin, socket_timeout=2, api_timeout=4, download_timeout=4)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_real_http_path_peels_annotated_tag_and_downloads_without_credentials(self):
        with mock.patch.dict(os.environ, {
            "GITHUB_TOKEN": "test-value-not-forwarded", "GH_TOKEN": "test-value-not-forwarded",
            "HTTP_PROXY": "http://127.0.0.1:1", "HTTPS_PROXY": "http://127.0.0.1:1",
            "NO_PROXY": "", "no_proxy": "",
        }):
            transport = PUBLICATION.HTTPTransport(self.origin, socket_timeout=2, api_timeout=4, download_timeout=4)
            result = PUBLICATION.authenticate(self.fixture.plan_path, "rtx3090", self.fixture.fixture.directory,
                                               self.fixture.out, transport=transport, clock=lambda: CLOCK)
        self.assertEqual(result["lanes"][0]["tag_commit"], self.fixture.fixture.row["source_commit"])
        self.assertEqual(len(self.requests), len(self.api["assets"]) + 3)
        for _, headers in self.requests:
            self.assertFalse({"authorization", "proxy-authorization", "cookie"} & {name.lower() for name in headers})
            self.assertEqual(headers["Accept-Encoding"], "identity")
        self.assertEqual(next(headers["Accept"] for path, headers in self.requests if "/releases/tags/" in path),
                         "application/vnd.github+json")

    def test_redirect_is_also_anonymous(self):
        expected = (self.fixture.fixture.assets / "SHA256SUMS").read_bytes()
        observed = b"".join(self.transport.download(self.origin + "/redirect", len(expected)))
        self.assertEqual(observed, expected)
        self.assertEqual(len(self.requests), 2)
        self.assertTrue(all("Cookie" not in headers for _, headers in self.requests))

    def test_streaming_size_bounds_and_api_size_limit_refuse(self):
        for path in ("/oversize", "/truncated"):
            with self.subTest(path=path), self.assertRaisesRegex(PUBLICATION.BundleError, "/bytes"):
                list(self.transport.download(self.origin + path, 4))
        with self.assertRaisesRegex(PUBLICATION.BundleError, "/Content-Length"):
            self.transport.api("large-api")

    def test_operation_deadline_stops_a_read_without_sleeping(self):
        clock = mock.Mock()
        clock.monotonic.side_effect = [0, 5]
        with mock.patch.object(PUBLICATION, "time", clock):
            with self.assertRaisesRegex(PUBLICATION.BundleError, "/timeout"):
                list(self.transport.download(self.origin + "/oversize", 4))

    def test_missing_tag_and_disallowed_urls_refuse(self):
        with self.assertRaisesRegex(PUBLICATION.BundleError, "/http_status"):
            self.transport.api("not-found")
        for url in ("http://192.0.2.1/asset", "https://test-value@example.invalid/asset", "file:///asset"):
            with self.subTest(url=url), self.assertRaisesRegex(PUBLICATION.BundleError, "/url"):
                list(self.transport.download(url, 1))

    def test_http_error_closes_its_response(self):
        response = io.BytesIO(b"not found")
        error = urllib.error.HTTPError(self.origin + "/missing", 404, "not found", {}, response)
        with mock.patch.object(self.transport.opener, "open", side_effect=error):
            with self.assertRaisesRegex(PUBLICATION.BundleError, "/http_status"):
                self.transport.api("missing")
        self.assertTrue(response.closed)


class PrivatePublicationGoldenTests(OfflineTestCase):
    def test_retained_public_observation_reproduces_record_byte_for_byte(self):
        registry_path = os.environ.get("OMP_NINFER_PRIVATE_FIXTURES")
        if not registry_path:
            self.skipTest("OMP_NINFER_PRIVATE_FIXTURES is unset")
        fixture = load(Path(registry_path).expanduser())["v0.19.0"]["aggregate"]
        observation = Path(fixture["lane_scripts"]).expanduser() / "public-rtx3090"
        api = load(observation / "release.json")
        refs = dict((line.split()[1], line.split()[0]) for line in (observation / "tag.txt").read_text().splitlines())
        tag = api["tag_name"]
        commit = refs.get("refs/tags/" + tag + "^{}", refs.get("refs/tags/" + tag))
        files = {row["browser_download_url"]: observation / "downloads" / row["name"] for row in api["assets"]}
        transport = FakeTransport(api, commit, files)
        clock = datetime.fromisoformat((observation / "observed-utc.txt").read_text().strip().replace("Z", "+00:00"))
        bundle_root = Path(fixture["bundle_root"]).expanduser()
        bundle = bundle_root / "rtx3090"
        reference = load(bundle / "bundle.json")
        release = reference["release"]
        assets = next(edge for edge in reference["inputs"] if edge["role"] == "assets")
        receipt = load(bundle / Path(assets["path"]).parent / "package-build-receipt.json")
        plan = {
            "artifact_type": "omp_ninfer_release_plan", "schema_version": 1, "release": release,
            "components": [{"id": "rtx3090-windows-native", "disposition": "recut",
                            "release_tag": tag, "source_commit": receipt["patch_stack_sha"]}]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "releases" / release / "plan.json"
            atomic_write_json(plan_path, plan)
            out = root / "publication.json"
            result = PUBLICATION.authenticate(plan_path, "rtx3090", bundle, out,
                                               transport=transport, clock=lambda: clock)
            self.assertEqual(PUBLICATION.json_bytes(result["lanes"][0]),
                             (observation / "authenticated.json").read_bytes())
            self.assertEqual(out.read_bytes(), (bundle_root / "native-publication-rtx3090.json").read_bytes())
            self.assertEqual(len([call for call in transport.calls if call[0] == "download"]), len(api["assets"]))


if __name__ == "__main__":
    unittest.main()
