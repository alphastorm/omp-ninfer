"""Stateful Responses launch contract shared by OMP client proofs and validation."""
from __future__ import annotations

import os
import re

VERSION_RE = re.compile(r"(?:omp/|v)?([0-9]+)[.]([0-9]+)[.]([0-9]+)")
PER_MODEL_STATEFUL_VERSION = (18, 8, 0)


def _version_tuple(version):
    match = VERSION_RE.fullmatch(version) if isinstance(version, str) else None
    return tuple(map(int, match.groups())) if match else None


def uses_per_model_stateful(version):
    """The repository's 18.8.x client epoch and later use model compat, not an override."""
    parsed = _version_tuple(version)
    return parsed is not None and parsed >= PER_MODEL_STATEFUL_VERSION


def client_environment(version):
    """Clear even an inherited override for modern clients; retain the historical contract."""
    parsed = _version_tuple(version)
    if parsed is None:
        raise ValueError("client version must be a semantic version")
    environment = dict(os.environ)
    if parsed >= PER_MODEL_STATEFUL_VERSION:
        environment.pop("PI_OPENAI_STATEFUL", None)
    else:
        environment["PI_OPENAI_STATEFUL"] = "1"
    return environment


def stateful_environment(environment):
    """Content-safe receipt projection of the actual stateful launch environment."""
    return {key: environment[key] for key in ("PI_OPENAI_STATEFUL",) if key in environment}
