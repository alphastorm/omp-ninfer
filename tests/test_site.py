"""Public site coherence: every page reference is served, nothing loads remotely, and the
canonical, social, and sitemap metadata agree.

The Pages workflow publishes ``site/`` after copying brand and media assets from their canonical
sources (one ``cp <source> site/<name>`` line each). These checks keep the hand-maintained pages,
that staging list, and ``.gitignore`` in step, so a renamed asset or a stale copy fails here instead
of as a 404 on the published site.
"""

from __future__ import annotations

import re
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
ORIGIN = "https://alphastorm.github.io/omp-ninfer/"

STAGE_LINE = re.compile(r"^\s*cp (\S+) site/(\S+)$", re.MULTILINE)
REFERENCE = re.compile(r"""\b(?:src|href|poster)="([^"#?]*)""")
META = re.compile(r'<meta (?:property|name)="([^"]+)" content="([^"]*)"')
CANONICAL = re.compile(r'<link rel="canonical" href="([^"]+)"')
REMOTE_LOAD = re.compile(
    r"""<(?:script|img|video|source|iframe)\b[^>]*\bsrc="(?:https?:)?//"""
    r"""|<link\b[^>]*\brel="(?:stylesheet|preload|modulepreload|icon)"[^>]*\bhref="(?:https?:)?//"""
)
FONT_IMPORT = re.compile(r"@import|url\(\s*['\"]?(?:https?:)?//")


def staged_assets() -> dict[str, Path]:
    text = WORKFLOW.read_text(encoding="utf-8")
    staged = {name: ROOT / source for source, name in STAGE_LINE.findall(text)}
    if not staged:
        raise AssertionError("pages.yml stages no assets; the site expects staged brand and media files")
    return staged


def site_pages() -> list[Path]:
    return sorted(SITE.rglob("index.html"))


def page_url(page: Path) -> str:
    rel = page.parent.relative_to(SITE).as_posix()
    return ORIGIN if rel == "." else f"{ORIGIN}{rel}/"


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[12:16] != b"IHDR":
        raise AssertionError(f"{path} is not a PNG")
    return struct.unpack(">II", header[16:24])


class SiteCoherenceTests(unittest.TestCase):
    def test_staged_sources_exist_and_are_ignored_and_watched(self) -> None:
        staged = staged_assets()
        ignored = ROOT.joinpath(".gitignore").read_text(encoding="utf-8").splitlines()
        workflow = WORKFLOW.read_text(encoding="utf-8")
        watched = workflow.split("paths:", 1)[1].split("workflow_dispatch:", 1)[0]
        for name, source in staged.items():
            with self.subTest(asset=name):
                self.assertTrue(source.is_file(), f"{source} is the canonical source of site/{name}")
                self.assertIn(f"site/{name}", ignored, f"site/{name} must be gitignored so no copy is committed")
                self.assertIn(f"- {source.relative_to(ROOT).as_posix()}", watched, f"{source} must redeploy the site when it changes")

    def test_no_committed_copy_of_a_staged_asset(self) -> None:
        import subprocess

        tracked = subprocess.run(["git", "ls-files", "site"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.split()
        for name in staged_assets():
            self.assertNotIn(f"site/{name}", tracked, f"site/{name} is staged at deploy time; do not commit a copy")

    def test_every_relative_reference_is_served(self) -> None:
        staged = staged_assets()
        for page in site_pages():
            html = page.read_text(encoding="utf-8")
            for target in set(REFERENCE.findall(html)):
                if not target or re.match(r"^(?:[a-z]+:)?//", target) or target.startswith("mailto:"):
                    continue
                with self.subTest(page=page.relative_to(ROOT).as_posix(), target=target):
                    resolved = (page.parent / target).resolve()
                    if target.endswith("/"):
                        resolved = resolved / "index.html"
                    relative = resolved.relative_to(SITE.resolve()).as_posix()
                    self.assertTrue(resolved.is_file() or relative in staged, f"{target} is neither committed nor staged")

    def test_nothing_loads_remotely(self) -> None:
        for page in site_pages():
            html = page.read_text(encoding="utf-8")
            with self.subTest(page=page.relative_to(ROOT).as_posix()):
                self.assertIsNone(REMOTE_LOAD.search(html), "runtime assets must be first-party")
        css = (SITE / "site.css").read_text(encoding="utf-8")
        self.assertIsNone(FONT_IMPORT.search(css), "the stylesheet must not import remote fonts or styles")

    def test_canonical_social_and_sitemap_agree(self) -> None:
        pages = site_pages()
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        listed = sorted(re.findall(r"<loc>([^<]+)</loc>", sitemap))
        self.assertEqual(listed, sorted(page_url(page) for page in pages))
        robots = (SITE / "robots.txt").read_text(encoding="utf-8")
        self.assertIn(f"Sitemap: {ORIGIN}sitemap.xml", robots)
        og_size = png_size(staged_assets()["og.png"])
        for page in pages:
            html = page.read_text(encoding="utf-8")
            meta = dict(META.findall(html))
            with self.subTest(page=page.relative_to(ROOT).as_posix()):
                self.assertEqual(CANONICAL.findall(html), [page_url(page)])
                self.assertEqual(meta.get("og:url"), page_url(page))
                self.assertEqual(meta.get("og:image"), f"{ORIGIN}og.png")
                self.assertEqual((int(meta["og:image:width"]), int(meta["og:image:height"])), og_size)
                self.assertEqual(meta.get("twitter:card"), "summary_large_image")


if __name__ == "__main__":
    unittest.main()
