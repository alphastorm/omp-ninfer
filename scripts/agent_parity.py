#!/usr/bin/env python3
"""Replay versioned p16-agent-parity rules on per-position comparisons.

Bounds and driver oracles are unchanged: candidate cached-minus-prompt >= incumbent;
candidate server TTFT <= incumbent + max(0.25 s, 25% of incumbent TTFT).

Sequential positions pair by label. Jobs with concurrent_receipts (incumbent/candidate
paths relative to the comparison) derive concurrent phase membership from receipt
request.phase and phases[].summary.per_request. A phase is simultaneous only when
all members were submitted before any member's first output. Pair its requests by
server admit/start timestamps when available for every member of both arms;
otherwise use client first_output_monotonic_s identically on both arms. Request-done
timestamps and engine request IDs are not admission timestamps. Equal server times
use client first-output order as a tie-breaker; indistinguishable ranks fail closed.

usage: agent_parity.py <comparison.json> [--out verdict.json]
Inputs require contract_version and rule. Contract 1 accepts the original positional
shape under rule /1. Contract 2 requires semantic labels and supports /1 or /2.
Unversioned, unsupported or incompatible inputs exit 2 with a contract-version error,
never an empty or partial pairing verdict. Rule /1 retains positional comparisons;
rule /2 retains receipt-backed admission pairing. Probe drivers still own all oracles.
"""
import argparse
import json
import math
import sys
from pathlib import Path

RULE_ONE = 'p16-agent-parity/1'
RULE_TWO = 'p16-agent-parity/2'
TTFT_ABSOLUTE_SLACK_S = 0.25
TTFT_RELATIVE_SLACK = 0.25
SERVER_ORDER_PATHS = (
    ('generation', 'admission', 'admitted_monotonic_s'),
    ('generation', 'admission', 'admitted_unix_ms'),
    ('generation', 'admission', 'started_monotonic_s'),
    ('generation', 'admission', 'started_unix_ms'),
    ('admitted_monotonic_s',), ('admitted_unix_ms',),
    ('started_monotonic_s',), ('started_unix_ms',),
    ('start_timestamp_unix_ms',), ('request_start_unix_ms',),
)


class ContractVersionError(ValueError):
    def __init__(self, message):
        super().__init__('contract-version error: ' + message)


def input_contract(document):
    if not isinstance(document, dict):
        raise ContractVersionError('comparison must be an object')
    version = document.get('contract_version')
    rule = document.get('rule')
    if type(version) is not int or version not in (1, 2):
        raise ContractVersionError('contract_version must be 1 or 2')
    if rule not in (RULE_ONE, RULE_TWO):
        raise ContractVersionError('rule must be p16-agent-parity/1 or p16-agent-parity/2')
    if version == 1 and rule != RULE_ONE:
        raise ContractVersionError('contract 1 supports only rule /1; /2 needs contract 2 and semantic labels')
    jobs = document.get('jobs')
    if not isinstance(jobs, dict) or not jobs:
        raise ContractVersionError('jobs must be a nonempty object')
    metrics = tuple(prefix + suffix for prefix in ('incumbent_', 'candidate_')
                    for suffix in ('prompt_tokens', 'cached_tokens', 'server_ttft_seconds'))
    for job, value in jobs.items():
        if not isinstance(value, dict):
            raise ContractVersionError(f'job {job} must be an object')
        if 'positions' not in value:  # A driver-only job is explicitly unjudged.
            continue
        positions = value['positions']
        if not isinstance(positions, list) or not positions:
            raise ContractVersionError(f'job {job} positions must be a nonempty array; omit it for driver-only jobs')
        for row in positions:
            if not isinstance(row, dict) or 'position' not in row or any(key not in row for key in metrics):
                raise ContractVersionError(f'job {job} needs position and all six parity metrics on every row')
            if any(type(row[key]) not in (int, float) or not math.isfinite(row[key]) for key in metrics):
                raise ContractVersionError(f'job {job} parity metrics must be finite numbers')
            if version == 2 and (not isinstance(row.get('label'), str) or not row['label']):
                raise ContractVersionError(f'job {job} contract 2 requires a nonempty semantic label on every row')
    return version, rule


