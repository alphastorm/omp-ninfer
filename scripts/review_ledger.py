#!/usr/bin/env python3
"""Publish a content-safe ledger, G4 binding and composition review from closed directories.

``--reviews`` names a manifest, or a directory containing ``manifest.json``. Its
native_runtime, native_component_delta and product_tooling entries name directories
(relative to the manifest), closed statuses and lead closure statements. ``--values``
supplies ledger_status, as_of and product_council {status, closure, scope_sentence};
approval_granted defaults to true. Only product_tooling is required: unchanged runtime
components need no new runtime reviews. Optional values.composition_review fields
native_runtime_summary, native_component_delta_subject and native_component_delta_summary
provide lead-authored result clauses; otherwise the closed ledger's closure text is used.
The product residuals_sentence, or its scope_sentence, completes that summary. Only a
pending composition.review or the identical generated value may be replaced.
Product subjects must lie between this release's plan addition (when present) and
the candidate. Runtime and native-delta subjects must name released component sources.
This records review closure, never publication.
``--check`` validates the inputs and refuses if either checked-in output differs.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_io import atomic_write, atomic_write_json, git
from verify_release import (CLOSED_REVIEW_STATUS_RE, PRIVATE_MARKERS, review_subject_errors,
                            validate_review_ledger)

SEAT_FIELDS = ("reviewer_id", "selectionClass", "role", "independence_class", "authority",
               "model", "model_family")
SECTIONS = ("native_runtime", "native_component_delta", "product_tooling")
# Whole private path tokens and synthetic identifiers, applied to leaves, never source bytes.
SANITIZE = (
    (re.compile(r"""[A-Z]:[\\/]+Users[\\/]+[^\s"'`\])}]*""", re.I),
     "a Windows user-profile path"),
    (re.compile(r"""/(?:Users|home)/[^\s"'`\])}]*"""), "a POSIX user-profile path"),
    (re.compile(r"GPU-[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"),
     "a synthetic GPU-identifier sentinel"),
)


def require(condition: Any, message: str) -> None:
    if not condition:
        raise SystemExit("review_ledger: " + message)


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"review_ledger: cannot read {path.name}: {error}") from error
    require(isinstance(value, dict), f"{path.name} must contain an object")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def closed(status: Any, label: str) -> None:
    require(isinstance(status, str) and CLOSED_REVIEW_STATUS_RE.fullmatch(status) is not None,
            f"{label} is not closed")


def table(path: Path, columns: int) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in re.split(r"(?<!\\) \| ", line.strip()[2:-2])]
        if cells and cells[0] in ("Finding", "ID", "Row"):
            continue
        require(len(cells) == columns, f"{path.name}: expected {columns} table cells")
        rows.append([cell.replace("\\|", "|") for cell in cells])
    require(rows, f"{path.name}: no disposition rows")
    return rows


def receipts(directory: Path, patterns: list[str]) -> dict:
    return {path.name: digest(path) for pattern in patterns
            for path in sorted(directory.glob(pattern)) if path.is_file()}


def results(directory: Path, seats: list[dict]) -> dict:
    output = {}
    for seat in seats:
        path = directory / (seat["reviewer_id"] + ".json")
        if path.is_file():
            result = load(path)
            output[seat["reviewer_id"]] = {
                key: result[key] for key in ("summary", "evidence", "unresolved")}
        else:
            output[seat["reviewer_id"]] = {"status": "missing", "approval_granted": False}
    return output


