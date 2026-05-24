#!/usr/bin/env python3
"""Create coordinate-grid copies of contract templates for field calibration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def calibrate(plan: str, output: Path | None = None, spacing: int = 50) -> Path:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Install PyMuPDF first: python3 -m pip install pymupdf") from exc

    if plan not in {"650", "1500", "2500"}:
        raise ValueError("plan must be one of 650, 1500, or 2500")

    skill_dir = _skill_dir()
    template_path = skill_dir / "templates" / f"{plan}.pdf"
    if output is None:
        output = skill_dir / "output" / f"calibration-grid-{plan}.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(template_path)
    for page_number, page in enumerate(doc, start=1):
        width = int(page.rect.width)
        height = int(page.rect.height)
        for x in range(0, width + 1, spacing):
            page.draw_line((x, 0), (x, height), color=(0.7, 0.7, 0.7), width=0.3, overlay=True)
            page.insert_text((x + 2, 12), str(x), fontsize=6, color=(0.1, 0.1, 0.1), overlay=True)
        for y in range(0, height + 1, spacing):
            page.draw_line((0, y), (width, y), color=(0.7, 0.7, 0.7), width=0.3, overlay=True)
            page.insert_text((2, y + 8), str(y), fontsize=6, color=(0.1, 0.1, 0.1), overlay=True)
        page.insert_text((width - 70, 14), f"page {page_number}", fontsize=8, overlay=True)
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a PDF coordinate grid for calibration.")
    parser.add_argument("--plan", required=True, choices=["650", "1500", "2500"])
    parser.add_argument("--output")
    parser.add_argument("--spacing", type=int, default=50)
    args = parser.parse_args()
    try:
        output = calibrate(args.plan, Path(args.output) if args.output else None, args.spacing)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