def judge_position(row: dict) -> list[str]:
    failures = []
    inc_gap = row['incumbent_cached_tokens'] - row['incumbent_prompt_tokens']
    cand_gap = row['candidate_cached_tokens'] - row['candidate_prompt_tokens']
    if cand_gap < inc_gap:
        failures.append(f'cached-prompt {cand_gap} < incumbent {inc_gap}')
    inc_ttft = row['incumbent_server_ttft_seconds']
    bound = inc_ttft + max(TTFT_ABSOLUTE_SLACK_S, TTFT_RELATIVE_SLACK * inc_ttft)
    if row['candidate_server_ttft_seconds'] > bound:
        failures.append(f"ttft {row['candidate_server_ttft_seconds']:.3f}s > bound {bound:.3f}s")
    return failures


def receipt_phases(receipt):
    groups = {}
    labels = []
    for index, scenario in enumerate(receipt['scenarios']):
        requests = scenario['requests']
        members = {request['label']: request for request in requests}
        if len(members) != len(requests):
            raise ValueError('duplicate request label in receipt')
        covered = []
        for phase in scenario['phases']:
            phase_labels = [row['label'] for row in phase['summary']['per_request']]
            selected = [members[label] for label in phase_labels]
            if any(request['phase'] != phase['name'] for request in selected):
                raise ValueError('receipt phase membership mismatch')
            covered.extend(phase_labels)
            simultaneous = len(selected) > 1 and max(request['submitted_monotonic_s'] for request in selected) < min(
                request['first_output_monotonic_s'] for request in selected)
            key = (index, scenario['name'], scenario.get('repeat'), phase['name'])
            if key in groups:
                raise ValueError('duplicate receipt phase')
            groups[key] = (selected, simultaneous)
        if sorted(covered) != sorted(members):
            raise ValueError('receipt phases do not cover each request exactly once')
        labels.extend(members)
    if len(labels) != len(set(labels)):
        raise ValueError('repeated receipt labels need separate comparison jobs')
    return groups, set(labels)


def server_order(request, path):
    events = request.get('server_request_done') or []
    if len(events) != 1:
        return None
    value = events[0]
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return value if isinstance(value, (int, float)) and math.isfinite(value) else None


def admission_pairs(incumbent, candidate):
    both = incumbent + candidate
    path = next((path for path in SERVER_ORDER_PATHS if all(server_order(row, path) is not None for row in both)), None)
    if path:
        source = 'server_admission.' + path[-1]
        tied = any(len({server_order(row, path) for row in arm}) != len(arm) for arm in (incumbent, candidate))
        if tied:
            source += '+client_first_output_monotonic_s'
        def order(row):
            return (server_order(row, path), row['first_output_monotonic_s'])
    else:
        source = 'client_first_output_monotonic_s'
        def order(row):
            return (row['first_output_monotonic_s'],)
    for arm in (incumbent, candidate):
        if any(not all(isinstance(value, (int, float)) and math.isfinite(value) for value in order(row)) for row in arm):
            raise ValueError('missing finite admission-order evidence')
        if len({order(row) for row in arm}) != len(arm):
            raise ValueError('indistinguishable admission ranks')
    return zip(sorted(incumbent, key=order), sorted(candidate, key=order)), source


