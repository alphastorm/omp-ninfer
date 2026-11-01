"""Acceptance helpers must not decode child output with the Windows locale."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUBPROCESS_CALLS = {"run", "Popen", "check_output", "check_call", "call", "getoutput", "getstatusoutput"}


def implicit_subprocess_encodings(source: str) -> list[int]:
    """Find text-mode subprocess calls, including imported aliases and dynamic text flags."""
    tree = ast.parse(source)
    modules, functions = set(), {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names if alias.name == "subprocess")
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            functions.update((alias.asname or alias.name, alias.name) for alias in node.names
                             if alias.name in SUBPROCESS_CALLS)

    def enabled(value):
        return value is not None and not (isinstance(value, ast.Constant) and not value.value)

    missing = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = functions.get(node.func.id) if isinstance(node.func, ast.Name) else None
        if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                and node.func.value.id in modules):
            function = node.func.attr
        if function not in SUBPROCESS_CALLS:
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        text_mode = (function in {"getoutput", "getstatusoutput"}
                     or any(enabled(keywords.get(name)) for name in ("text", "universal_newlines", "encoding", "errors")))
        if text_mode and not enabled(keywords.get("encoding")):
            missing.append(node.lineno)
    return sorted(missing)


class SubprocessEncodingTests(unittest.TestCase):
    def test_ast_check_covers_aliases_multiline_and_universal_newlines(self):
        source = textwrap.dedent("""\
            import subprocess as child
            from subprocess import check_output as output
            child.run(['fixture'], text=True)
            child.Popen(
                ['fixture'], universal_newlines=True,
            )
            output(['fixture'], text=want_text, encoding=None)
            child.getoutput('fixture')
            child.run(['fixture'], errors='strict')
            child.run(['fixture'], text=True, encoding='utf-8', errors='strict')
            output(['fixture'], universal_newlines=True, encoding='utf-8')
            child.run(['fixture'], text=False)
            child.Popen(['fixture'])
            """)
        self.assertEqual(implicit_subprocess_encodings(source), [3, 4, 7, 8, 9])

    def test_all_tooling_text_subprocesses_have_explicit_encodings(self):
        missing = []
        for directory in (ROOT / "scripts", ROOT / "examples"):
            for path in sorted(directory.rglob("*.py")):
                source = path.read_text(encoding="utf-8")
                missing.extend(f"{path.relative_to(ROOT).as_posix()}:{line}"
                               for line in implicit_subprocess_encodings(source))
        self.assertEqual(missing, [], "subprocess text mode requires explicit encoding:\n" + "\n".join(missing))

    def test_tooling_text_file_reads_have_explicit_encodings(self):
        missing = []
        for directory in (ROOT / "scripts", ROOT / "examples"):
            for path in sorted(directory.rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                            and node.func.attr == "read_text" and not node.args
                            and not any(keyword.arg == "encoding" and not (
                                isinstance(keyword.value, ast.Constant) and keyword.value.value is None)
                                for keyword in node.keywords)):
                        missing.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
        self.assertEqual(missing, [], "text files require explicit encoding:\n" + "\n".join(missing))


class StockOmpUtf8Tests(unittest.TestCase):
    def pump_child(self, payload: bytes, *, invalid: bool = False):
        # Python 3.15 defaults to UTF-8 mode, so disable it in a fresh interpreter. Mock only
        # its locale: this reproduces Windows cp1252 on every CI OS while retaining the real
        # proof constructor, subprocess pipe wrappers, child bytes and _pump JSON reader.
        harness = textwrap.dedent("""\
            import argparse
            import json
            import locale
            from pathlib import Path
            import subprocess
            import sys
            import tempfile
            from unittest import mock

            sys.path.insert(0, str(Path(sys.argv[1]) / 'scripts'))
            import stock_omp_session_proof as proof

            spawn = subprocess.Popen
            def launch(command, **kwargs):
                return spawn([sys.executable, '-c', sys.argv[2]], **kwargs)

            assert not sys.flags.utf8_mode, 'fixture requires locale-based Python text defaults'
            with tempfile.TemporaryDirectory() as temporary, \\
                 mock.patch.object(locale, 'getencoding', return_value='cp1252'), \\
                 mock.patch.object(proof.subprocess, 'Popen', side_effect=launch), \\
                 mock.patch.object(proof.threading, 'Thread'), \\
                 mock.patch.object(proof.Omp, '_wait'):
                args = argparse.Namespace(omp=Path(sys.executable), home=Path(temporary),
                                          omp_version='omp/18.14.0', model='fixture/model')
                omp = proof.Omp(args, 'utf8', False)
                try:
                    if sys.argv[3] == 'invalid':
                        try:
                            omp._pump()
                        except UnicodeDecodeError as error:
                            assert error.encoding == 'utf-8', error.encoding
                        else:
                            raise AssertionError('invalid UTF-8 was not rejected')
                    else:
                        omp._pump()
                        assert omp.events.get_nowait() == json.loads(sys.argv[3])
                        assert omp.events.get_nowait() == {'type': '_eof'}
                        assert omp.events.empty()
                finally:
                    omp.close()
                    omp.stdout.close()
            """)
        child = f"import sys; sys.stdout.buffer.write({payload!r}); sys.stdout.buffer.flush()"
        expected = "invalid" if invalid else payload.decode("utf-8")
        result = subprocess.run([sys.executable, "-X", "utf8=0", "-c", harness, str(ROOT), child, expected],
                                env=dict(os.environ, PYTHONUTF8="0"), capture_output=True,
                                text=True, encoding="utf-8", errors="strict", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stock_omp_pump_preserves_utf8_under_cp1252(self):
        event = {"type": "ready", "text": "\u201cJuniper\u201d \U0001f9ea"}
        payload = (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
        with self.assertRaises(UnicodeDecodeError):
            payload.decode("cp1252")
        self.pump_child(payload)

    def test_stock_omp_pump_rejects_invalid_utf8(self):
        self.pump_child(b'{"type":"ready","text":"\xff"}\n', invalid=True)


if __name__ == "__main__":
    unittest.main()
