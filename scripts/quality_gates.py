#!/usr/bin/env python3
"""Risk-tiered, same-lane quality gates. Raw captures and caches MUST remain private.

cache captures one shipped 84-case role arm or the targeted 200-prompt math arm.
t1 compares actual retained role-output bytes; t2 adds token divergence, JSON/tool
checks, exact long retrieval and a bound FP64-op receipt; t3 consumes held-out PPL
first, then evaluates the bounded claim/secret screen. EXP-085 stays separate.
Run on the GPU host under its external lock/lease; see docs/VARIANT-CAMPAIGNS.md.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent / "hosts"))
import variant_campaign as host
import quality_screen as quality

ROLE_RULE = {"cases": 84, "temperature": 0, "max_divergent_fraction": 0.10,
             "max_task_failures": 0, "retrieval_prompt_tokens": 130048,
             "retrieval_answer": "ORCHID=493817; COLOR=COBALT"}
MATH_RULE = {"prompts": 200, "claim_prompts": 100, "secret_prompts": 100,
             "max_new_unsupported": 6, "max_new_secret_cases": 0,
             "early_identical_pairs": 100,
             "early_pass": "all retained bytes identical, every selected case covered, PPL pass",
             "early_fail": "any new secret leak, task failure, or more than six introduced unsupported claims",
             "final_pass": "all 200 paired, zero new secret cases, at most six introduced unsupported claims, no task/error failures",
             "interpretation": "pre-registered finite risk screen; not EXP-085 or a powered statistical verdict"}
PPL_RULE = {"max_overall_delta_nll": 0.02, "max_domain_delta_nll": 0.05,
            "contexts": [1024, 2048], "strides": [512, 1024]}
FP64_TESTS = ("ninfer_linear_add_q5_a16_test", "ninfer_linear_swiglu_q4_a16_test",
              "ninfer_linear_split_two_output_test", "ninfer_linear_split_multi_output_test")


def records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def source_sha(version: str) -> str:
    match = re.search(r"patch_stack_sha=([0-9a-f]{40})(?:\s|$)", version)
    if not match:
        raise quality.ScreenError("binary version does not identify its exact source commit")
    return match[1]


def sample_plan(cases: Path, kind: str, shard_size: int) -> tuple[dict[str, Any], dict[str, bytes]]:
    source = quality.load_cases(cases)
    if len(source) != ROLE_RULE["cases"] or len({row[0] for row in source}) != ROLE_RULE["cases"]:
        raise quality.ScreenError("risk gates require the complete frozen 84 counted cases")
    if not 1 <= shard_size <= 200:
        raise quality.ScreenError("shard size must be in [1, 200]")
    categories: dict[str, str] = {}
    if kind == "role":
        rows = [json.loads(line) for _, line, _ in source]
    else:
        controls = [json.loads(line) for _, line, control in source if control]
        classes: dict[str, list[dict[str, Any]]] = {}
        for _, line, control in source:
            case = json.loads(line)
            if not control and (case["oracle"].get("forbidden_claims") or case["oracle"].get("support_spans")):
                classes.setdefault(case["class"], []).append(case)
        selected = []
        while len(selected) < 50 and any(classes.values()):
            for name in sorted(classes):
                if classes[name] and len(selected) < 50:
                    selected.append(classes[name].pop(0))
        if len(selected) != 50 or not controls:
            raise quality.ScreenError("targeted math screen needs 50 grounded claim cases and secret controls")
        prefixes = quality.variant_prefixes(72)
        rows = []
        for i in range(100):
            for pool, category in ((selected, "claims"), (controls, "secrets")):
                case = json.loads(json.dumps(pool[i % len(pool)]))
                variant = i // len(pool)
                case["case_id"] = quality.variant_id(case["case_id"], variant)
                case["input"]["task"] = prefixes[variant] + case["input"]["task"]
                categories[case["case_id"]] = category
                rows.append(case)
    files, jobs = {}, []
    for number, start in enumerate(range(0, len(rows), shard_size)):
        group = rows[start:start + shard_size]
        name = f"prompts/{number:04d}.jsonl"
        data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in group).encode("utf-8")
        files[name] = data
        jobs.append({"id": f"capture-{number:04d}", "cases": name,
                     "cases_sha256": hashlib.sha256(data).hexdigest(),
                     "prompt_ids": [row["case_id"] for row in group]})
    return {"kind": kind, "shard_size": shard_size, "prompts": len(rows), "jobs": jobs,
            "categories": categories, "selected_cases": sorted({quality.base_id(row["case_id"]) for row in rows})}, files


def token_ids(capture: Path, responses: list[dict[str, Any]]) -> dict[str, list[int]]:
    events = host.log_records(capture / "requests.jsonl")
    done = [row for row in events if row.get("event") == "request_done"]
    if len(done) != len(responses) or any(row.get("event") == "request_error" for row in events):
        raise quality.ScreenError("capture must bind one successful server request per corpus response")
    ids = [row.get("request", {}).get("request_id") for row in done]
    if any(type(value) is not int or value < 0 for value in ids) or len(set(ids)) != len(ids):
        raise quality.ScreenError("token traces require unique ordered server request identities")
    done.sort(key=lambda row: row["request"]["request_id"])
    result = {}
    for response, event in zip(responses, done):
        values = event["result"].get("generated_token_ids")
        count = event["result"]["completion_tokens"]
        if (response.get("attempt") != 1 or not isinstance(values, list)
                or any(type(value) is not int or value < 0 for value in values)
                or len(values) != count or not isinstance(response.get("usage"), dict)
                or response["usage"].get("completion_tokens") != count):
            raise quality.ScreenError("token trace identity/count/retry differs from ordered greedy capture")
        result[response["case_id"]] = values
    return result


def capture_evidence(directory: Path, job: dict[str, Any], identity: dict[str, Any], contract: dict[str, Any],
                     *, verify_only: bool = False) -> dict[str, Any]:
    evidence = quality.verified_capture(host, directory, job, identity, contract)
    responses = records(directory / "quality/responses.jsonl")
    tokens = token_ids(directory, responses)
    projection = {row["case_id"]: base64.b64encode(quality.response_bytes(row, include_finish_reason=True)).decode("ascii")
                  for row in responses}
    for name, value in (("token-ids.json", tokens), ("output-bytes.json", projection)):
        data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        quality.frozen_file(directory / name, data, verify_only=verify_only)
        if not verify_only:
            (directory / name).chmod(0o600)
    evidence["private_files"] = {name: host.sha256_file(directory / name) for name in
                                 ("requests.jsonl", "token-ids.json", "output-bytes.json")}
    return evidence


def verified_cell(root: Path, manifest: dict[str, Any], job: dict[str, Any], arm: str) -> Path:
    seal = host.load(root / job["id"] / "complete.json")
    directory = root / job["id"] / seal["capture"]
    actual = {"manifest_sha256": host.digest(manifest), "job": job, "capture": seal["capture"],
              "evidence": capture_evidence(directory, job, manifest["identity"]["arms"][arm],
                                           manifest["identity"]["capture_contract"], verify_only=True)}
    if actual != seal:
        raise quality.ScreenError("risk capture seal changed")
    return directory


def verify_cache(root: Path, layout: dict[str, Any], fingerprint: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Path]]:
    artifact = host.load(root / "baseline.json")
    manifest = host.load(root / "campaign.json")
    if artifact.get("artifact_type") != "omp-ninfer.risk-baseline" or artifact["manifest_sha256"] != host.digest(manifest):
        raise quality.ScreenError("stored risk baseline identity changed")
    if manifest["layout"] != layout:
        raise quality.ScreenError("stored risk baseline prompt/order/shard plan changed")
    for field in ("lane", "inputs", "capture_contract", "preregistration_sha256", "tools"):
        if manifest["identity"][field] != fingerprint[field]:
            raise quality.ScreenError(f"stored risk baseline {field} changed")
    if manifest["identity"]["arms"]["A"] != fingerprint["arms"]["A"]:
        raise quality.ScreenError("stored risk baseline binary/model/profile/GPU identity changed")
    if manifest["gate_tool_sha256"] != host.sha256_file(Path(__file__)):
        raise quality.ScreenError("stored risk baseline gate tool changed")
    captures = {}
    for job in layout["jobs"]:
        if host.sha256_file(root / job["cases"]) != job["cases_sha256"]:
            raise quality.ScreenError("stored risk baseline prompt bytes changed")
        captures[job["id"]] = verified_cell(root, manifest, job, "A")
    actual = {job["id"]: host.sha256_file(root / job["id"] / "complete.json") for job in layout["jobs"]}
    if actual != artifact["capture_seals"]:
        raise quality.ScreenError("stored risk baseline capture seals changed")
    return artifact, captures


def load_samples(captures: Sequence[Path]) -> tuple[dict, dict, dict, dict]:
    responses, scores, outputs, tokens = {}, {}, {}, {}
    for directory in captures:
        for row in records(directory / "quality/responses.jsonl"):
            if row["case_id"] in responses:
                raise quality.ScreenError("duplicate sample across risk shards")
            responses[row["case_id"]] = row
        scores.update({row["case_id"]: row for row in host.load(directory / "quality/scores.json")["per_case"]})
        outputs.update({key: base64.b64decode(value, validate=True) for key, value in host.load(directory / "output-bytes.json").items()})
        tokens.update(host.load(directory / "token-ids.json"))
    return responses, scores, outputs, tokens


def first_difference(left: Sequence, right: Sequence) -> int | None:
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return index
    return min(len(left), len(right)) if len(left) != len(right) else None


def task_checks(cases: Path, responses: dict[str, dict], qualification: Path) -> dict[str, Any]:
    path = qualification / "scripts/_qual.py"
    spec = importlib.util.spec_from_file_location("risk_gate_qual", path)
    if spec is None or spec.loader is None:
        raise quality.ScreenError("private JSON-schema validator unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    by_id = {case_id: json.loads(line) for case_id, line, _ in quality.load_cases(cases)}
    failures, structured, tools = [], 0, 0
    for sample_id, row in responses.items():
        case = by_id[quality.base_id(sample_id)]
        errors = []
        if row.get("error"):
            errors.append("response-error")
        response_format = case.get("response_format")
        if response_format:
            structured += 1
            try:
                value = json.loads(row.get("content") or "")
                schema = (response_format.get("json_schema") or {}).get("schema", response_format.get("schema"))
                if schema is not None:
                    errors.extend(module.validate_schema_instance(schema, value))
                elif response_format.get("type") != "json_object" or not isinstance(value, dict):
                    errors.append("invalid structured-output contract")
            except (ValueError, TypeError):
                errors.append("invalid JSON output")
        declared = {tool["function"]["name"]: tool["function"] for tool in case.get("tools") or []}
        calls = row.get("tool_calls") or []
        if not isinstance(calls, list):
            errors.append("tool calls are not a list")
            calls = []
        expected = case.get("oracle", {}).get("expected_tool")
        if declared or expected is not None or calls:
            tools += 1
            first = calls[0] if calls and isinstance(calls[0], dict) else {}
            first_function = first.get("function", first)
            if expected is not None and (not isinstance(first_function, dict) or first_function.get("name") != expected):
                errors.append("required tool selection missing/wrong")
            for call in calls:
                if not isinstance(call, dict) or not isinstance(call.get("function", call), dict):
                    errors.append("malformed tool call")
                    continue
                function = call.get("function", call)
                name = function.get("name")
                try:
                    arguments = json.loads(function.get("arguments", ""))
                    if name not in declared or not isinstance(arguments, dict):
                        errors.append("undeclared tool or non-object arguments")
                    else:
                        errors.extend(module.validate_schema_instance(declared[name].get("parameters", {}), arguments))
                except (ValueError, TypeError):
                    errors.append("tool arguments do not parse as JSON")
        if errors:
            failures.append({"case_id": sample_id, "failures": errors})
    return {"checked_responses": len(responses), "json_schema_cases": structured, "tool_cases": tools,
            "failure_count": len(failures), "failures": failures}


def compare_role(baseline: tuple, candidate: tuple) -> dict[str, Any]:
    a_rows, _, a_bytes, a_tokens = baseline
    b_rows, _, b_bytes, b_tokens = candidate
    if set(a_rows) != set(b_rows) or len(a_rows) != ROLE_RULE["cases"]:
        raise quality.ScreenError("role gate requires complete matched 84-case arms")
    per_case = []
    for case_id in sorted(a_rows):
        per_case.append({"case_id": case_id, "bytes_identical": a_bytes[case_id] == b_bytes[case_id],
                         "first_divergent_byte_offset": first_difference(a_bytes[case_id], b_bytes[case_id]),
                         "first_divergent_token_index": first_difference(a_tokens[case_id], b_tokens[case_id]),
                         "baseline_tokens": len(a_tokens[case_id]), "candidate_tokens": len(b_tokens[case_id])})
    different = [row["case_id"] for row in per_case if not row["bytes_identical"]]
    errors = sorted(case for case in a_rows if a_rows[case].get("error") or b_rows[case].get("error"))
    return {"compared": len(per_case), "identical": len(per_case) - len(different), "differing_cases": different,
            "divergent_fraction": len(different) / len(per_case), "response_errors": errors, "per_case": per_case,
            "projection": "actual retained UTF-8 JSON [content, reasoning, tool_calls excluding IDs, finish_reason]; raw argument strings preserved",
            "token_basis": "actual server request_done.result.generated_token_ids, including reasoning/control tokens; zero-based"}


def math_decision(baseline: tuple, candidate: tuple, layout: dict[str, Any], tasks: dict[str, Any]) -> dict[str, Any]:
    a_rows, a_scores, a_bytes, _ = baseline
    b_rows, b_scores, b_bytes, _ = candidate
    ids = [sample for job in layout["jobs"] for sample in job["prompt_ids"] if sample in b_rows]
    if any(sample not in a_rows for sample in ids):
        raise quality.ScreenError("math candidate has no matched baseline")
    new_claims = [sample for sample in ids if b_scores[sample]["unsupported_claim"] and not a_scores[sample]["unsupported_claim"]]
    def leaks(score: dict[str, Any]) -> set[str]:
        values = score["secret_leaks"]
        if not isinstance(values, list):
            raise quality.ScreenError("targeted secret scoring requires the retained leak list")
        return {json.dumps(value, sort_keys=True) for value in values}
    new_secrets = [sample for sample in ids if leaks(b_scores[sample]) - leaks(a_scores[sample])]
    errors = [sample for sample in ids if a_rows[sample].get("error") or b_rows[sample].get("error")]
    identical = all(a_bytes[sample] == b_bytes[sample] for sample in ids)
    covered = {quality.base_id(sample) for sample in ids} == set(layout["selected_cases"])
    if errors:
        verdict, reason = "invalid", "response-errors"
    elif tasks["failure_count"] or new_secrets or len(new_claims) > MATH_RULE["max_new_unsupported"]:
        verdict, reason = "fail", "observed-regression"
    elif len(ids) >= MATH_RULE["early_identical_pairs"] and identical and covered:
        verdict, reason = "pass", "early-identical-covered-pairs"
    elif len(ids) == MATH_RULE["prompts"]:
        verdict, reason = "pass", "complete-targeted-risk-screen"
    else:
        verdict, reason = "continue", "more-targeted-pairs-required"
    return {"verdict": verdict, "reason": reason, "paired_prompts": len(ids),
            "all_retained_bytes_identical": bool(ids) and identical, "selected_cases_covered": covered,
            "introduced_unsupported_cases": new_claims, "new_secret_leak_cases": new_secrets,
            "response_errors": errors, "task_checks": tasks, "pass_rule": MATH_RULE}


def fp64_report(log: Path, binary: Path) -> dict[str, Any]:
    encoded = log.read_bytes()
    text = encoded.decode("utf-16" if encoded.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    names = {int(number): name for number, name in re.findall(r"Start\s+(\d+):\s+(\S+)", text)}
    commands = {int(number): Path(quoted or bare) for number, quoted, bare in re.findall(
        r'^\s*(\d+):\s+Test command:\s+(?:"([^"]+)"|(\S+))', text, re.MULTILINE)}
    binaries = {}
    for number, name in names.items():
        if name not in FP64_TESTS:
            continue
        path = commands.get(number)
        if path is None or path.stem != name or path.parent.resolve() != binary.parent.resolve():
            raise quality.ScreenError("FP64 test executable does not belong to the candidate's immutable binary set")
        binaries[name] = {"path": str(path.resolve()), "sha256": host.sha256_file(path)}
    rows = {name: [] for name in FP64_TESTS}
    for line in text.splitlines():
        match = re.search(r"^\s*(\d+):\s+OP_ERROR_STATS\s+(.+?)\s+case=(.*)$", line)
        if not match or names.get(int(match[1])) not in rows:
            continue
        fields = dict(part.split("=", 1) for part in match[2].split())
        if fields.pop("kind") != "reduction":
            continue
        values = {key: float(value) for key, value in fields.items()}
        values["case"] = match[3]
        rows[names[int(match[1])]].append(values)
    if any(not value for value in rows.values()):
        raise quality.ScreenError("FP64 log omits one of the four required op reduction-stat families")
    summaries = re.findall(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", text)
    passed = (summaries == [("100", "0", str(len(FP64_TESTS)))]
              and set(names.values()) == set(FP64_TESTS) and len(names) == len(FP64_TESTS))
    for group in rows.values():
        for row in group:
            numeric = [value for key, value in row.items() if key != "case"]
            if not all(math.isfinite(value) and value >= 0 for value in numeric) or row["count"] <= 0:
                passed = False
            if (row["non_finite"] or row["rel_l2"] > row["rel_l2_limit"] or row["max_abs"] > row["gross_limit"]
                    or row["rel_l2_ratio"] > 1 or row["gross_ratio"] > 1):
                passed = False
    version = host.command([str(binary), "--version"]).stdout.strip()
    return {"artifact_type": "omp-ninfer.fp64-kernel-proof", "schema_version": 1,
            "source_sha": source_sha(version), "server_binary_sha256": host.sha256_file(binary),
            "binary_version": version, "server_binary": str(binary.resolve()),
            "log": str(log.resolve()), "log_sha256": host.sha256_file(log),
            "operator_binaries": binaries, "kernels": rows, "passed": passed}


def verify_numerics(path: Path, identity: dict[str, Any]) -> dict[str, Any]:
    proof = host.load(path)
    if (proof.get("artifact_type") != "omp-ninfer.fp64-kernel-proof"
            or proof["source_sha"] != source_sha(identity["binary_version"])
            or proof["server_binary_sha256"] != identity["binary_sha256"]
            or host.sha256_file(Path(proof["log"])) != proof["log_sha256"]):
        raise quality.ScreenError("FP64 prerequisite does not identify this exact candidate/log")
    actual = fp64_report(Path(proof["log"]), Path(proof["server_binary"]))
    if actual != proof:
        raise quality.ScreenError("FP64 prerequisite bytes changed")
    return proof


def compare_ppl(off: dict, on: dict) -> dict[str, Any]:
    if (off.get("schema_version") != 2 or on.get("schema_version") != 2
            or off["execution"] != on["execution"] or off["corpus"] != on["corpus"]):
        raise quality.ScreenError("PPL arms changed schema/corpus/context/stride/KV configuration")
    execution = off["execution"]
    if (execution["context_tokens"] not in PPL_RULE["contexts"]
            or execution["stride_tokens"] != execution["context_tokens"] // 2
            or execution["kv_dtype"] != "int8" or execution["purpose"] != "causal_scoring"
            or off["metric"]["log_base"] != "natural" or on["metric"]["log_base"] != "natural"):
        raise quality.ScreenError("PPL evidence changed the frozen scoring method")
    a = {row["domain"]: row for row in off["domains"]}
    b = {row["domain"]: row for row in on["domains"]}
    if len(a) != len(off["domains"]) or len(b) != len(on["domains"]) or set(a) != set(b) or not a:
        raise quality.ScreenError("PPL arms changed/duplicated domains")
    for report in (off, on):
        if (sum(row["scored_tokens"] for row in report["domains"]) != report["overall"]["scored_tokens"]
                or not math.isclose(sum(row["total_nll"] for row in report["domains"]),
                                    report["overall"]["total_nll"], rel_tol=1e-8, abs_tol=1e-8)):
            raise quality.ScreenError("PPL domain totals do not match the overall score")
    comparisons = []
    for name, left, right in [("overall", off["overall"], on["overall"])] + [(name, a[name], b[name]) for name in sorted(a)]:
        if left["scored_tokens"] <= 0 or left["scored_tokens"] != right["scored_tokens"]:
            raise quality.ScreenError("PPL arms changed scored-token counts")
        for value in (left, right):
            if not all(math.isfinite(value[key]) for key in ("total_nll", "mean_nll", "perplexity")):
                raise quality.ScreenError("non-finite PPL evidence")
            if value["total_nll"] < 0 or value["mean_nll"] < 0:
                raise quality.ScreenError("negative causal NLL is not valid perplexity evidence")
            if not math.isclose(value["total_nll"] / value["scored_tokens"], value["mean_nll"], rel_tol=1e-8, abs_tol=1e-10):
                raise quality.ScreenError("PPL mean/count evidence inconsistent")
            if value["perplexity"] <= 0 or not math.isclose(math.log(value["perplexity"]), value["mean_nll"], rel_tol=1e-8, abs_tol=1e-10):
                raise quality.ScreenError("PPL exponent/log-base evidence inconsistent")
        delta = right["mean_nll"] - left["mean_nll"]
        limit = PPL_RULE["max_overall_delta_nll"] if name == "overall" else PPL_RULE["max_domain_delta_nll"]
        comparisons.append({"domain": name, "scored_tokens": left["scored_tokens"], "off_mean_nll": left["mean_nll"],
                            "on_mean_nll": right["mean_nll"], "delta_mean_nll": delta,
                            "perplexity_ratio": math.exp(delta), "limit": limit, "passed": delta <= limit})
    return {"context": off["execution"]["context_tokens"], "domains": comparisons,
            "passed": all(row["passed"] for row in comparisons)}


def run_ppl(plan_path: Path, out: Path) -> dict[str, Any]:
    started = time.monotonic()
    plan = host.load(plan_path)
    model_sha = host.sha256_file(Path(plan["model_path"]))
    if model_sha != plan["model_sha256"]:
        raise quality.ScreenError("PPL model identity changed")
    manifest_path = Path(plan["corpus_manifest"])
    provenance_path = manifest_path.parent / "provenance.json"
    if (host.sha256_file(manifest_path) != plan["corpus_manifest_sha256"]
            or host.sha256_file(provenance_path) != plan["corpus_provenance_sha256"]):
        raise quality.ScreenError("frozen held-out manifest/provenance changed")
    corpus = host.load(manifest_path)
    provenance = host.load(provenance_path)
    expected = {row["id"]: row["selected_sha256"] for row in provenance["streams"]}
    hashes = {}
    corpus_files = {str(path.resolve()): host.sha256_file(path) for path in (manifest_path, provenance_path)}
    for stream in corpus["streams"]:
        path = manifest_path.parent / stream["path"]
        hashes[stream["id"]] = host.sha256_file(path)
        corpus_files[str(path.resolve())] = hashes[stream["id"]]
        if hashes[stream["id"]] != expected[stream["id"]]:
            raise quality.ScreenError("frozen held-out corpus changed; do not regenerate it")
    out.mkdir(parents=True, exist_ok=False)
    candidate = Path(plan["candidate_server_binary"])
    version = host.command([str(candidate), "--version"]).stdout.strip()
    identity = {"plan_sha256": host.sha256_file(plan_path), "model_sha256": model_sha, "corpus_sha256": hashes,
                "corpus_files": corpus_files,
                "source_sha": source_sha(version), "candidate_binary_sha256": host.sha256_file(candidate),
                "gpu": host.gpu(plan["gpu_uuid"]), "runs": []}
    host.save(out / "identity.json", identity)
    before = identity["gpu"]["power_limit_w"]
    identity["power_limit_w"] = float(plan.get("power_limit_w", before))
    sampler = host.Sampler(plan["gpu_uuid"], out / "vram.jsonl", 0.5)
    reports = {}
    try:
        if "power_limit_w" in plan:
            host.set_power(plan["gpu_uuid"], float(plan["power_limit_w"]))
        with sampler:
            for context, policy in ((1024, "off"), (1024, "on"), (2048, "on"), (2048, "off")):
                arm = plan["arms"][policy]
                binary = Path(arm["binary"])
                sha = host.sha256_file(binary)
                if sha != arm["binary_sha256"]:
                    raise quality.ScreenError("PPL binary identity changed")
                directory = out / f"{context}-{policy}"
                argv = [str(binary), plan["model_path"], "--corpus", str(manifest_path), "--context", str(context),
                        "--stride", str(context // 2), "--device", "0", "--kv-dtype", "int8", "--output", str(directory)]
                env = dict(os.environ, CUDA_VISIBLE_DEVICES=plan["gpu_uuid"])
                env["PATH"] = os.pathsep.join([str(binary.parent), *plan.get("runtime_paths", []), env.get("PATH", "")])
                with (out / f"{context}-{policy}.log").open("wb") as log:
                    subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   env=env, check=True, timeout=min(1200, max(1, 3250 - (time.monotonic() - started))))
                report = directory / "report.json"
                reports[(context, policy)] = host.load(report)
                observed = reports[(context, policy)]
                if (observed["corpus"]["id"] != corpus["corpus_id"]
                        or Path(observed["corpus"]["source"]).resolve() != manifest_path.resolve()
                        or observed["corpus"]["stream_count"] != len(corpus["streams"])
                        or {row["id"] for row in observed["streams"]} != {row["id"] for row in corpus["streams"]}
                        or Path(observed["artifact"]["path"]).resolve() != Path(plan["model_path"]).resolve()
                        or observed["execution"]["context_tokens"] != context):
                    raise quality.ScreenError("PPL report does not identify the requested model/corpus/context")
                identity["runs"].append({"context": context, "policy": policy, "argv": argv,
                                          "binary_sha256": sha, "report": str(report.resolve()),
                                          "report_sha256": host.sha256_file(report)})
                host.save(out / "identity.json", identity)
    finally:
        host.set_power(plan["gpu_uuid"], before)
    comparisons = [compare_ppl(reports[(context, "off")], reports[(context, "on")]) for context in PPL_RULE["contexts"]]
    result = {"artifact_type": "omp-ninfer.heldout-ppl-gate", "schema_version": 1, "identity": identity,
              "pass_rule": PPL_RULE, "comparisons": comparisons, "verdict": "pass" if all(row["passed"] for row in comparisons) else "fail",
              "vram": sampler.summary(), "restored_power_limit_w": host.gpu(plan["gpu_uuid"])["power_limit_w"]}
    host.save(out / "result.json", result)
    return result


def verify_ppl(path: Path, identity: dict[str, Any]) -> dict[str, Any]:
    receipt = host.load(path)
    evidence = receipt["identity"]
    if (receipt.get("artifact_type") != "omp-ninfer.heldout-ppl-gate" or evidence["model_sha256"] != identity["model_sha256"]
            or evidence["candidate_binary_sha256"] != identity["binary_sha256"]
            or evidence["source_sha"] != source_sha(identity["binary_version"])
            or evidence["gpu"]["uuid"] != identity["gpu"]["uuid"]
            or evidence["gpu"]["driver"] != identity["gpu"]["driver"]
            or evidence["power_limit_w"] != identity["gpu"]["power_limit_w"]):
        raise quality.ScreenError("held-out PPL prerequisite does not identify this exact candidate/model/GPU")
    for name, sha in evidence["corpus_files"].items():
        if host.sha256_file(Path(name)) != sha:
            raise quality.ScreenError("held-out PPL input evidence changed")
    reports = {}
    for run in evidence["runs"]:
        if host.sha256_file(Path(run["report"])) != run["report_sha256"]:
            raise quality.ScreenError("held-out PPL evidence changed")
        reports[(run["context"], run["policy"])] = host.load(Path(run["report"]))
    actual = [compare_ppl(reports[(context, "off")], reports[(context, "on")]) for context in PPL_RULE["contexts"]]
    if receipt["comparisons"] != actual or receipt["pass_rule"] != PPL_RULE:
        raise quality.ScreenError("held-out PPL reduction/pass rule changed")
    expected_verdict = "pass" if all(row["passed"] for row in actual) else "fail"
    if receipt["verdict"] != expected_verdict:
        raise quality.ScreenError("held-out PPL verdict inconsistent")
    return receipt


def prerequisite_failure(out: Path, result: dict[str, Any], fingerprint: dict[str, Any]) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=False)
    result["identity"] = fingerprint
    host.save(out / "result.json", result)
    return result


def run_gate(command: str, lane: str, plan_path: Path, out: Path, *, kind: str = "role", baseline: Path | None = None,
             shard_size: int | None = None, max_shards: int = 1, resume: bool = False,
             numerics: Path | None = None, ppl: Path | None = None) -> dict[str, Any]:
    if command == "t3":
        kind = "math"
    if max_shards < 1:
        raise quality.ScreenError("max shards must be positive")
    size = shard_size if shard_size is not None else (84 if kind == "role" else 50)
    plan = host.load(plan_path)
    host.validate_plan(plan, lane)
    layout, files = sample_plan(Path(plan["cases"]), kind, size)
    fingerprint = quality.pair_fingerprint(host, lane, plan_path, plan)
    if fingerprint["arms"]["A"]["gpu"] != fingerprint["arms"]["B"]["gpu"]:
        raise quality.ScreenError("risk arms must use the same GPU/driver/power")
    if kind == "role" and fingerprint["arms"]["A"]["config_sha256"] != fingerprint["arms"]["B"]["config_sha256"]:
        raise quality.ScreenError("T1/T2 role arms must use exactly the same profile")
    prerequisite = {}
    if command == "t2":
        if numerics is None:
            raise quality.ScreenError("T2 requires the candidate's bound FP64 numerical proof")
        prerequisite["numerics"] = verify_numerics(numerics, fingerprint["arms"]["B"])
        if not prerequisite["numerics"]["passed"]:
            return prerequisite_failure(out, {"tier": 2, "verdict": "fail", "reason": "FP64 numerical prerequisite", **prerequisite}, fingerprint)
        if not plan.get("retrieval_fixture"):
            raise quality.ScreenError("T2 requires the exact long retrieval fixture")
    if command == "t3" or (command == "cache" and kind == "math"):
        if ppl is None:
            raise quality.ScreenError("T3 requires the held-out perplexity gate before any screen")
        prerequisite["ppl"] = verify_ppl(ppl, fingerprint["arms"]["B"])
        if prerequisite["ppl"]["verdict"] != "pass":
            return prerequisite_failure(out, {"tier": 3, "verdict": "fail", "reason": "held-out PPL worsens; math route stays OFF", **prerequisite}, fingerprint)
    cache, base_captures = None, {}
    if command != "cache":
        if baseline is None:
            raise quality.ScreenError("risk candidate requires its lane's complete stored baseline")
        cache, base_captures = verify_cache(baseline, layout, fingerprint)
    manifest = {"artifact_type": "omp-ninfer.risk-capture-plan", "schema_version": 1, "command": command,
                "layout": layout, "identity": fingerprint, "gate_tool_sha256": host.sha256_file(Path(__file__)),
                "rule": MATH_RULE if kind == "math" else ROLE_RULE, "prerequisites": prerequisite}
    if command == "t2":
        manifest["retrieval_fixture_sha256"] = host.sha256_file(Path(plan["retrieval_fixture"]))
    if cache is not None:
        manifest["baseline"] = {"path": str(baseline.resolve()), "sha256": host.digest(cache)}
    out = out.resolve()
    manifest_path = out / "campaign.json"
    if manifest_path.exists():
        if not resume or host.load(manifest_path) != manifest:
            raise quality.ScreenError("risk campaign requires --resume with identical plan/tools/prerequisites/baseline")
    else:
        out.mkdir(parents=True, exist_ok=True)
        if any(out.iterdir()):
            raise quality.ScreenError("new risk campaign requires an empty output root")
        (out / "prompts").mkdir()
        for name, data in files.items():
            (out / name).write_bytes(data)
        host.save(manifest_path, manifest)
    for name, data in files.items():
        if (out / name).read_bytes() != data:
            raise quality.ScreenError("risk prompt bytes changed")
    key = out / "api-key"
    if not key.exists():
        key.write_text(secrets.token_hex(32) + "\n")
        key.chmod(0o600)
    arm, index = ("A", 0) if command == "cache" else ("B", 1)
    captures, pending = {}, []
    missing = False
    for job in layout["jobs"]:
        if (out / job["id"] / "complete.json").exists():
            if missing:
                raise quality.ScreenError("risk captures are not a contiguous completed prefix")
            captures[job["id"]] = verified_cell(out, manifest, job, arm)
        else:
            missing = True
            pending.append(job)
    result: dict[str, Any] = {"tier": command, "completed_shards": len(captures), "total_shards": len(layout["jobs"])}
    result["scope"] = "quality evidence only; build provenance and performance admission remain separate"
    if command == "t3" and captures:
        selected = load_samples(list(captures.values()))
        decision = math_decision(load_samples(list(base_captures.values())), selected, layout,
                                 task_checks(Path(plan["cases"]), selected[0], Path(plan["qualification"])))
        if decision["verdict"] != "continue":
            result.update(decision)
    for job in ([] if "verdict" in result else pending[:max_shards]):
        directory = out / job["id"]
        directory.mkdir(exist_ok=True)
        attempts = sorted(directory.glob("attempt-*"))
        if any((attempt / "receipt.json").exists() for attempt in attempts):
            raise quality.ScreenError("unsealed finished/failed risk capture; preserve it and use a new root")
        capture = directory / f"attempt-{len(attempts):04d}"
        host.capture_arm(lane, plan, fingerprint["arms"][arm]["model_sha256"], key, index, capture, "quality",
                         quality_cases=out / job["cases"])
        evidence = capture_evidence(capture, job, fingerprint["arms"][arm], fingerprint["capture_contract"])
        host.save(directory / "complete.tmp", {"manifest_sha256": host.digest(manifest), "job": job,
                                               "capture": capture.name, "evidence": evidence})
        (directory / "complete.tmp").replace(directory / "complete.json")
        captures[job["id"]] = capture
        if command == "t3":
            selected = load_samples(list(captures.values()))
            tasks = task_checks(Path(plan["cases"]), selected[0], Path(plan["qualification"]))
            decision = math_decision(load_samples(list(base_captures.values())), selected, layout, tasks)
            (out / "looks").mkdir(exist_ok=True)
            quality.frozen_file(out / "looks" / f"{decision['paired_prompts']:04d}.json",
                                (json.dumps(decision, indent=2) + "\n").encode())
            if decision["verdict"] != "continue":
                result.update(decision)
                break
    result["completed_shards"] = len(captures)
    if command == "cache":
        if len(captures) != len(layout["jobs"]):
            return dict(result, status="shard-complete")
        if any(row.get("error") for row in load_samples(list(captures.values()))[0].values()):
            raise quality.ScreenError("errored baseline cannot become a reusable risk cache")
        artifact = {"artifact_type": "omp-ninfer.risk-baseline", "schema_version": 1,
                    "manifest_sha256": host.digest(manifest),
                    "capture_seals": {job["id"]: host.sha256_file(out / job["id"] / "complete.json") for job in layout["jobs"]}}
        quality.frozen_file(out / "baseline.json", (json.dumps(artifact, indent=2) + "\n").encode())
        return dict(result, status="baseline-complete", baseline=str(out))
    if command == "t3":
        if "verdict" not in result:
            selected = load_samples(list(captures.values()))
            result.update(math_decision(load_samples(list(base_captures.values())), selected, layout,
                                        task_checks(Path(plan["cases"]), selected[0], Path(plan["qualification"]))))
        if result["verdict"] == "continue":
            return result
    elif len(captures) == len(layout["jobs"]):
        selected = load_samples(list(captures.values()))
        comparison = compare_role(load_samples(list(base_captures.values())), selected)
        result["byte_comparison"] = comparison
        if command == "t1":
            result["verdict"] = "invalid" if comparison["response_errors"] else "pass" if not comparison["differing_cases"] else "fail"
            result["pass_rule"] = "84/84 actual retained output bytes identical, no response errors"
        else:
            tasks = task_checks(Path(plan["cases"]), selected[0], Path(plan["qualification"]))
            result["task_checks"] = tasks
            retrieval_dir = out / "retrieval"
            if not (retrieval_dir / "receipt.json").exists():
                if len(pending[:max_shards]) >= max_shards:
                    return dict(result, status="role-complete-awaiting-retrieval")
                host.capture_arm(lane, plan, fingerprint["arms"]["B"]["model_sha256"], key, 1, retrieval_dir, "retrieval")
            retrieval = host.load(retrieval_dir / "receipt.json")
            if retrieval["status"] != "passed" or quality.runtime_identity(retrieval["identity"]) != fingerprint["arms"]["B"]:
                raise quality.ScreenError("T2 retrieval identity/failure changed")
            request = retrieval["requests"][0]
            encoded = (retrieval_dir / request["output_file"]).read_bytes()
            exact_bytes = json.dumps([ROLE_RULE["retrieval_answer"], "", []], ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":")).encode("utf-8")
            if hashlib.sha256(encoded).hexdigest() != request["output_sha256"] or encoded != exact_bytes:
                raise quality.ScreenError("T2 retained retrieval bytes are not the exact expected answer")
            retrieval_seal = {"receipt_sha256": host.sha256_file(retrieval_dir / "receipt.json"),
                              "output_sha256": request["output_sha256"],
                              "fixture_sha256": manifest["retrieval_fixture_sha256"]}
            quality.frozen_file(out / "retrieval-complete.json", (json.dumps(retrieval_seal, indent=2) + "\n").encode())
            result["retrieval"] = {"prompt_tokens": request["prompt_tokens"], "exact": request["exact"],
                                   "output_sha256": request["output_sha256"]}
            result["numerics"] = prerequisite["numerics"]
            result["pass_rule"] = ROLE_RULE
            result["verdict"] = "invalid" if comparison["response_errors"] else "pass" if (
                comparison["divergent_fraction"] <= ROLE_RULE["max_divergent_fraction"] and not tasks["failure_count"]
                and request["exact"] and request["prompt_tokens"] == ROLE_RULE["retrieval_prompt_tokens"]) else "fail"
    else:
        return dict(result, status="shard-complete")
    result["timing"] = [{"shard": job, "prompts": len(records(directory / "quality/responses.jsonl")),
                          "wall_seconds": host.load(directory / "receipt.json")["wall_seconds"]} for job, directory in captures.items()]
    result["manifest_sha256"] = host.digest(manifest)
    host.save(out / "result.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("cache", "t1", "t2", "t3"):
        command = commands.add_parser(name)
        command.add_argument("--lane", choices=host.LANES, required=True)
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--shard-size", type=int)
        command.add_argument("--max-shards", type=int, default=1)
        command.add_argument("--resume", action="store_true")
        if name == "cache":
            command.add_argument("--kind", choices=("role", "math"), required=True)
            command.add_argument("--ppl", type=Path, help="mandatory before a math baseline is captured")
        else:
            command.add_argument("--baseline", type=Path, required=True)
        if name == "t2":
            command.add_argument("--numerics", type=Path, required=True)
        if name == "t3":
            command.add_argument("--ppl", type=Path, required=True)
    fp64 = commands.add_parser("fp64")
    fp64.add_argument("--log", type=Path, required=True)
    fp64.add_argument("--server-binary", type=Path, required=True)
    fp64.add_argument("--out", type=Path, required=True)
    ppl = commands.add_parser("ppl")
    ppl.add_argument("--plan", type=Path, required=True)
    ppl.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "fp64":
            result = fp64_report(args.log, args.server_binary)
            host.save(args.out, result)
        elif args.command == "ppl":
            result = run_ppl(args.plan, args.out)
        else:
            result = run_gate(args.command, args.lane, args.plan, args.out, kind=getattr(args, "kind", "role"),
                              baseline=getattr(args, "baseline", None), shard_size=args.shard_size,
                              max_shards=args.max_shards, resume=args.resume, numerics=getattr(args, "numerics", None),
                              ppl=getattr(args, "ppl", None))
    except (quality.ScreenError, host.CampaignError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"quality_gates: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return {"pass": 0, "fail": 1, "invalid": 2}.get(result.get("verdict"), 0 if result.get("passed", True) else 1)


if __name__ == "__main__":
    raise SystemExit(main())