def council(directory: Path, status: str, closure: str, *, product: bool) -> dict:
    closed(status, directory.name)
    frozen = load(directory / "frozen-subject.json")
    panel = load(directory / "panel-selection.json")
    resolver = load(directory / "resolver-receipt.json")
    record = load(directory / "review-record.json")
    require(record.get("review_id") == directory.name, "review-record review_id mismatch")
    if "status" in record:
        closed(record["status"], "review-record status")
    selected = panel["selected"]
    output = {"repository": "https://github.com/alphastorm/omp-ninfer"} if product else {}
    output.update(review_id=directory.name, review_sequence_id=record["review_sequence_id"],
                  review_class="full-council", status=status)
    output["reviewed_commit" if product else "source_commit"] = frozen["subjectCommit"]
    output.update(
        base_commit=load(directory / "prepare-input.json")["subject"]["base"],
        subject_digest=panel["subjectDigest"], resolver_subject_digest=frozen["subjectDigest"],
        resolver_assignments=[{key: seat[key] for key in SEAT_FIELDS}
                              for seat in resolver["assignments"]],
        receipt_digests=receipts(directory, [
            "close-report.md", "ledger.md", "review-record.json", "frozen-subject.json",
            "resolver-receipt.json", "panel-selection.json",
            *(seat["reviewer_id"] + ".json" for seat in selected),
            "review-dispatch-envelope.attempt-*.json"]),
        reviewer_results=results(directory, selected),
        dispositions={row[0].split(" — ", 1)[0].strip(): {
            "severity": row[3], "result": row[6], "disposition": row[7],
            "change": row[8], "rationale": row[9]} for row in table(directory / "ledger.md", 10)},
        closure=closure)
    for name in ("close-report.md", "ledger.md", "review-record.json"):
        require(name in output["receipt_digests"], f"{name} is required")
    return output


def focused(directory: Path, status: str, closure: str, base: str) -> dict:
    closed(status, "focused review status")
    receipt = load(directory / "receipt.json")
    subject = load(directory / "subject.json")
    require(receipt.get("reviewClass") == "focused", "receipt is not a focused review")
    if "status" in receipt:
        closed(receipt["status"], "focused receipt status")
    seats = [{key: seat[key] for key in SEAT_FIELDS} for seat in receipt["assignments"]]
    return {
        "review_class": "focused", "status": status, "source_commit": subject["subjectCommit"],
        "base_commit": base, "subject_digest": receipt["subjectDigest"],
        "changed_paths": subject["files"], "resolver_assignments": seats,
        "receipt_digests": receipts(directory, [
            "receipt.json", "subject.json", "scope.md", "dispositions.md",
            *(seat["reviewer_id"] + ".json" for seat in seats), "envelope.attempt-*.json"]),
        "reviewer_results": results(directory, seats),
        "dispositions": {row[0].split(" ", 1)[0]: {
            "severity": row[2], "result": row[3], "disposition": row[4], "rationale": row[5]}
            for row in table(directory / "dispositions.md", 6)},
        "closure": closure,
    }


def sanitize(value: Any, counts: dict[str, int]) -> Any:
    if isinstance(value, str):
        for pattern, replacement in SANITIZE:
            value, hits = pattern.subn(replacement, value)
            if hits:
                counts[replacement] = counts.get(replacement, 0) + hits
        return value
    if isinstance(value, list):
        return [sanitize(child, counts) for child in value]
    if isinstance(value, dict):
        return {key: sanitize(child, counts) for key, child in value.items()}
    return value


def public_text(value: Any) -> None:
    if isinstance(value, str):
        require(not any(marker.casefold() in value.casefold() for marker in PRIVATE_MARKERS),
                "private marker in public ledger")
        require(not re.search(r"GPU-[0-9a-f-]{8,}|[A-Z]:[\\/](?:[U]sers|[Hh]ome)[\\/]", value, re.I),
                "private identifier in public ledger")
    elif isinstance(value, dict):
        for key, child in value.items():
            public_text(key)
            public_text(child)
    elif isinstance(value, list):
        for child in value:
            public_text(child)


