"""Host-free native lifecycle/capture rehearsal; no Windows or GPU qualification is inferred."""
from __future__ import annotations

import argparse
import hashlib
import http.server
import importlib.util
import json
import os
import sys
import tempfile
import threading
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import native_screen_arm as NATIVE
import quality_screen as SCREEN
from redaction_screen import ScreenError, native_arm, run_identity


def arm_identity(candidate=False, determinism=False):
    return {"artifact_type": "omp_ninfer_screen_arm", "schema_version": 1, "kind": "native-windows",
            "lane": "rtx3090", "release_id": "qwen38-3090-native-v0.8.0-beta.1",
            "package_sha256": ("b" if candidate else "a") * 64,
            "server_binary_sha256": ("d" if candidate else "c") * 64,
            "configuration_sha256": ("f" if candidate else "e") * 64,
            "model_artifact_sha256": "1" * 64, "gpu_name": "NVIDIA GeForce RTX 3090",
            "power_limit_w": 350, "endpoint_port": 18082, "concurrency": 1, "reasoning": "low",
            "fresh_start": {"cache_root_empty": True,
                            "process_started_utc": "2026-10-30T0" + ("3" if determinism else "2") + ":00:00Z"},
            "prompts_sha256": ("3" if determinism else "2") * 64}


FROZEN_CASE_IDS = [row["id"] for row in json.loads(
    (ROOT / "docs/measurements/2026-10-25-exp097-role-corpus.json").read_text())["cases"]]
FROZEN_CONTROLS = {"log-023", "log-024", "repo-029", "repo-030",
                   "worklog-007", "worklog-008", "worklog-014"}
FROZEN_SCREEN_IDS = SCREEN.screen_order(FROZEN_CASE_IDS, FROZEN_CONTROLS)


