"""Documentation contracts that no release gate checks: anchors, and release-neutral pages.

Anchors. `scripts/verify_release.py` already requires the file behind every relative link. This
suite adds the fragment. A link to `FILE.md#fragment`, to `#fragment` in the same file, or to
`https://github.com/alphastorm/omp-ninfer/blob/main/FILE.md#fragment` from the site, `llms.txt`,
or an issue form must match a GitHub heading slug or an explicit `id`/`name` anchor in the target.
Release notes, tagged guides and published release bodies link into the living documents and can
no longer be edited. When a heading they cite is renamed or moved, keep the old fragment alive
with `<a id="old-slug"></a>` beside the new location.

Release-neutral pages. `docs/FACTS.md` owns the current release's identities. The reference pages
describe behavior that holds across releases and link there, so publishing a release does not
edit them.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import unittest
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MAIN_URL = re.compile(
    r"https://github\.com/alphastorm/omp-ninfer/(?:blob|tree)/main/([^\s\"'<>)#?]+)(?:#([^\s\"'<>)]+))?")
FENCE = re.compile(r"^\s*(?:>\s*)*(`{3,}|~{3,})")
HEADING = re.compile(r"^ {0,3}#{1,6}\s+(.*?)(?:\s+#+)?\s*$")
EXPLICIT_ANCHOR = re.compile(r"""<[A-Za-z][^>]*?\s(?:id|name)=["']([^"']+)["']""")
INLINE_LINK = re.compile(r"""!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+["'][^)]*["'])?\s*\)""")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s+<?(\S+?)>?(?:\s|$)")
HTML_LINK = re.compile(r"""\s(?:href|src)=["']([^"']+)["']""")
CODE_SPAN = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)")


def published(*patterns: str) -> list[Path]:
    """Tracked or untracked-but-not-ignored files, as the release verifier counts them."""
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard",
         "--", *patterns],
        capture_output=True,
    )
    if listed.returncode != 0:
        return sorted(path for pattern in patterns for path in ROOT.glob(f"**/{pattern}"))
    names = [name for name in listed.stdout.decode("utf-8").split("\0") if name]
    return sorted(path for path in (ROOT / name for name in names) if path.is_file())


def prose_lines(text: str) -> list[str]:
    """The document's lines with fenced code blanked, so line numbers stay true."""
    lines, fence = [], None
    for line in text.splitlines():
        marker = FENCE.match(line)
        if marker and fence is None:
            fence = marker.group(1)[0] * 3
            lines.append("")
        elif fence is not None:
            if line.strip().lstrip("> ").startswith(fence):
                fence = None
            lines.append("")
        else:
            lines.append(line)
    return lines