def build(root: Path, release: str, candidate: str, reviews: Path,
          values: dict, *, as_of: str | None = None) -> tuple[dict, dict]:
    require(re.fullmatch(r"v\d+\.\d+\.\d+", release), "release must be a GA product version")
    require(re.fullmatch(r"[0-9a-f]{40}", candidate), "candidate must be a full commit")
    try:
        git(root, "merge-base", "--is-ancestor", candidate, "HEAD")
    except subprocess.CalledProcessError as error:
        raise SystemExit("review_ledger: candidate is not an ancestor of HEAD") from error
    manifest_path = reviews / "manifest.json" if reviews.is_dir() else reviews
    entries = load(manifest_path)
    require("product_tooling" in entries and set(entries) <= set(SECTIONS),
            "review manifest must name product_tooling and only known review sections")
    product = values["product_council"]
    require(product.get("stage_commit", candidate) == candidate, "stage_commit must equal candidate")
    sections = {}
    for name in SECTIONS:
        if name not in entries:
            continue
        entry = entries[name]
        require(isinstance(entry, dict), f"{name} manifest entry must be an object")
        directory = Path(entry["directory"]).expanduser()
        if not directory.is_absolute():
            directory = manifest_path.parent / directory
        lead = product if name == "product_tooling" else entry
        closed(entry.get("status", lead.get("status")), name)
        status, closure = lead["status"], lead["closure"]
        closed(status, name)
        if name == "native_component_delta":
            base = entry.get("base_commit") or sections.get("native_runtime", {}).get("source_commit")
            require(isinstance(base, str) and re.fullmatch(r"[0-9a-f]{40}", base),
                    "native component delta must identify its base commit")
            sections[name] = focused(directory, status, closure, base)
        else:
            sections[name] = council(directory, status, closure, product=name == "product_tooling")
    tooling = sections["product_tooling"]
    require(entries["product_tooling"].get("stage_commit", candidate) == candidate,
            "stage_commit must equal candidate")
    tooling["stage_commit"] = candidate
    if product.get("follow_up"):
        tooling["follow_up"] = product["follow_up"]
    epochs = []
    for number, epoch in enumerate(product.get("epochs", []), 1):
        closed(epoch.get("status"), "epoch status")
        directory = Path(epoch["directory"]).expanduser()
        if not directory.is_absolute():
            directory = manifest_path.parent / directory
        record = load(directory / "review-record.json")
        if "status" in record:
            closed(record["status"], "epoch review-record status")
        epochs.append({"epoch": number, "review_id": directory.name,
                       "review_mode": epoch["review_mode"], "review_class": epoch["review_class"],
                       "reviewed_commit": epoch["reviewed_commit"], "status": epoch["status"],
                       "receipt_digests": {"review-record.json": digest(directory / "review-record.json")}})
    if epochs:
        tooling["epochs"] = epochs
    manifest = {}
    if any(name in sections for name in ("native_runtime", "native_component_delta")):
        try:
            manifest = json.loads(git(root, "show", f"{candidate}:releases/{release}/manifest.json"))
        except (subprocess.CalledProcessError, ValueError) as error:
            raise SystemExit(f"review_ledger: cannot read release manifest at candidate {candidate}") from error
        require(isinstance(manifest, dict), "candidate release manifest must contain an object")
    subject_errors = review_subject_errors(root, release, sections, manifest)
    require(not subject_errors, "; ".join(subject_errors))
    status = values["ledger_status"]
    closed(status, "ledger status")
    require(values.get("approval_granted", True) is True, "closed ledger must grant G4 approval")
    stamp = as_of or values.get("as_of") or date.today().isoformat()
    date.fromisoformat(stamp)
    subjects = []
    if "native_runtime" in sections:
        runtime = sections["native_runtime"]
        subjects.append(f"exact-source runtime full council {runtime['review_id']} on N "
                        f"{runtime['source_commit']} ({runtime['status']})")
    if "native_component_delta" in sections:
        delta = sections["native_component_delta"]
        subjects.append(f"the focused review of the native component delta to N' "
                        f"{delta['source_commit']} ({delta['status']})")
    subjects.append(f"product full council {tooling['review_id']} ({tooling['status']})")
    subject_scope = (", ".join(subjects[:-1]) + ", and " + subjects[-1]
                     if len(subjects) > 1 else subjects[0])
    ledger = {
        "artifact_type": "omp_ninfer_review_ledger", "schema_version": 1, "release": release,
        "as_of": stamp, "status": status, "approval_granted": True,
        "publication_authorized": False, "public_route_acceptance_granted": False,
        "scope": (
            f"Closed {subject_scope} with route stage candidate "
            f"{candidate}. {product['scope_sentence']} This is not approval of a later executable "
            "subject, publication, or independent public-user acceptance; no human waivers are recorded."),
        **sections,
    }
    counts: dict[str, int] = {}
    ledger = sanitize(ledger, counts)
    public_text(ledger)
    return ledger, counts