def screen_run_identity(role):
    ids = FROZEN_SCREEN_IDS[:80] if "determinism" in role else FROZEN_SCREEN_IDS
    return {"arm": arm_identity("candidate" in role, "determinism" in role),
            "prompt_count": len(ids),
            "prompt_ids_sha256": hashlib.sha256(
                json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest()}


class NativeIdentityTests(unittest.TestCase):
    def identities(self):
        return {role: screen_run_identity(role)
                for role in ("production", "candidate", "production_determinism", "candidate_determinism")}

    def test_verdict_refuses_partial_or_wrong_frozen_membership_before_deciding(self):
        for role, field, value in (
            ("production", "prompt_count", 1119),
            ("candidate", "prompt_ids_sha256", "0" * 64),
            ("production_determinism", "prompt_count", 79),
            ("candidate_determinism", "prompt_ids_sha256", "0" * 64),
        ):
            runs = self.identities()
            runs[role][field] = value
            args = argparse.Namespace(**{key: Path(key) for key in runs})
            with self.subTest(role=role, field=field), \
                    patch.object(SCREEN, "run_identity", side_effect=runs.values()), \
                    patch.object(SCREEN, "load_run", return_value={}), \
                    patch.object(SCREEN, "decide") as decide:
                with self.assertRaisesRegex(ScreenError, "frozen corpus membership"):
                    SCREEN.verdict(args)
                decide.assert_not_called()

    def test_native_preconditions_and_legacy_container_identity(self):
        SCREEN.validate_native_arms(self.identities())
        SCREEN.validate_native_arms({role: {} for role in self.identities()})
        for role, field, value in (
            ("candidate", "model_artifact_sha256", "4" * 64),
            ("candidate", "power_limit_w", 300),
            ("candidate", "server_binary_sha256", "c" * 64),
            ("candidate_determinism", "configuration_sha256", "4" * 64),
            ("production_determinism", "package_sha256", "4" * 64),
            ("production_determinism", "fresh_start", {"cache_root_empty": True,
                                                       "process_started_utc": "2026-10-30T02:00:00Z"}),
        ):
            with self.subTest(role=role, field=field):
                runs = self.identities()
                runs[role]["arm"][field] = value
                with self.assertRaises(ScreenError):
                    SCREEN.validate_native_arms(runs)
        runs = self.identities()
        del runs["production_determinism"]["arm"]
        with self.assertRaises(ScreenError):
            SCREEN.validate_native_arms(runs)

    def test_public_arm_contract_excludes_private_fields_and_invalid_freshness(self):
        for change in ({"gpu_uuid": "private"}, {"host": "private"}, {"key": "private"},
                       {"endpoint_port": 18083}, {"concurrency": 2}, {"power_limit_w": True},
                       {"lane": "rtx5090"}, {"configuration_sha256": "bad"},
                       {"fresh_start": {"cache_root_empty": False, "process_started_utc": "bad"}}):
            with self.subTest(change=change), self.assertRaises(ScreenError):
                native_arm({**arm_identity(), **change})

    def test_redaction_identity_keeps_legacy_runs_and_includes_only_valid_arm(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            for name, value in (("manifest.json", {"label": "legacy"}), ("scores.json", {})):
                NATIVE.save(run / name, value)
            (run / "responses.jsonl").write_text("")
            self.assertNotIn("arm", run_identity(run))
            NATIVE.save(run / "arm.json", arm_identity())
            self.assertEqual(run_identity(run)["arm"], arm_identity())
            NATIVE.save(run / "arm.json", {**arm_identity(), "host": "private"})
            with self.assertRaises(ScreenError):
                run_identity(run)

    def test_native_membership_seals_reject_duplicates_or_missing_responses(self):
        self.assertEqual(list(SCREEN.FROZEN_CASE_IDS), FROZEN_CASE_IDS)
        self.assertEqual(SCREEN.FROZEN_CONTROLS, FROZEN_CONTROLS)
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            NATIVE.save(run / "manifest.json", {})
            NATIVE.save(run / "arm.json", arm_identity())
            for scored, responses in (
                (["log-001.v0", "log-001.v0"], ["log-001.v0"]),
                (["log-001.v0"], ["log-001.v0", "log-001.v0"]),
                (["log-001.v0"], ["log-002.v0"]),
            ):
                NATIVE.save(run / "scores.json", {"per_case": [{"case_id": value} for value in scored]})
                (run / "responses.jsonl").write_text(
                    "".join(json.dumps({"case_id": value}) + "\n" for value in responses))
                with self.subTest(scored=scored, responses=responses), self.assertRaisesRegex(
                        ScreenError, "match without duplicates"):
                    run_identity(run)

    def test_verdict_checks_identity_before_statistical_decision(self):
        with patch.object(SCREEN, "run_identity", side_effect=self.identities().values()), \
                patch.object(SCREEN, "load_run", return_value={}), patch.object(SCREEN, "decide", return_value={}) as decide:
            args = argparse.Namespace(**{key: Path(key) for key in self.identities()})
            SCREEN.verdict(args)
            decide.assert_called_once()
        runs = self.identities()
        runs["candidate_determinism"]["arm"]["package_sha256"] = "0" * 64
        with patch.object(SCREEN, "run_identity", side_effect=runs.values()), patch.object(SCREEN, "decide") as decide:
            with self.assertRaises(ScreenError):
                SCREEN.verdict(args)
            decide.assert_not_called()


# This fixture executor makes real HTTP requests; the fixture scorer emits synthetic metrics.
# It is deliberately not the private scorer and proves plumbing, not model quality.
EXECUTOR = '''import argparse,json,os,urllib.request
from pathlib import Path
p=argparse.ArgumentParser()
for x in ('model','base-url','cases','fixtures','out','concurrency','reasoning-mode','reasoning-wire','reasoning-token-headroom','temperature','timeout','label'): p.add_argument('--'+x)
p.add_argument('--no-ssh',action='store_true')
a=p.parse_args()
assert (a.concurrency,a.reasoning_mode,a.reasoning_wire,a.reasoning_token_headroom,a.temperature)==('1','low','top-level','8192','0')
out=Path(a.out);out.mkdir()
rows=[]
for f in sorted(Path(a.cases).glob('*.jsonl')):
 for line in f.read_text().splitlines():
  c=json.loads(line)
  request=urllib.request.Request(a.base_url+'/chat/completions',data=json.dumps({'messages':[{'role':'user','content':c['case_id']}]}).encode(),headers={'Authorization':'Bearer '+os.environ['LOCAL_5090_API_KEY'],'Content-Type':'application/json'})
  with urllib.request.urlopen(request) as response: answer=json.load(response)
  rows.append({'case_id':c['case_id'],'content':answer['choices'][0]['message']['content'],'reasoning':''})
(out/'responses.jsonl').write_text(''.join(json.dumps(r)+'\\n' for r in rows))
(out/'manifest.json').write_text(json.dumps({'label':a.label}))
'''
SCORER = '''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run');p.add_argument('--cases');a=p.parse_args();out=Path(a.run)
rows=[]
for line in (out/'responses.jsonl').read_text().splitlines():
 r=json.loads(line);rows.append({'case_id':r['case_id'],'is_redaction_control':r['case_id'].split('.v')[0] in ('log-023','log-024','repo-029','repo-030','worklog-007','worklog-008','worklog-014'),'required_facts_found':1,'required_facts_total':1,'citations_supported':1,'citations_total':1,'schema_valid':True,'tool_evaluable':True,'tool_selection_ok':True,'tool_argument_ok':True})
(out/'scores.json').write_text(json.dumps({'per_case':rows}))
'''
CONTROL = '''import json,sys
from pathlib import Path
from datetime import datetime,timezone
args=sys.argv;root=Path(args[args.index('-StateRoot')+1]);action=args[args.index('-Action')+1]
if action=='Start':
 state=json.loads((root/'state.json').read_text());rid=state['active_release']
 now=datetime.now(timezone.utc);delta=now-datetime(1,1,1,tzinfo=timezone.utc);ticks=(delta.days*86400+delta.seconds)*10000000+delta.microseconds*10
 (root/'runtime.json').write_text(json.dumps({'release_id':rid,'gpu_uuid_verified':True,'gpu_name':'NVIDIA GeForce RTX 3090','start_time_utc_ticks':ticks}))
'''


class NativeCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        state = self.root / "screen-prod" / "qwen38-3090-native"
        state.mkdir(parents=True)
        receipts = state / "receipts"
        receipts.mkdir()
        config = state / "server-config.json"
        config.write_text(json.dumps({"model_id": "qwen3.8-27b"}))
        binary, model = state / "server.exe", state / "model.ninfer"
        binary.write_bytes(b"server")
        model.write_bytes(b"model")
        release_id = "qwen38-3090-native-v0.8.0-beta.1"
        self.release = {"release_id": release_id, "host": "127.0.0.1", "port": 18082,
                        "receipts_root": str(receipts), "config_file": str(config),
                        "server_executable": str(binary), "model_artifact": str(model),
                        "binary_sha256": NATIVE.digest(binary), "config_sha256": NATIVE.digest(config),
                        "model_artifact_sha256": NATIVE.digest(model), "package_sha256": "a" * 64,
                        "gpu_name": "NVIDIA GeForce RTX 3090", "gpu_uuid": "private-gpu",
                        "cache_root": str(state / "cache" / release_id)}
        NATIVE.save(state / "state.json", {"artifact_type": "ninfer_windows_lifecycle_state", "schema_version": 4,
                    "task_name": "NInfer-Qwen38-3090-Native-Scratch-screen-prod", "active_release": release_id,
                    "releases": {release_id: self.release}})
        self.spec = {"lifecycle": {"task_name": "NInfer-Qwen38-3090-Native",
                                  "state_root_name": state.name, "listen_port": 18082,
                                  "gpu_owner_controller_protocol": {"qualified_power_limit_w": 350}}}
        NATIVE.save(receipts / "release-spec.json", self.spec)
        qualification = self.root / "qualification"
        (qualification / "scripts").mkdir(parents=True)
        (qualification / "scripts/run_qualification.py").write_text(EXECUTOR)
        (qualification / "scripts/score_qualification.py").write_text(SCORER)
        fixtures = self.root / "fixtures"
        fixtures.mkdir()
        (fixtures / "fixture").write_text("synthetic")
        prompts = self.root / "screen.jsonl"
        prompts.write_text(''.join(json.dumps({"case_id": f"log-001.v{i}"}) + "\n" for i in range(4)))
        control = self.root / "Control-Release.ps1"
        control.write_text(CONTROL)
        key = self.root / "key"
        key.write_text("test-key")
        self.args = argparse.Namespace(state_root=state, key_file=key, prompts=prompts, out=self.root / "run",
            qualification=qualification, fixtures=fixtures, fresh=True, resume=False, power_limit_w=350,
            shard_size=2, max_shards=1, install_cmd=[sys.executable, "Install-Release.ps1", "-ScratchTaskSuffix",
            "screen-prod", "-StateRoot", str(state), "-NoStart"],
            stop_cmd=[sys.executable, str(control), "-Action", "Stop", "-StateRoot", str(state)],
            start_cmd=[sys.executable, str(control), "-Action", "Start", "-StateRoot", str(state)],
            production_stop_cmd=[sys.executable, str(control), "-Action", "Stop", "-StateRoot", str(self.root / "product")])

    def test_active_endpoint_comes_from_record_and_must_equal_spec_port(self):
        release, _ = NATIVE.active_release(self.args.state_root, "screen-prod")
        self.assertEqual(release["endpoint"], "http://127.0.0.1:18082")
        record = NATIVE.load(self.args.state_root / "state.json")
        record["releases"][self.release["release_id"]]["host"] = "100.101.102.103"
        NATIVE.save(self.args.state_root / "state.json", record)
        self.assertEqual(NATIVE.active_release(self.args.state_root, "screen-prod")[0]["endpoint"],
                         "http://100.101.102.103:18082")
        self.spec["lifecycle"]["listen_port"] = 18083
        NATIVE.save(Path(self.release["receipts_root"]) / "release-spec.json", self.spec)
        with self.assertRaisesRegex(ScreenError, "18082"):
            NATIVE.active_release(self.args.state_root, "screen-prod")

    def test_uncapped_lane_screens_at_owner_power_only(self):
        spec = {"lifecycle": {"gpu_owner_controller_protocol": {"qualified_power_limit_w": None,
                                                                "owner_power_limit_w": 450}}}
        release = {**self.release, "gpu_name": "NVIDIA GeForce RTX 4090"}
        reply = type("Reply", (), {"stdout": "NVIDIA GeForce RTX 4090, 450.00\n"})()
        with patch.object(NATIVE.subprocess, "run", return_value=reply):
            self.assertEqual(NATIVE.measured_power(release, spec, 450), 450.0)
            with self.assertRaisesRegex(ScreenError, "qualification"):
                NATIVE.measured_power(release, spec, 350)

    def test_cache_cleanup_never_targets_product_or_symlink(self):
        release = {**self.release, "cache_root": str(self.root / "product")}
        with self.assertRaises(ScreenError):
            NATIVE.empty_cache(self.args.state_root, release)
        cache = Path(self.release["cache_root"])
        cache.parent.mkdir(parents=True)
        cache.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ScreenError):
            NATIVE.empty_cache(self.args.state_root, self.release)

    def start_stub(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({"data": [{"id": "qwen3.8-27b"}]}).encode())
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({"choices": [{"message": {"content": body['messages'][0]['content']}}]}).encode())
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 18082), Handler)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        return server

    def test_local_stub_capture_resume_and_seal_tamper(self):
        self.start_stub()
        with patch.object(NATIVE, "measured_power", return_value=350):
            first = NATIVE.run_arm(self.args)
            self.assertEqual(first["status"], "shard-complete")
            self.assertFalse((self.args.out / "arm.json").exists())
            self.args.resume = True
            second = NATIVE.run_arm(self.args)
            self.assertEqual(second["status"], "complete")
            self.assertEqual(len(SCREEN.load_run(self.args.out)), 4)
            identity = run_identity(self.args.out)
            self.assertEqual(identity["arm"]["endpoint_port"], 18082)
            self.assertNotIn("private-gpu", json.dumps(identity))
            self.assertNotIn(str(self.root), json.dumps(identity))
            (self.args.out / "shard-0000/attempt-0000/responses.jsonl").write_text("tampered\n")
            with self.assertRaises((ScreenError, ValueError)):
                NATIVE.run_arm(self.args)

    def test_host_free_1120_prompt_capture_and_native_verdict(self):
        self.start_stub()
        ids = FROZEN_SCREEN_IDS
        self.assertEqual(len(ids), 1120)
        self.args.prompts.write_text("".join(json.dumps({"case_id": value}) + "\n" for value in ids))
        subset = self.root / "subset.jsonl"
        subset.write_text("".join(json.dumps({"case_id": value}) + "\n" for value in ids[:80]))
        screen = self.args.prompts
        self.args.max_shards = 12
        self.args.shard_size = 100
        runs = {}
        with patch.object(NATIVE, "measured_power", return_value=350):
            for role in ("production", "production_determinism", "candidate", "candidate_determinism"):
                if role == "candidate":
                    Path(self.release["server_executable"]).write_bytes(b"candidate")
                    self.release["binary_sha256"] = NATIVE.digest(Path(self.release["server_executable"]))
                    self.release["package_sha256"] = "b" * 64
                    state = NATIVE.load(self.args.state_root / "state.json")
                    state["releases"][self.release["release_id"]] = self.release
                    NATIVE.save(self.args.state_root / "state.json", state)
                self.args.prompts = subset if "determinism" in role else screen
                self.args.out = self.root / role
                self.assertEqual(NATIVE.run_arm(self.args)["status"], "complete")
                runs[role] = self.args.out
        result = SCREEN.verdict(argparse.Namespace(**runs))
        self.assertEqual(result["counted_prompts"], 1120)
        self.assertEqual(result["validity"]["determinism_subset"], 80)
        self.assertEqual(result["verdict"], "pass")
        self.assertTrue(result["validity"]["valid"])
        self.assertFalse(result["raw_prompts_outputs_or_secrets_included"])

    def test_failed_capture_always_stops_and_has_no_completion(self):
        def fresh_arm(*_):
            value = arm_identity()
            value["fresh_start"]["process_started_utc"] = datetime.now(timezone.utc).isoformat()
            return value
        with patch.object(NATIVE, "hook") as hook, \
                patch.object(NATIVE, "capture_endpoint", side_effect=ScreenError("failed")) as capture, \
                patch.object(NATIVE, "measured_power", return_value=350), \
                patch.object(NATIVE, "arm_record", side_effect=fresh_arm):
            with self.assertRaisesRegex(ScreenError, "^failed$"):
                NATIVE.run_arm(self.args)
            capture.assert_called_once()
            self.assertEqual(hook.call_args.args[0], self.args.stop_cmd)
            self.assertFalse((self.args.out / "shard-0000/complete.json").exists())


if __name__ == "__main__":
    unittest.main()
