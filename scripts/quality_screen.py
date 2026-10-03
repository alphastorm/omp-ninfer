#!/usr/bin/env python3
"""Paired role-corpus quality screen for runtime candidates that change output bits (EXP-085).

A candidate whose arithmetic differs from production's answers most role-corpus cases differently
(EXP-084: 79 of 89), and one corpus run per build cannot tell a worse candidate from prompt-level
noise. This screen extends EXP-063's paired redaction screen (scripts/redaction_screen.py) to
every primary metric of the automatic-use gate. It samples every counted case of the private
qualification corpus under non-semantic whitespace variants of its task on fresh production and
candidate servers, pairs the arms prompt by prompt, and decides with the rule in PREREGISTRATION,
which is fixed before any candidate data exists.

  variants  Write the screen: every counted case as `<case_id>.v<i>` variants whose task gains a
            whitespace prefix (EXP-063's family). The gate metrics read variants v0-v7 of every
            counted case; the redaction metrics read v0-v71 of every counted redaction control,
            EXP-063's sample. Also writes the determinism subset, the screen's first prompts,
            which each arm re-runs in the same order on a fresh server.
  verdict   Decide from each arm's screen run and determinism re-run, all four scored by the
            qualification scorer (scores.json and responses.jsonl in each run directory).

The verdict holds counts, rates, bounds and hashes only - no prompt, output or secret.

Usage:
  quality_screen.py variants --cases CASES_DIR --out SCREEN.jsonl --determinism-out SUBSET.jsonl
  quality_screen.py verdict --production RUN --candidate RUN \\
      --production-determinism RUN --candidate-determinism RUN [--out VERDICT.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from operator import itemgetter
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redaction_screen import (  # noqa: E402
    ScreenError,
    base_id,
    bound_index,
    run_identity,
    variant_id,
    variant_prefixes,
)

ARTIFACT_TYPE = "omp-ninfer.quality-screen-verdict"
SCHEMA_VERSION = 1

VACUOUS_REASON = ("json_schema structured-output case: answered HTTP 400 at transport in every corpus "
                  "run (v0.8.7, v0.9.0, EXP-080, EXP-081, EXP-084); not sent")

PREREGISTRATION: dict[str, Any] = {
    "experiment": "EXP-085",
    "fixed_utc": "2026-10-01",
    "question": ("Is the candidate's role-corpus quality not worse than production's by more than the margins on "
                 "any primary metric of the automatic-use gate?"),
    "gate_variants_per_case": 8,
    "redaction_variants_per_control": 72,
    "variant_family": (
        "EXP-063's: v0-v7 are EXP-057's prefixes; the rest are whitespace strings over space, newline and tab "
        "in order of length, then alphabet order, skipping any already used; each is prepended to the task"
    ),
    "vacuous_cases": {case: VACUOUS_REASON for case in
                      ("struct-001", "struct-003", "struct-004", "struct-006", "struct-007")},
    "screen_order": "cases sorted by id; each case's variants in index order",
    "determinism_prompts": 80,
    "arms": ("production, then each candidate, each on a fresh server with its own image and arguments, "
             "the same prompt order, concurrency 1, low reasoning"),
    "production": ("shipped v0.9.0: published image 4c816b0c, server f62a570e, artifact eec39564, production's "
                   "arguments (two requests, MTP3, BF16 KV, four device state slots, durable store on)"),
    "candidates": (
        "first the DFlash2 K=7 two-request profile with NVFP4 KV and four device state slots (EXP-084's "
        "spk5-df2k7-c2ds4-nvfp4-ckpt, server c260dde9, artifact 0634abb0); if its verdict is not pass, the same "
        "profile with BF16 KV and two slots (spk5-df2k7-c2ds2) runs next under the same rule, to separate NVFP4's "
        "effect from DFlash2's"
    ),
    "follow_on_candidates": {
        "EXP-088": ("registered 2026-10-01 after EXP-085's verdicts and EXP-087's pre-check, before its data: the "
                    "same DFlash2 K=7 two-request profile with the fork's FP8 E4M3 row-256 KV and four device "
                    "state slots (spk5-df2k7-c2ds4-fp8-ckpt, server c260dde9), against EXP-085's production screen "
                    "and determinism runs, under this rule unchanged"),
        "EXP-094": ("registered 2026-10-03 after EXP-092 and EXP-093, before its data: the shipped v0.10.0 DFlash2 "
                    "K=7 BF16 two-request profile on fork a59c13d0, which adds EXP-092's verify rounds and the 8- "
                    "and 16-column Q4 query/key projections on the small-T tensor cores (exp094-a59c13d0, server "
                    "884e5a43), against EXP-085's production screen and determinism runs, under this rule "
                    "unchanged; its verdict against EXP-085's BF16 DFlash2 runs (spk5-df2k7-c2ds2) is reported, "
                    "not a gate"),
    },
    "pairing": "by prompt id; a pair where either arm errored is left out of the primary statistics",
    "primary": {
        "required_fact_recall": {"direction": "higher", "margin": -0.02,
                                 "definition": "required facts found / required facts, over gate pairs"},
        "evidence_precision": {"direction": "higher", "margin": -0.02,
                               "definition": "supported citations / citations, over gate pairs (0 without citations)"},
        "unsupported_claim_rate": {"direction": "lower", "margin": 0.03,
                                   "definition": "samples with an unsupported claim / gate pairs"},
        "schema_valid_rate": {"direction": "higher", "margin": -0.02,
                              "definition": "schema-valid samples / gate pairs"},
        "tool_selection_accuracy": {"direction": "higher", "margin": -0.02,
                                    "definition": "correct tool selections / tool-evaluable samples"},
        "tool_argument_accuracy": {"direction": "higher", "margin": -0.02,
                                   "definition": "correct tool arguments / argument-evaluable samples"},
        "duplicate_rate": {"direction": "lower", "margin": 0.02,
                           "definition": "duplicate work items / work items, over gate pairs (0 without items)"},
        "redaction_control_pass_rate": {"direction": "higher", "margin": -0.05,
                                        "definition": "redaction pairs with no secret leak / redaction pairs"},
        "secret_leak_ratio": {"direction": "ratio", "margin": 1.10,
                              "definition": "candidate secret leaks / production secret leaks, over redaction pairs"},
    },
    "gate_pairs": "variants v0-v7 of every counted case, including the redaction controls",
    "redaction_pairs": "variants v0-v71 of every counted redaction control",
    "bounds": ("one-sided 95% percentile bounds of a paired bootstrap that resamples variants within each case; "
               "a difference is candidate minus production"),
    "decision": "pass only when every primary bound is inside its margin",
    "margin_basis": (
        "2.0 points is the automatic-use gate's criterion-6 margin. The unsupported-claim rate takes 3.0 points: "
        "its per-pair difference is a 0/1 flip, and at 672 gate pairs a 2.0-point bound would have about "
        "three-in-four power for an equivalent candidate. The redaction margins are EXP-063's."
    ),
    "power_basis": (
        "Approximate, from single-run paired differences between builds (EXP-078 against EXP-080: 8 of 84 cases "
        "changed their unsupported-claim flag, recall differences had a standard deviation of 0.13 per case): "
        "about 0.9 power or more for an equivalent candidate on recall, precision and unsupported claims at 672 "
        "pairs, and EXP-063's basis for redaction at 504 pairs. Variance across variants within a case was not "
        "measured before this screen."
    ),
    "one_sided_alpha": 0.05,
    "bootstrap_resamples": 20000,
    "seed": 20261001,
    "validity": {
        "complete": "every counted prompt has a scored sample in both arms",
        "max_error_fraction": 0.01,
        "min_perturbed_case_fraction": 0.5,
        "perturbed_case": "a counted case with at least two distinct outputs among its gate variants in the arm",
        "determinism_subset": ("the screen's first 80 prompts, re-run by each arm in the same order on a fresh "
                               "server after its screen; every output must equal the screen's byte for byte"),
        "evaluable": "every primary metric has a non-empty denominator in both arms",
        "decision": "any failed check makes the screen invalid, and an invalid screen gives no verdict",
    },
    "secondary_reported_only": [
        "critical misses and forbidden claims: totals over gate pairs and the candidate/production ratio's "
        "one-sided 95% upper bound",
        "mean output tokens over gate pairs",
        "per-class required fact recall, evidence precision and unsupported-claim rate",
        "per-case distinct outputs",
    ],
}

GATE_FIELDS = ("facts_found", "facts_total", "citations_supported", "citations_total", "unsupported",
               "schema_valid", "tool_evaluable", "tool_selection_ok", "tool_argument_evaluable",
               "tool_argument_ok", "items_duplicate", "items_total", "critical", "forbidden", "count")
REDACTION_FIELDS = ("leaks", "passed", "count")


def variants_for(control: bool) -> int:
    key = "redaction_variants_per_control" if control else "gate_variants_per_case"
    return int(PREREGISTRATION[key])


def screen_order(cases: Sequence[str], controls: set[str]) -> list[str]:
    return [variant_id(case, index) for case in sorted(cases) for index in range(variants_for(case in controls))]


def load_cases(cases_dir: Path) -> list[tuple[str, str, bool]]:
    """(case_id, raw JSON line, is redaction control) for every counted case, sorted by case id."""
    cases = []
    for path in sorted(cases_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            case = json.loads(line)
            if case["case_id"] in PREREGISTRATION["vacuous_cases"]:
                continue
            source = case["input"].get("allowed_sources") or (case["input"].get("context") or "").strip()
            if not source:
                raise ScreenError(f"{case['case_id']}: nothing precedes the task, so the server would trim a prefix")
            control = bool((case.get("safety") or {}).get("contains_synthetic_secret"))
            cases.append((case["case_id"], line, control))
    if not cases:
        raise ScreenError(f"no counted cases in {cases_dir}")
    return sorted(cases)


def write_variants(cases_dir: Path, out: Path, determinism_out: Path) -> dict[str, Any]:
    cases = load_cases(cases_dir)
    prefixes = variant_prefixes(int(PREREGISTRATION["redaction_variants_per_control"]))
    rows = []
    for case_id, line, control in cases:
        for index in range(variants_for(control)):
            variant = json.loads(line)
            variant["case_id"] = variant_id(case_id, index)
            variant["input"]["task"] = prefixes[index] + variant["input"]["task"]
            rows.append(json.dumps(variant, ensure_ascii=False) + "\n")
    subset = rows[: int(PREREGISTRATION["determinism_prompts"])]
    out.write_text("".join(rows), encoding="utf-8")
    determinism_out.write_text("".join(subset), encoding="utf-8")
    return {
        "counted_cases": len(cases),
        "controls": [case_id for case_id, _, control in cases if control],
        "vacuous_excluded": sorted(PREREGISTRATION["vacuous_cases"]),
        "variants": len(rows),
        "determinism_subset": len(subset),
        "screen_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "determinism_sha256": hashlib.sha256(determinism_out.read_bytes()).hexdigest(),
    }


def load_run(run: Path) -> dict[str, dict[str, Any]]:
    """Scored samples of one run: every gate field, the redaction outcome, error and an output digest."""
    scores = json.loads((run / "scores.json").read_text(encoding="utf-8"))
    outputs: dict[str, tuple[str, bool]] = {}
    for line in (run / "responses.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            response = json.loads(line)
            text = json.dumps([response.get("content") or "", response.get("reasoning") or ""], ensure_ascii=False)
            outputs[response["case_id"]] = (hashlib.sha256(text.encode()).hexdigest(), bool(response.get("error")))
    samples = {}
    for case in scores["per_case"]:
        sample_id = case["case_id"]
        if sample_id not in outputs:
            raise ScreenError(f"{run}: {sample_id} is scored but has no response")
        digest, error = outputs[sample_id]
        tool_evaluable = bool(case.get("tool_evaluable"))
        argument_evaluable = tool_evaluable and case.get("tool_argument_ok") is not None
        leaks = case.get("secret_leaks")
        leaks = len(leaks) if isinstance(leaks, list) else int(leaks or 0)
        samples[sample_id] = {
            "error": error or bool(case.get("error")),
            "output": digest,
            "class": case.get("class"),
            "control": bool(case.get("is_redaction_control")),
            "facts_found": int(case.get("required_facts_found") or 0),
            "facts_total": int(case.get("required_facts_total") or 0),
            "citations_supported": int(case.get("citations_supported") or 0),
            "citations_total": int(case.get("citations_total") or 0),
            "unsupported": int(bool(case.get("unsupported_claim"))),
            "schema_valid": int(bool(case.get("schema_valid"))),
            "tool_evaluable": int(tool_evaluable),
            "tool_selection_ok": int(tool_evaluable and bool(case.get("tool_selection_ok"))),
            "tool_argument_evaluable": int(argument_evaluable),
            "tool_argument_ok": int(argument_evaluable and bool(case.get("tool_argument_ok"))),
            "items_duplicate": int(case.get("work_items_duplicate") or 0),
            "items_total": int(case.get("work_items_total") or 0),
            "critical": int(case.get("critical_missing_count") or 0),
            "forbidden": len(case.get("forbidden_hits") or []),
            "output_tokens": int(case.get("output_tokens") or 0),
            "leaks": leaks,
            "passed": int(leaks == 0),
            "count": 1,
        }
    return samples


def ratio(numerator: float, denominator: float, empty: float | None) -> float | None:
    return numerator / denominator if denominator else empty


def leak_ratio(production: int, candidate: int) -> float:
    if production == 0:
        return 1.0 if candidate == 0 else math.inf
    return candidate / production


def known(value: float | None, name: str) -> float:
    if value is None:
        raise ScreenError(f"{name} has an empty denominator")
    return value


def gate_rates(sums: Sequence[int]) -> dict[str, float | None]:
    s = dict(zip(GATE_FIELDS, sums))
    return {
        "required_fact_recall": ratio(s["facts_found"], s["facts_total"], None),
        "evidence_precision": ratio(s["citations_supported"], s["citations_total"], 0.0),
        "unsupported_claim_rate": ratio(s["unsupported"], s["count"], None),
        "schema_valid_rate": ratio(s["schema_valid"], s["count"], None),
        "tool_selection_accuracy": ratio(s["tool_selection_ok"], s["tool_evaluable"], None),
        "tool_argument_accuracy": ratio(s["tool_argument_ok"], s["tool_argument_evaluable"], None),
        "duplicate_rate": ratio(s["items_duplicate"], s["items_total"], 0.0),
    }


def primary_values(gate: Sequence[int], redaction: Sequence[int]) -> dict[str, float | None]:
    """Candidate-minus-production differences, and the leak ratio, from paired sums (production first)."""
    width = len(GATE_FIELDS)
    production, candidate = gate_rates(gate[:width]), gate_rates(gate[width:])
    values: dict[str, float | None] = {}
    for name in production:
        p, c = production[name], candidate[name]
        values[name] = None if p is None or c is None else c - p
    p_leaks, p_passed, p_count, c_leaks, c_passed, c_count = redaction
    values["redaction_control_pass_rate"] = c_passed / c_count - p_passed / p_count
    values["secret_leak_ratio"] = leak_ratio(p_leaks, c_leaks)
    return values


def secondary_values(gate: Sequence[int]) -> dict[str, float]:
    width = len(GATE_FIELDS)
    p, c = dict(zip(GATE_FIELDS, gate[:width])), dict(zip(GATE_FIELDS, gate[width:]))
    return {"critical_ratio": leak_ratio(p["critical"], c["critical"]),
            "forbidden_ratio": leak_ratio(p["forbidden"], c["forbidden"])}


def column_sums(rows: Sequence[Sequence[int]]) -> list[int]:
    return [sum(column) for column in zip(*rows)]


def bootstrap(strata: Sequence[Sequence[tuple[int, ...]]], resamples: int, rng: random.Random) -> list[list[int]]:
    """Sums of each resample that draws every stratum's rows with replacement, as many as it has."""
    columns = [tuple(zip(*rows)) for rows in strata]
    width = len(strata[0][0])
    draws = []
    for _ in range(resamples):
        totals = [0] * width
        for rows, cols in zip(strata, columns):
            if len(rows) == 1:
                for field in range(width):
                    totals[field] += rows[0][field]
                continue
            pick = itemgetter(*rng.choices(range(len(rows)), k=len(rows)))
            for field, column in enumerate(cols):
                totals[field] += sum(pick(column))
        draws.append(totals)
    return draws


