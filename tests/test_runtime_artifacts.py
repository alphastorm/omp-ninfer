"""Offline runtime asset authentication and the unchanged aggregate consumer."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import aggregate_qualification as AGGREGATE
import runtime_artifacts as RUNTIME
from qualification_bundle import BundleError, Inputs, json_bytes, sha
from release_io import atomic_write, atomic_write_json
from test_native_publication import OfflineTestCase

CLOCK = datetime(2026, 11, 15, 18, 42, 32, tzinfo=timezone.utc)


def load(path):
    return json.loads(path.read_bytes())


def newest_record():
    return max((ROOT / "releases").glob("*/qualification/runtime-artifacts.json"),
               key=lambda path: tuple(map(int, path.parents[1].name[1:].split("."))))


class FakeTransport:
    def __init__(self, releases, files, commit):
        self.releases, self.files, self.commit = releases, files, commit
        self.calls, self.overrides = [], {}

    def tag(self, repository, tag):
        self.calls.append(("tag", repository, tag))
        if repository != RUNTIME.REPOSITORY or tag not in self.releases:
            raise AssertionError("unexpected public tag")
        return self.commit

    def api(self, path):
        self.calls.append(("api", path))
        prefix = f"repos/{RUNTIME.REPOSITORY}/releases/tags/"
        if not path.startswith(prefix):
            raise AssertionError("unexpected public API")
        return deepcopy(self.releases[urllib.parse.unquote(path.removeprefix(prefix))])

    def download(self, url, expected_size):
        self.calls.append(("download", url, expected_size))
        data = self.overrides.get(url, self.files[url])
        for offset in range(0, len(data), 7):
            yield data[offset:offset + 7]


class RuntimeFixture:
    """Reuse retained receipt shapes; replace only the synthetic asset identities."""

    def __init__(self, root):
        self.root, self.release = root, "v99.0.0"
        self.predecessor = newest_record().parents[1]
        self.manifest = load(self.predecessor / "manifest.json")
        self.qualification = load(self.predecessor / "qualification.json")
        self.component = self.manifest["components"]["ninfer"]
        self.source = "a" * 40
        self.tag, self.source_tag, self.runtime_tag = "runtime-test", "source-test", "image-test"
        self.mirror = root / "mirror"
        self.mirror.mkdir()
        self.input_dir = root / "inputs"
        self.input_dir.mkdir()
        self.plan_path = root / "releases" / self.release / "plan.json"
        self.stage_path = self.input_dir / "stage.json"
        self.publication_path = self.input_dir / "publication.json"
        self.identity_path = self.input_dir / "build-identity.json"
        self.base_path = self.input_dir / "base.json"
        self.out = root / "observed/runtime-artifacts.json"
        self.archive_name = "runtime-package.tar.gz"
        self.server = b"synthetic server; never executed\n"
        identity = load(self.predecessor / "qualification/runtime-build-identity.json")
        identity.update(patch_stack_sha=self.source, source_dirty=False)
        identity["binaries"]["ninfer-serve"] = sha(self.server)
        atomic_write_json(self.identity_path, identity)
        self.members = [
            ("runtime-package/LICENSE", b"license\n"),
            ("runtime-package/bin/ninfer-serve", self.server),
            ("runtime-package/build-identity.json", self.identity_path.read_bytes()),
        ]
        self.write_archive()
        self.base = load(self.predecessor / "qualification/runtime-base.json")
        atomic_write_json(self.base_path, self.base)
        self.publication = load(self.predecessor / "qualification/runtime-publication.json")
        self.publication.update(
            source_commit=self.source, release_tag=self.tag, runtime_release_tag=self.runtime_tag,
            binary_asset=self.archive_name, binary_sha256=sha(self.archive),
            runtime_base_receipt_sha256=sha(self.base_path.read_bytes()))
        atomic_write_json(self.publication_path, self.publication)
        self.source_bytes = b"synthetic source archive\n"
        self.source_path = self.input_dir / "source.tar.gz"
        atomic_write(self.source_path, self.source_bytes)
        self.sbom_bytes = json_bytes({"spdxVersion": "SPDX-2.3", "files": []})
        self.checksums_path = self.input_dir / "checksums"
        sums = (sha(self.archive) + "  " + self.archive_name + "\n"
                + sha(self.sbom_bytes) + "  runtime-package.spdx.json\n").encode()
        atomic_write(self.checksums_path, sums)
        self.stage = {
            "source_tag": self.source_tag, "binary_sha": sha(self.server),
            "archive_sha": sha(self.archive), "sbom_sha": sha(self.sbom_bytes),
            "source_archive_sha": sha(self.source_bytes), "source_archive": self.source_path.name,
            "checksums": self.checksums_path.name, "image_digest": self.publication["image_digest"],
            "runtime_receipt_release": self.runtime_tag,
        }
        atomic_write_json(self.stage_path, self.stage)
        self.plan = {
            "artifact_type": "omp_ninfer_release_plan", "schema_version": 1,
            "release": self.release, "predecessor": self.predecessor.name,
            "components": [{"id": "rtx5090-container", "disposition": "recut",
                            "release_tag": self.tag, "source_commit": self.source}],
        }
        atomic_write_json(self.plan_path, self.plan)
        packaging = self.qualification["composition"]["local_release_packaging"]
        base_edge = packaging["runtime_base_receipt"]
        atomic_write(root / base_edge["repository_path"], self.base_path.read_bytes())
        atomic_write_json(root / "releases" / self.predecessor.name / "qualification.json",
                          self.qualification)
        self.releases, self.files = {}, {}
        self.add_asset(self.tag, self.archive_name, self.archive)
        self.add_asset(self.tag, "runtime-package.spdx.json", self.sbom_bytes)
        self.add_asset(self.tag, "runtime-package.SHA256SUMS", sums)
        self.add_asset(self.source_tag, "runtime-source.tar.gz", self.source_bytes)
        self.add_asset(self.runtime_tag, "ninfer-runtime-image-" + self.tag + ".json",
                       self.publication_path.read_bytes())
        self.add_asset(self.publication["runtime_base_receipt_release"], "ninfer-runtime-base.json",
                       self.base_path.read_bytes())
        self.transport = FakeTransport(self.releases, self.files, self.source)

    def write_archive(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name, data in self.members:
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        self.archive = buffer.getvalue()

    def add_asset(self, tag, name, data):
        url = RUNTIME.REPOSITORY_URL + "/releases/download/" + tag + "/" + name
        release = self.releases.setdefault(tag, {
            "tag_name": tag, "draft": False,
            "html_url": RUNTIME.REPOSITORY_URL + "/releases/tag/" + tag,
            "published_at": "2026-11-15T18:00:00Z", "assets": []})
        release["assets"].append({"name": name, "size": len(data), "digest": "sha256:" + sha(data),
                                  "browser_download_url": url})
        self.files[url] = data
        atomic_write(self.mirror / name, data)

    def reseal_archive(self):
        self.write_archive()
        self.stage["archive_sha"] = sha(self.archive)
        atomic_write_json(self.stage_path, self.stage)
        self.publication["binary_sha256"] = sha(self.archive)
        atomic_write_json(self.publication_path, self.publication)
        replacements = {
            self.archive_name: self.archive,
            "ninfer-runtime-image-" + self.tag + ".json": self.publication_path.read_bytes(),
        }
        for release in self.releases.values():
            for row in release["assets"]:
                if row["name"] in replacements:
                    data = replacements[row["name"]]
                    row.update(size=len(data), digest="sha256:" + sha(data))
                    self.files[row["browser_download_url"]] = data
                    atomic_write(self.mirror / row["name"], data)

    def run(self, **kwargs):
        return RUNTIME.authenticate(
            self.plan_path, self.stage_path, self.publication_path, self.identity_path,
            self.mirror, self.out, transport=self.transport, clock=lambda: CLOCK, **kwargs)

    def consume(self):
        component = self.component
        component.update(
            source_commit=self.source, release_tag=self.tag,
            server_binary_sha256=self.stage["binary_sha"],
            binary_archive_sha256=self.stage["archive_sha"], sbom_sha256=self.stage["sbom_sha"],
            source_archive_sha256=self.stage["source_archive_sha"],
            source_archive_bytes=len(self.source_bytes), checksums_sha256=sha(self.checksums_path.read_bytes()),
            oci_manifest_digest=self.stage["image_digest"], runtime_receipt_release=self.runtime_tag)
        for key, name in (("binary_archive_url", self.archive_name), ("sbom_url", "runtime-package.spdx.json"),
                          ("source_archive_url", "runtime-source.tar.gz")):
            component[key] = next(url for url in self.files if url.endswith("/" + name))
        rc_path = self.input_dir / "runtime-rc.json"
        rc = load(self.predecessor / "qualification/runtime-rc.json")
        rc["source_commit"] = self.source
        atomic_write_json(rc_path, rc)
        return AGGREGATE._runtime_outputs(
            Inputs(), self.root, self.release, self.manifest, self.qualification,
            self.publication_path,
            {"artifacts": self.out, "build_identity": self.identity_path, "rc": rc_path})


class RuntimeArtifactsTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = RuntimeFixture(Path(temporary.name))

    def test_round_trip_accepts_the_unchanged_aggregate_consumer(self):
        fixture = self.fixture
        result = fixture.run()
        self.assertEqual(result, load(fixture.out))
        outputs = fixture.consume()
        self.assertEqual(len(outputs), 5)
        self.assertEqual(result["packaged_server_sha256"], sha(fixture.server))
        self.assertEqual(len(result["package_files_sha256"]), len(fixture.members))
        self.assertEqual(len([call for call in fixture.transport.calls if call[0] == "download"]), 6)

    def test_exact_key_parity_with_the_newest_committed_record(self):
        result, retained = self.fixture.run(), load(newest_record())
        self.assertEqual(set(result), set(retained))
        self.assertTrue(all(set(row) == set(retained["assets"][0]) for row in result["assets"]))

    def test_public_api_digest_mismatch_refuses_without_a_partial_record(self):
        self.fixture.releases[self.fixture.tag]["assets"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(BundleError, "/digest"):
            self.fixture.run()
        self.assertFalse(self.fixture.out.exists())

    def test_duplicate_digest_refuses(self):
        row = deepcopy(self.fixture.releases[self.fixture.tag]["assets"][0])
        row["name"] = "duplicate.tar.gz"
        self.fixture.releases[self.fixture.tag]["assets"].append(row)
        with self.assertRaisesRegex(BundleError, "digest"):
            self.fixture.run()
        self.assertFalse(self.fixture.out.exists())

    def test_extra_asset_refuses(self):
        self.fixture.add_asset(self.fixture.tag, "unexpected.txt", b"unexpected\n")
        with self.assertRaisesRegex(BundleError, "digest"):
            self.fixture.run()
        self.assertFalse(self.fixture.out.exists())

    def test_truncated_oversized_and_changed_downloads_refuse(self):
        fixture = self.fixture
        url = next(url for url in fixture.files if url.endswith(".tar.gz"))
        data = fixture.files[url]
        for replacement, pointer in ((data[:-1], "bytes"), (data + b"x", "bytes"),
                                     (bytes([data[0] ^ 1]) + data[1:], "sha256")):
            with self.subTest(pointer=pointer):
                fixture.transport.overrides[url] = replacement
                with self.assertRaisesRegex(BundleError, "/" + pointer):
                    fixture.run()
                self.assertFalse(fixture.out.exists())

    def test_mirror_mismatch_and_symlink_refuse(self):
        fixture = self.fixture
        path = fixture.mirror / fixture.archive_name
        data = path.read_bytes()
        atomic_write(path, data[:-1] + bytes([data[-1] ^ 1]))
        with self.assertRaisesRegex(BundleError, "SHA-256 mismatch"):
            fixture.run()
        path.unlink()
        path.symlink_to(fixture.source_path)
        with self.assertRaisesRegex(BundleError, "regular file"):
            fixture.run()
        self.assertFalse(fixture.out.exists())

    def test_wrong_tag_commit_refuses_before_downloads(self):
        self.fixture.transport.commit = "b" * 40
        with self.assertRaisesRegex(BundleError, "/peeled_commit"):
            self.fixture.run()
        self.assertFalse(any(call[0] == "download" for call in self.fixture.transport.calls))

    def test_dirty_build_identity_refuses(self):
        value = load(self.fixture.identity_path)
        value["source_dirty"] = True
        atomic_write_json(self.fixture.identity_path, value)
        with self.assertRaisesRegex(BundleError, "build identity"):
            self.fixture.run()
        self.assertFalse(self.fixture.out.exists())

    def test_two_server_members_refuse(self):
        fixture = self.fixture
        fixture.members.append(("second-package/bin/ninfer-serve", fixture.server))
        fixture.reseal_archive()
        with self.assertRaisesRegex(BundleError, "/package_files_sha256"):
            fixture.run()
        self.assertFalse(fixture.out.exists())

    def test_unsafe_duplicate_and_excess_tar_members_refuse(self):
        fixture = self.fixture
        original = list(fixture.members)
        for name in ("/absolute", "../escape", "root/../escape", original[0][0]):
            with self.subTest(name=name):
                fixture.members = original + [(name, b"unsafe")]
                fixture.reseal_archive()
                with self.assertRaises(BundleError):
                    fixture.run()
                self.assertFalse(fixture.out.exists())
        fixture.members = original
        fixture.reseal_archive()
        with mock.patch.object(RUNTIME, "MAX_TAR_MEMBERS", 2):
            with self.assertRaisesRegex(BundleError, "member cap"):
                fixture.run()

    def test_changed_base_requires_explicit_override(self):
        fixture = self.fixture
        edge = fixture.qualification["composition"]["local_release_packaging"]["runtime_base_receipt"]
        atomic_write(fixture.root / edge["repository_path"], b"stale base\n")
        with self.assertRaisesRegex(BundleError, "--runtime-base"):
            fixture.run()
        fixture.run(runtime_base=fixture.base_path)

    def test_carried_lane_and_mismatched_publication_refuse(self):
        fixture = self.fixture
        fixture.plan["components"][0]["disposition"] = "carried"
        atomic_write_json(fixture.plan_path, fixture.plan)
        with self.assertRaisesRegex(BundleError, "/disposition"):
            fixture.run()
        fixture.plan["components"][0]["disposition"] = "recut"
        atomic_write_json(fixture.plan_path, fixture.plan)
        fixture.publication["secret_free"] = False
        atomic_write_json(fixture.publication_path, fixture.publication)
        with self.assertRaisesRegex(BundleError, "publication"):
            fixture.run()
        self.assertEqual(fixture.transport.calls, [])

    def test_check_reobserves_and_ignores_only_as_of(self):
        fixture = self.fixture
        fixture.run()
        before = fixture.out.read_bytes()
        fixture.transport.calls.clear()
        fixture.run(check=True, as_of="2026-11-16")
        self.assertEqual(fixture.out.read_bytes(), before)
        self.assertEqual(len([call for call in fixture.transport.calls if call[0] == "download"]), 6)
        fixture.releases[fixture.tag]["assets"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(BundleError, "/digest"):
            fixture.run(check=True)
        self.assertEqual(fixture.out.read_bytes(), before)

    def test_check_refuses_changed_record_and_missing_record(self):
        fixture = self.fixture
        with self.assertRaisesRegex(BundleError, "existing"):
            fixture.run(check=True)
        fixture.run()
        value = load(fixture.out)
        value["status"] = "failed"
        atomic_write_json(fixture.out, value)
        with self.assertRaisesRegex(BundleError, "record differs"):
            fixture.run(check=True)
        value["as_of"] = "not a timestamp"
        atomic_write_json(fixture.out, value)
        with self.assertRaisesRegex(BundleError, "/as_of"):
            fixture.run(check=True)

    def test_refusal_preserves_existing_output_and_protects_inputs(self):
        fixture = self.fixture
        atomic_write(fixture.out, b"retained record\n")
        fixture.transport.commit = "b" * 40
        with self.assertRaises(BundleError):
            fixture.run()
        self.assertEqual(fixture.out.read_bytes(), b"retained record\n")
        fixture.transport.commit = fixture.source
        fixture.out = fixture.stage_path
        before = fixture.stage_path.read_bytes()
        with self.assertRaisesRegex(BundleError, "/out"):
            fixture.run()
        self.assertEqual(fixture.stage_path.read_bytes(), before)

    def test_input_change_during_observation_refuses(self):
        fixture = self.fixture
        original = fixture.transport.download

        def changing_download(url, size):
            yield from original(url, size)
            atomic_write(fixture.stage_path, fixture.stage_path.read_bytes() + b"\n")

        with mock.patch.object(fixture.transport, "download", side_effect=changing_download):
            with self.assertRaisesRegex(BundleError, "input changed"):
                fixture.run()
        self.assertFalse(fixture.out.exists())

    def test_cli_authenticates_then_checks_without_writing(self):
        fixture = self.fixture
        args = ["--plan", str(fixture.plan_path), "--stage-input", str(fixture.stage_path),
                "--runtime-publication", str(fixture.publication_path),
                "--runtime-build-identity", str(fixture.identity_path),
                "--mirror", str(fixture.mirror), "--out", str(fixture.out)]
        for mode, status in (([], "authenticated"), (["--check"], "checked")):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(RUNTIME.main(args + mode, transport=fixture.transport, clock=lambda: CLOCK), 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], status)
            self.assertEqual(stderr.getvalue(), "")
        fixture.transport.commit = "b" * 40
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(RUNTIME.main(args, transport=fixture.transport, clock=lambda: CLOCK), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("runtime artifacts refused", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
