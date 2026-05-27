#!/usr/bin/env python3
"""Generate sanitized public copies of private contract templates.

Replacement rules are intentionally loaded from an external JSON file so
private client identifiers do not need to be committed to this public package.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

import fitz

DEFAULT_RULES_PATH = Path("sanitize-rules.private.json")


def _sanitize_pdf(
    private_path: Path,
    output_path: Path,
    replacements: list[tuple[str, str]],
) -> None:
    doc = fitz.open(private_path)
    for old, new in replacements:
        for page in doc:
            rects = page.search_for(old)
            for rect in rects:
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
                fontsize = max(7, rect.height * 0.75)
                page.insert_text(
                    (rect.x0, rect.y1 - 2),
                    new,
                    fontsize=fontsize,
                    fontname="helv",
                    color=(0, 0, 0),
                )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


def _load_replacements(path: Path) -> dict[str, list[tuple[str, str]]]:
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    replacements: dict[str, list[tuple[str, str]]] = {}
    for filename, pairs in raw.items():
        replacements[str(filename)] = [
            (str(pair["old"]), str(pair["new"]))
            for pair in pairs
            if str(pair.get("old", "")).strip()
        ]
    return replacements


def main() -> int:
    skill_public = Path(__file__).resolve().parents[1]
    skill_private = Path(__file__).resolve().parents[2] / "contract_skill"
    rules_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_RULES_PATH

    templates_private = skill_private / "templates"
    templates_public = skill_public / "templates"

    if not rules_path.exists():
        print(f"error: replacement rules not found: {rules_path}", file=sys.stderr)
        print("Create a private JSON rules file and do not commit it.", file=sys.stderr)
        return 1

    if not templates_private.is_dir():
        print(f"error: private templates not found at {templates_private}", file=sys.stderr)
        return 1

    for filename, pairs in _load_replacements(rules_path).items():
        src = templates_private / filename
        dst = templates_public / filename
        if not src.exists():
            print(f"error: private template missing: {src}", file=sys.stderr)
            return 1

        print(f"Sanitizing {filename} ...")
        _sanitize_pdf(src, dst, pairs)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