def pair_positions(job, base):
    positions = job['positions']
    by_label = {row['label']: row for row in positions}
    if len(by_label) != len(positions):
        raise ValueError('duplicate comparison label')
    pairing = {label: (label, 'label', None, None, None) for label in by_label}
    receipts = job.get('concurrent_receipts')
    if receipts:
        arms = {arm: receipt_phases(json.loads((base / receipts[arm]).read_text(encoding='utf-8'))) for arm in ('incumbent', 'candidate')}
        old, old_labels = arms['incumbent']
        new, new_labels = arms['candidate']
        if old.keys() != new.keys() or old_labels != new_labels or old_labels != set(by_label):
            raise ValueError('receipt phases/labels differ between arms or comparison')
        for phase, (incumbent, simultaneous) in old.items():
            candidate, candidate_simultaneous = new[phase]
            if simultaneous != candidate_simultaneous or {row['label'] for row in incumbent} != {row['label'] for row in candidate}:
                raise ValueError('simultaneous phase membership differs between arms')
            if simultaneous:
                pairs, source = admission_pairs(incumbent, candidate)
                for rank, (inc, cand) in enumerate(pairs, 1):
                    pairing[inc['label']] = (cand['label'], 'admission_rank', '/'.join(map(str, phase)), rank, source)
    paired = []
    for original in positions:
        row = dict(original)
        candidate_label, mode, phase, rank, source = pairing[row['label']]
        row.update({key: value for key, value in by_label[candidate_label].items() if key.startswith('candidate_')})
        row.update(incumbent_label=row['label'], candidate_label=candidate_label, pairing=mode)
        if mode == 'admission_rank':
            row.update(phase=phase, admission_rank=rank, ordering_source=source)
        inc_ttft = row['incumbent_server_ttft_seconds']
        row['ttft_bound_seconds'] = inc_ttft + max(TTFT_ABSOLUTE_SLACK_S, TTFT_RELATIVE_SLACK * inc_ttft)
        row['ttft_margin_seconds'] = row['ttft_bound_seconds'] - row['candidate_server_ttft_seconds']
        row['cached_prompt_gap_delta'] = (row['candidate_cached_tokens'] - row['candidate_prompt_tokens']) - (
            row['incumbent_cached_tokens'] - row['incumbent_prompt_tokens'])
        paired.append(row)
    return paired


def judge_comparison(document, base, source):
    version, rule = input_contract(document)
    identity = {'contract_version': version, 'rule': rule}
    verdict = {**identity, 'source': source, 'jobs': {}, 'passed': True}
    for job, value in document['jobs'].items():
        positions = value.get('positions')
        if positions is None:
            verdict['jobs'][job] = {**identity, 'judged': False, 'note': 'no per-position rows; driver verdict applies'}
            continue
        failing = {}
        if rule == RULE_ONE:
            # The original /1 loop: compare the metrics already paired on each row.
            for row in positions:
                reasons = judge_position(row)
                if reasons:
                    failing[str(row['position'])] = reasons
            judged = {**identity, 'judged': True, 'positions': len(positions)}
        else:
            try:
                paired = pair_positions(value, base)
            except (KeyError, ValueError, TypeError, AttributeError, IndexError, OSError) as error:
                detail = type(error).__name__ if isinstance(error, OSError) else str(error)
                raise ContractVersionError(f'job {job} incompatible /2 pairing evidence: {detail}') from error
            if not paired or len(paired) != len(positions):
                raise ContractVersionError(f'job {job} /2 must pair every position exactly once')
            for row in paired:
                reasons = judge_position(row)
                row.update(**identity, passed=not reasons, failures=reasons)
                if reasons:
                    failing[str(row['position'])] = reasons
            judged = {**identity, 'judged': True, 'positions': len(positions), 'paired_positions': paired}
        verdict['jobs'][job] = {**judged, 'failing': failing, 'passed': not failing}
        verdict['passed'] = verdict['passed'] and not failing
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('comparison', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    document = None
    try:
        try:
            document = json.loads(args.comparison.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise ContractVersionError('comparison must be readable UTF-8 JSON') from error
        verdict = judge_comparison(document, args.comparison.parent, args.comparison.name)
        code = 0 if verdict['passed'] else 1
    except ContractVersionError as error:
        supplied = document if isinstance(document, dict) else {}
        verdict = {'contract_version': supplied.get('contract_version'), 'rule': supplied.get('rule'),
                   'source': args.comparison.name, 'passed': False,
                   'error': {'code': 'contract-version', 'message': str(error)}}
        code = 2
    text = json.dumps(verdict, indent=2) + '\n'
    if args.out:
        args.out.write_text(text, encoding='utf-8')
    sys.stdout.write(text)
    return code


if __name__ == '__main__':
    sys.exit(main())
