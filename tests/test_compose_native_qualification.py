"""The native qualification receipt names the transport its OMP golden run actually used."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compose_native_qualification", ROOT / "scripts" / "compose_native_qualification.py")
assert SPEC is not None and SPEC.loader is not None
COMPOSE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPOSE)


def transcript(*apis: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = [{"type": "agent_start"}]
    for api in apis:
        events.append({"type": "message_start", "message": {"role": "assistant", "api": api}})
        events.append({"type": "message_end", "message": {"role": "assistant", "api": api}})
    events.append({"type": "message_end", "message": {"role": "toolResult"}})
    return events


class OmpTransportTest(unittest.TestCase):
    def write(self, directory: Path, events: list[dict[str, Any]], encoding: str) -> Path:
        path = directory / "omp-events.jsonl"
        path.write_bytes("\n".join(json.dumps(event) for event in events).encode(encoding))
        return path

    def test_reports_the_api_the_client_used_in_either_encoding(self) -> None:
        # Windows PowerShell redirection writes UTF-16; OMP 18.2.3 talks Responses to NInfer.
        with tempfile.TemporaryDirectory() as directory:
            for encoding in ("utf-16", "utf-8"):
                path = self.write(Path(directory), transcript("openai-responses", "openai-responses"),
                                  encoding)
                self.assertEqual(COMPOSE.omp_transport(path), "openai-responses")
            path = self.write(Path(directory), transcript("openai-completions"), "utf-8")
            self.assertEqual(COMPOSE.omp_transport(path), "openai-completions")

    def test_refuses_a_run_without_one_assistant_api(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for events in (transcript("openai-responses", "openai-completions"), transcript()):
                path = self.write(Path(directory), events, "utf-8")
                with self.assertRaises(SystemExit):
                    COMPOSE.omp_transport(path)


if __name__ == "__main__":
    unittest.main()
