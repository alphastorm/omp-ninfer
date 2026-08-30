#!/usr/bin/env python3
"""Render the editable HTML brand sources into deterministic PNG assets."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
TARGETS = {
    "banner": (1280, 320, 2),
    "benchmarks": (1240, 360, 2),
    "architecture": (1240, 420, 2),
    "og": (1280, 640, 1),
}


def chrome_path(explicit: str | None) -> str:
    candidates = [
        explicit,
        os.environ.get("CHROME"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit("Chrome/Chromium not found; pass --chrome or set CHROME")


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"not a PNG: {path}")
        length = struct.unpack(">I", stream.read(4))[0]
        kind = stream.read(4)
        if kind != b"IHDR" or length < 8:
            raise RuntimeError(f"missing PNG IHDR: {path}")
        return struct.unpack(">II", stream.read(8))


def render(chrome: str, name: str, check: bool) -> None:
    width, height, scale = TARGETS[name]
    source = ASSETS / f"{name}.html"
    destination = ASSETS / f"{name}.png"
    with tempfile.TemporaryDirectory(prefix=f"omp-ninfer-{name}-") as directory:
        output = Path(directory) / f"{name}.png"
        command = [
            chrome,
            "--headless=new",
            "--hide-scrollbars",
            "--disable-gpu",
            f"--force-device-scale-factor={scale}",
            f"--window-size={width},{height}",
            "--virtual-time-budget=5000",
            f"--screenshot={output}",
            source.resolve().as_uri(),
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        expected = (width * scale, height * scale)
        observed = png_dimensions(output)
        if observed != expected:
            raise RuntimeError(f"{name}: expected {expected}, observed {observed}")
        if check:
            if not destination.is_file() or destination.read_bytes() != output.read_bytes():
                raise RuntimeError(f"{name}: committed PNG is stale")
        else:
            os.replace(output, destination)
        print(f"{name}: {observed[0]}x{observed[1]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", choices=sorted(TARGETS))
    parser.add_argument("--chrome")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    chrome = chrome_path(args.chrome)
    for name in args.names or TARGETS:
        render(chrome, name, args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