def slug(heading: str) -> str:
    """GitHub's heading anchor: rendered text, lowercased, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = re.sub(r"(?<![\w`])_(?=\S)(.+?)(?<=\S)_(?![\w`])", r"\1", text)
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


@lru_cache(maxsize=None)
def anchors(path: Path) -> frozenset[str]:
    found: set[str] = set()
    seen: Counter[str] = Counter()
    for line in prose_lines(path.read_text(encoding="utf-8")):
        heading = HEADING.match(line)
        if heading:
            base = slug(heading.group(1))
            found.add(base if seen[base] == 0 else f"{base}-{seen[base]}")
            seen[base] += 1
        found.update(EXPLICIT_ANCHOR.findall(line))
    return frozenset(found)


def markdown_targets(path: Path) -> list[tuple[int, str]]:
    targets = []
    for number, line in enumerate(prose_lines(path.read_text(encoding="utf-8")), 1):
        reference = REFERENCE_LINK.match(line)
        if reference:
            targets.append((number, reference.group(1)))
            continue
        line = CODE_SPAN.sub("", line)
        targets.extend((number, target) for target in INLINE_LINK.findall(line))
        targets.extend((number, target) for target in HTML_LINK.findall(line))
    return targets


def broken(source: Path, number: int, target: str) -> str | None:
    """Why `target`, written at `source:number`, does not reach its Markdown anchor; else None."""
    main = MAIN_URL.fullmatch(target)
    if main:
        linked, fragment = ROOT / unquote(main.group(1)), main.group(2)
        if not linked.exists():
            return f"{source.relative_to(ROOT).as_posix()}:{number}: {target} names a missing path"
    elif re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:|^//", target):
        return None
    else:
        relative, _, fragment = target.partition("#")
        linked = (source.parent / unquote(relative.split("?", 1)[0])) if relative else source
    if not fragment or linked.suffix != ".md" or not linked.is_file():
        return None
    if unquote(fragment) in anchors(linked.resolve()):
        return None
    return (f"{source.relative_to(ROOT).as_posix()}:{number}: {target} names no heading or anchor "
            f"in {linked.resolve().relative_to(ROOT).as_posix()}")


class DocumentationAnchorTests(unittest.TestCase):
    def test_markdown_links_reach_their_anchors(self) -> None:
        failures = [problem for path in published("*.md", "llms.txt")
                    for number, target in markdown_targets(path)
                    if (problem := broken(path, number, target))]
        if failures:
            self.fail("\n" + "\n".join(failures))

    def test_site_and_issue_form_links_to_main_reach_their_anchors(self) -> None:
        failures = []
        for path in published("site/*.html", "site/**/*.html", ".github/ISSUE_TEMPLATE/*.yml"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for match in MAIN_URL.finditer(line):
                    if (problem := broken(path, number, match.group(0))):
                        failures.append(problem)
        if failures:
            self.fail("\n" + "\n".join(failures))

    def test_slugs_follow_github(self) -> None:
        cases = {
            "Current release": "current-release",
            "v0.10.0 public release — DFlash2 on the RTX 5090":
                "v0100-public-release--dflash2-on-the-rtx-5090",
            "`draft`": "draft",
            "[Get started →](docs/QUICKSTART.md)": "get-started-",
            "What `--require-ready` checks (and why)": "what---require-ready-checks-and-why",
            "RTX&nbsp;5090 <sub>container</sub>": "rtx5090-container",
            "The _one_ owner of `snake_case` names": "the-one-owner-of-snake_case-names",
        }
        for heading, expected in cases.items():
            with self.subTest(heading=heading):
                self.assertEqual(slug(heading), expected)

    def test_duplicate_headings_and_explicit_anchors_are_addressable(self) -> None:
        document = ROOT / "tests" / "fixtures" / "anchors.md"
        self.assertEqual(
            anchors(document),
            frozenset({"anchors-fixture", "fixed", "fixed-1", "kept-old-slug", "named"}),
        )
        self.assertIsNone(broken(document, 1, "#fixed-1"))
        self.assertIsNone(broken(document, 1, "anchors.md#kept-old-slug"))
        self.assertIn("names no heading or anchor in tests/fixtures/anchors.md",
                      broken(document, 1, "#in-a-fence") or "")
        self.assertIn("names no heading or anchor", broken(document, 1, "anchors.md#Fixed") or "")


class ReleaseNeutralPageTests(unittest.TestCase):
    PAGES = (
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/ARCHITECTURE.md",
        "docs/DECISION_GUIDE.md",
        "docs/RELATED_WORK.md",
        "docs/SECURITY.md",
        "docs/TROUBLESHOOTING.md",
        "examples/fleet/README.md",
    )

    @staticmethod
    def current_identities() -> list[str]:
        """The product release, client version and runtime component tags the manifest binds."""
        release = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
        manifest = json.loads(
            (ROOT / "releases" / release / "manifest.json").read_text(encoding="utf-8"))
        components = manifest["components"]
        runtimes = [components["ninfer"], *components.get("ninfer_variants", [])]
        found = [release, components["omp"].get("distribution_version"),
                 *(runtime.get("release_tag") for runtime in runtimes)]
        return sorted({identity for identity in found if isinstance(identity, str) and identity})

    @staticmethod
    def named(identity: str, line: str) -> bool:
        return re.search(r"(?<![\w.-])" + re.escape(identity) + r"(?![\w-]|\.\d)", line) is not None

    def test_reference_pages_name_no_current_release_identity(self) -> None:
        identities = self.current_identities()
        failures = [
            f"{page}:{number}: names {identity}; link docs/FACTS.md#current-release instead"
            for page in self.PAGES
            for number, line in enumerate(
                (ROOT / page).read_text(encoding="utf-8").splitlines(), 1)
            for identity in identities if self.named(identity, line)
        ]
        if failures:
            self.fail("\n" + "\n".join(failures))

    def test_an_identity_is_matched_whole(self) -> None:
        self.assertTrue(self.named("v0.19.0", "Run from tag `v0.19.0`."))
        self.assertTrue(self.named("18.20.0", "stock Oh My Pi 18.20.0, unmodified"))
        self.assertFalse(self.named("v0.19.0", "see releases/v0.19.0-rc.1 and v0.19.01"))
        self.assertFalse(self.named("18.20.0", "build 118.20.0 and 18.20.0.1"))



if __name__ == "__main__":
    unittest.main()
