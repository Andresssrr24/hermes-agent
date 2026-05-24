#!/usr/bin/env python3
"""Generate sanitized public copies of private contract templates.

Replaces client identifiers with placeholders. Professional data and
legal text are left untouched."""

from __future__ import annotations

import sys
from pathlib import Path

import fitz

REPLACEMENTS: dict[str, list[tuple[str, str]]] = {
    "650.pdf": [
        ("CONSTRUCTORA REYES RAMIREZ", "[Nombre de la Empresa]"),
        ("Constructora Reyes Ramirez", "[Nombre de la Empresa]"),
        ("inmobiliario", "[Sector]"),
        ("en Rep\u00fablica Dominicana", "en [Pa\u00eds]"),
        ("131725651", "[Documento Empresa]"),
        ("AVENIDA LAS PALMAS, NO. 46", "[Direcci\u00f3n Empresa]"),
        ("Katherine Ramirez", "[Nombre del Propietario]"),
        ("001-1530949-4", "[Documento Identidad]"),
        ("$500 USD", "[Presupuesto Campa\u00f1as]"),
        ("+1 849 918 1620", "[WhatsApp Propietario]"),
        ("constructorareyesramirez@gmail.com", "[Correo Electr\u00f3nico]"),
    ],
    "1500.pdf": [
        ("DOMARQ SRL Y REPUBLIC REALTORS", "[Nombre de la Empresa]"),
        ("JONATHAN J DIAZ LIZ", "[Nombre del Propietario]"),
        ("1-32-81836-9", "[Documento Empresa]"),
        ("40240164828", "[Documento Identidad]"),
    ],
    "2500.pdf": [
        ("NADER ASSET MANAGEMENT SRL", "[Nombre de la Empresa]"),
        ("GEORGE ALEXANDER NADER NICOLAS", "[Nombre del Propietario]"),
        ("SR. GEORGE", "[Nombre del Propietario]"),
        ("130747083", "[Documento Empresa]"),
        (
            "00116507039, EN ADELANTE EL CLIENTE",
            "[Documento Identidad], EN ADELANTE EL CLIENTE",
        ),
    ],
}


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


def main() -> int:
    skill_public = Path(__file__).resolve().parents[1]
    skill_private = Path(__file__).resolve().parents[2] / "contract_skill"

    templates_private = skill_private / "templates"
    templates_public = skill_public / "templates"

    if not templates_private.is_dir():
        print(f"error: private templates not found at {templates_private}", file=sys.stderr)
        return 1

    for filename, pairs in REPLACEMENTS.items():
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