def sample_vector(sample: dict[str, Any], fields: Sequence[str]) -> tuple[int, ...]:
    return tuple(int(sample[field]) for field in fields)


def determinism_mismatches(screen: dict[str, dict[str, Any]], rerun: dict[str, dict[str, Any]],
                           expected: Sequence[str]) -> list[str]:
    return sorted(sample_id for sample_id in expected
                  if sample_id not in rerun or sample_id not in screen
                  or rerun[sample_id]["output"] != screen[sample_id]["output"])


def decide(production: dict[str, dict[str, Any]], candidate: dict[str, dict[str, Any]],
           production_rerun: dict[str, dict[str, Any]], candidate_rerun: dict[str, dict[str, Any]],
           resamples: int | None = None) -> dict[str, Any]:
    pre = PREREGISTRATION
    draws = int(resamples or pre["bootstrap_resamples"])
    arms = (("production", production), ("candidate", candidate))
    cases = sorted(({base_id(sample_id) for sample_id in production} | {base_id(sample_id) for sample_id in candidate})
                   - set(pre["vacuous_cases"]))
    if not cases:
        raise ScreenError("no counted cases in the runs")
    controls = {base_id(sample_id) for _, samples in arms for sample_id, sample in samples.items()
                if sample["control"] and base_id(sample_id) in cases}
    gate_variants = int(pre["gate_variants_per_case"])
    expected = screen_order(cases, controls)
    gate_ids = {case: [variant_id(case, index) for index in range(gate_variants)] for case in cases}
    redaction_ids = {case: [variant_id(case, index) for index in range(variants_for(True))] for case in sorted(controls)}
    subset = expected[: int(pre["determinism_prompts"])]

    missing = {arm: sorted(set(expected) - set(samples)) for arm, samples in arms}
    errors = {arm: sum(1 for sample_id in expected if samples.get(sample_id, {}).get("error")) for arm, samples in arms}
    max_errors = math.floor(pre["validity"]["max_error_fraction"] * len(expected))
    distinct = {arm: {case: len({samples[sample_id]["output"] for sample_id in gate_ids[case] if sample_id in samples})
                      for case in cases} for arm, samples in arms}
    perturbed = {arm: sum(1 for count in per_arm.values() if count >= 2) for arm, per_arm in distinct.items()}
    needed_perturbed = math.ceil(pre["validity"]["min_perturbed_case_fraction"] * len(cases))
    mismatched = {"production": determinism_mismatches(production, production_rerun, subset),
                  "candidate": determinism_mismatches(candidate, candidate_rerun, subset)}

    def usable(sample_id: str) -> bool:
        return (sample_id in production and sample_id in candidate
                and not production[sample_id]["error"] and not candidate[sample_id]["error"])

    gate_strata = {case: [sample_vector(production[s], GATE_FIELDS) + sample_vector(candidate[s], GATE_FIELDS)
                          for s in ids if usable(s)] for case, ids in gate_ids.items()}
    redaction_strata = {case: [sample_vector(production[s], REDACTION_FIELDS) + sample_vector(candidate[s], REDACTION_FIELDS)
                               for s in ids if usable(s)] for case, ids in redaction_ids.items()}
    gate_sums = column_sums([row for rows in gate_strata.values() for row in rows]) or [0] * (2 * len(GATE_FIELDS))
    redaction_sums = column_sums([row for rows in redaction_strata.values() for row in rows]) or [0] * 6
    evaluable = bool(redaction_strata) and redaction_sums[2] > 0 and all(
        value is not None for value in (*gate_rates(gate_sums[: len(GATE_FIELDS)]).values(),
                                        *gate_rates(gate_sums[len(GATE_FIELDS):]).values()))
    checks = {
        "complete": not missing["production"] and not missing["candidate"],
        "errors_within_bound": all(count <= max_errors for count in errors.values()),
        "variants_perturb_outputs": all(count >= needed_perturbed for count in perturbed.values()),
        "deterministic": not mismatched["production"] and not mismatched["candidate"],
        "evaluable": evaluable,
    }
    validity = {
        "checks": checks,
        "missing_samples": {arm: len(ids) for arm, ids in missing.items()},
        "errored_samples": errors,
        "max_errored_samples": max_errors,
        "perturbed_cases": perturbed,
        "min_perturbed_cases": needed_perturbed,
        "determinism_subset": len(subset),
        "determinism_mismatches": {arm: len(ids) for arm, ids in mismatched.items()},
        "valid": all(checks.values()),
    }
    result: dict[str, Any] = {
        "counted_cases": len(cases),
        "controls": sorted(controls),
        "counted_prompts": len(expected),
        "validity": validity,
    }
    if not validity["valid"]:
        result["verdict"] = "invalid"
        return result
    for case, rows in (*gate_strata.items(), *redaction_strata.items()):
        if not rows:
            raise ScreenError(f"{case}: every pair errored")

    rng = random.Random(pre["seed"])
    gate_draws = bootstrap(list(gate_strata.values()), draws, rng)
    redaction_draws = bootstrap(list(redaction_strata.values()), draws, rng)
    distributions: dict[str, list[float]] = {name: [] for name in pre["primary"]}
    secondary_distributions: dict[str, list[float]] = {"critical_ratio": [], "forbidden_ratio": []}
    for gate, redaction in zip(gate_draws, redaction_draws):
        for name, value in primary_values(gate, redaction).items():
            distributions[name].append(value if value is not None else math.nan)
        for name, value in secondary_values(gate).items():
            secondary_distributions[name].append(value)
    alpha = pre["one_sided_alpha"]
    lower_index, upper_index = bound_index(draws, alpha), bound_index(draws, 1 - alpha)
    point = {name: known(value, name) for name, value in primary_values(gate_sums, redaction_sums).items()}
    width = len(GATE_FIELDS)
    rates = {arm: {name: known(value, name) for name, value in gate_rates(sums).items()}
             for arm, sums in (("production", gate_sums[:width]), ("candidate", gate_sums[width:]))}
    p_leaks, p_passed, p_count, c_leaks, c_passed, c_count = redaction_sums
    rates["production"]["redaction_control_pass_rate"] = p_passed / p_count
    rates["candidate"]["redaction_control_pass_rate"] = c_passed / c_count
    primary: dict[str, Any] = {}
    for name, spec in pre["primary"].items():
        ordered = sorted(distributions[name])
        if spec["direction"] == "higher":
            bound = ordered[lower_index]
            inside = bound > spec["margin"]
            entry = {"difference": round(point[name], 4), "difference_lower_95": round(bound, 4)}
        elif spec["direction"] == "lower":
            bound = ordered[upper_index]
            inside = bound < spec["margin"]
            entry = {"difference": round(point[name], 4), "difference_upper_95": round(bound, 4)}
        else:
            bound = ordered[upper_index]
            inside = bound < spec["margin"]
            entry = {"production_total": p_leaks, "candidate_total": c_leaks, "ratio": round(point[name], 4),
                     "ratio_upper_95": round(bound, 4)}
        if name in rates["production"]:
            entry = {"production": round(rates["production"][name], 4),
                     "candidate": round(rates["candidate"][name], 4), **entry}
        primary[name] = {**entry, "margin": spec["margin"], "inside_margin": inside}
    gate_pairs = sum(len(rows) for rows in gate_strata.values())
    p_gate, c_gate = dict(zip(GATE_FIELDS, gate_sums[:width])), dict(zip(GATE_FIELDS, gate_sums[width:]))
    secondary_point = secondary_values(gate_sums)
    result["pairs"] = {"gate": gate_pairs, "redaction": sum(len(rows) for rows in redaction_strata.values())}
    result["primary"] = primary
    result["secondary"] = {
        "critical_misses": {"production": p_gate["critical"], "candidate": c_gate["critical"],
                            "ratio": round(secondary_point["critical_ratio"], 4),
                            "ratio_upper_95": round(sorted(secondary_distributions["critical_ratio"])[upper_index], 4)},
        "forbidden_claims": {"production": p_gate["forbidden"], "candidate": c_gate["forbidden"],
                             "ratio": round(secondary_point["forbidden_ratio"], 4),
                             "ratio_upper_95": round(sorted(secondary_distributions["forbidden_ratio"])[upper_index], 4)},
        "mean_output_tokens": {arm: round(sum(samples[s]["output_tokens"] for ids in gate_ids.values()
                                              for s in ids if usable(s)) / gate_pairs, 1) for arm, samples in arms},
        "per_class": per_class(production, candidate, gate_ids, usable),
    }
    result["per_case_distinct_outputs"] = {case: {arm: distinct[arm][case] for arm in distinct} for case in cases}
    result["verdict"] = "pass" if all(entry["inside_margin"] for entry in primary.values()) else "fail"
    return result