def composition_review(ledger: dict, values: dict, reference: str) -> dict:
    """Restate only the reviews actually present; result clauses remain lead-owned inputs."""
    details = values.get("composition_review", {})
    require(isinstance(details, dict) and all(isinstance(text, str) and text.strip()
                                             for text in details.values()),
            "values.composition_review must contain nonempty text clauses")
    sentences = []
    runtime = ledger.get("native_runtime")
    if runtime is not None:
        result = details.get("native_runtime_summary",
                             f"closed ({runtime['status']}). {runtime['closure']}")
        sentences.append(f"Runtime full council {runtime['review_id']} on "
                         f"{runtime['source_commit']} {result}")
    delta = ledger.get("native_component_delta")
    if delta is not None:
        subject = details.get("native_component_delta_subject", "the native component delta")
        result = details.get("native_component_delta_summary",
                             f"closed ({delta['status']}). {delta['closure']}")
        sentences.append(f"The focused review of {subject} at {delta['source_commit']} {result}")
    product = ledger["product_tooling"]
    sentences.append(f"Product full council {product['review_id']} closed ({product['status']}) "
                     f"with route candidate {product['stage_commit']}.")
    lead = values["product_council"]
    sentences.append(lead.get("residuals_sentence", lead["scope_sentence"]))
    sentences.append(f"The combined content-safe ledger is {reference}.")
    sentences.append("Review approval authorizes neither product publication nor production promotion.")
    return {"status": ledger["status"], "scope": " ".join(sentences)}


def write_ledger(root: Path, release: str, candidate: str, reviews: Path, values: dict,
                 *, check: bool = False, as_of: str | None = None) -> dict:
    ledger, counts = build(root, release, candidate, reviews, values, as_of=as_of)
    reference = f"releases/{release}/review/runtime-ledger.json"
    payload = (json.dumps(ledger, indent=2) + "\n").encode("utf-8")
    qualification_path = root / "releases" / release / "qualification.json"
    qualification = deepcopy(load(qualification_path))
    review = sanitize(composition_review(ledger, values, reference), counts)
    public_text(review)
    composition = qualification.get("composition")
    require(isinstance(composition, dict), "qualification.composition must contain the staged review")
    staged_review = composition.get("review")
    require(staged_review == review
            or isinstance(staged_review, dict) and staged_review.get("status") == "pending",
            "qualification.composition.review is neither pending nor the generated closed review")
    composition["review"] = review
    qualification.setdefault("observed_gates", {})["g4_review"] = {
        "status": "passed", "repository_path": reference, "sha256": hashlib.sha256(payload).hexdigest(),
        "ledger_status": ledger["status"], "approval_granted": True,
        "publication_authorized": False, "public_route_acceptance_granted": False,
    }
    # Use the verifier's real file reader against an isolated in-memory write plan.
    with tempfile.TemporaryDirectory() as temporary:
        staged = Path(temporary)
        atomic_write(staged / reference, payload)
        errors: list[str] = []
        validate_review_ledger(staged, release, qualification, errors)
        require(not errors, "; ".join(errors))
    qualification_bytes = (json.dumps(qualification, indent=2) + "\n").encode("utf-8")
    if check:
        require((root / reference).is_file() and (root / reference).read_bytes() == payload,
                "review ledger is not up to date")
        require(qualification_path.read_bytes() == qualification_bytes,
                "G4 binding or composition review is not up to date")
    else:
        atomic_write(root / reference, payload)
        atomic_write(qualification_path, qualification_bytes)
    return {"repository_path": reference, "sha256": hashlib.sha256(payload).hexdigest(),
            "status": ledger["status"], "sanitized": counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--reviews", required=True, type=Path)
    parser.add_argument("--values", required=True, type=Path)
    parser.add_argument("--as-of", help="override values.as_of (defaults to today's date)")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(write_ledger(ROOT, args.release, args.candidate, args.reviews,
                                  load(args.values), check=args.check, as_of=args.as_of)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