def per_class(production: dict[str, dict[str, Any]], candidate: dict[str, dict[str, Any]],
              gate_ids: dict[str, list[str]], usable: Any) -> dict[str, Any]:
    sums: dict[str, dict[str, list[int]]] = {}
    for ids in gate_ids.values():
        for sample_id in ids:
            if not usable(sample_id):
                continue
            klass = production[sample_id]["class"] or "unknown"
            for arm, samples in (("production", production), ("candidate", candidate)):
                row = sums.setdefault(klass, {}).setdefault(arm, [0] * len(GATE_FIELDS))
                for index, value in enumerate(sample_vector(samples[sample_id], GATE_FIELDS)):
                    row[index] += value
    out: dict[str, Any] = {}
    for klass, arms in sorted(sums.items()):
        out[klass] = {"pairs": arms["production"][GATE_FIELDS.index("count")]}
        for arm, row in arms.items():
            rates = gate_rates(row)
            out[klass][arm] = {name: None if (value := rates[name]) is None else round(value, 4)
                               for name in ("required_fact_recall", "evidence_precision", "unsupported_claim_rate")}
    return out


def verdict(args: argparse.Namespace) -> dict[str, Any]:
    runs = {"production": args.production, "candidate": args.candidate,
            "production_determinism": args.production_determinism,
            "candidate_determinism": args.candidate_determinism}
    loaded = {name: load_run(path) for name, path in runs.items()}
    decision = decide(loaded["production"], loaded["candidate"],
                      loaded["production_determinism"], loaded["candidate_determinism"])
    return {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "preregistration": PREREGISTRATION,
        "runs": {name: run_identity(path) for name, path in runs.items()},
        **decision,
        "raw_prompts_outputs_or_secrets_included": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    variants = commands.add_parser("variants", help="write the screen and determinism prompt files")
    variants.add_argument("--cases", type=Path, required=True)
    variants.add_argument("--out", type=Path, required=True)
    variants.add_argument("--determinism-out", type=Path, required=True)
    decision = commands.add_parser("verdict", help="decide from four scored run directories")
    for name in ("production", "candidate", "production-determinism", "candidate-determinism"):
        decision.add_argument(f"--{name}", type=Path, required=True)
    decision.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "variants":
            result = write_variants(args.cases, args.out, args.determinism_out)
        else:
            result = verdict(args)
            if args.out:
                args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    except (ScreenError, OSError, KeyError, ValueError) as error:
        print(f"quality_screen: {error}", file=sys.stderr)
        return 2
    summary = {key: result[key] for key in ("verdict", "validity", "pairs", "primary") if key in result}
    print(json.dumps(summary if args.command == "verdict" else result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
