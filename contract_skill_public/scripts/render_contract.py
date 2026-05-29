#!/usr/bin/env python3
"""Generate ready-to-sign company contracts from fixed PDF templates."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))
from normalize import normalize_form_data  # noqa: E402


REQUIRED_FIELDS = [
    "plan",
    "company_name",
    "company_sector",
    "company_whatsapp",
    "company_document",
    "owner_name",
    "owner_whatsapp",
    "owner_email",
    "owner_identity_document",
    "ad_budget_30_days_usd",
]

SPANISH_MONTHS = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}


def _skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "client"


def _parse_contract_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return date.today()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError("contract_date must use YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY")


def _spanish_date(value: date) -> str:
    return f"{value.day} DE {SPANISH_MONTHS[value.month]} DE {value.year}"


def _load_input(args: argparse.Namespace) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if args.input:
        data.update(_load_json(Path(args.input)))

    for field in REQUIRED_FIELDS:
        value = getattr(args, field, None)
        if value not in (None, ""):
            data[field] = value
    if args.contract_date:
        data["contract_date"] = args.contract_date

    data, warnings = normalize_form_data(data)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    contract_date = _parse_contract_date(data.get("contract_date"))
    data["contract_date"] = contract_date.isoformat()
    data["contract_date_es"] = _spanish_date(contract_date)
    data.setdefault("generated_date", date.today().isoformat())

    missing = [field for field in REQUIRED_FIELDS if not str(data.get(field, "")).strip()]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))
    return data


def _professional_values(config: dict[str, Any]) -> dict[str, str]:
    professional = config["professional"]
    address = str(professional.get("address", "")).strip()
    if not address or address == "CONFIGURE_COMPANY_ADDRESS":
        raise ValueError(
            "Set professional.address in references/plans.json before generating contracts."
        )
    return {
        "professional_company_name": professional["company_name"],
        "professional_dba": professional["dba"],
        "professional_brand_name": professional["brand_name"],
        "professional_representative_name": professional["representative_name"],
        "professional_representative_title": professional["representative_title"],
        "professional_representative_identity": professional["representative_identity"],
        "professional_ein": professional["ein"],
        "professional_address": address,
        "professional_whatsapp": professional.get("whatsapp", ""),
        "professional_email": professional.get("email", ""),
        "professional_signature_image": professional.get("signature_image", ""),
    }


def _format_line(template: str, values: dict[str, Any], uppercase: bool) -> str:
    line = template.format(**values)
    return line.upper() if uppercase else line


def _insert_text_run(page: Any, point: tuple[float, float], text: str, font_size: float, fontname: str) -> float:
    import fitz  # type: ignore[import-not-found]

    page.insert_text(
        point,
        text,
        fontsize=font_size,
        fontname=fontname,
        color=(0, 0, 0),
        overlay=True,
    )
    return fitz.get_text_length(text, fontname=fontname, fontsize=font_size)


def _resolve_asset_path(path_text: str, skill_dir: Path) -> Path | None:
    path_text = path_text.strip()
    if not path_text or path_text.startswith("CONFIGURE_"):
        return None
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = skill_dir / path
    return path if path.exists() else None


def _add_manual_blocks(doc: Any, blocks: list[dict[str, Any]], values: dict[str, Any]) -> None:
    import fitz  # type: ignore[import-not-found]

    for block in blocks:
        page = doc[int(block["page"])]
        rect = fitz.Rect(*block["rect"])
        if block.get("redact", True):
            redact_rect = fitz.Rect(*block.get("redact_rect", block["rect"]))
            page.add_redact_annot(redact_rect, fill=(1, 1, 1))
            page.apply_redactions()

        for erase_rect in block.get("erase_rects", []):
            page.draw_rect(fitz.Rect(*erase_rect), color=(1, 1, 1), fill=(1, 1, 1), overlay=True)

        for line in block.get("draw_lines", []):
            width = float(line[4]) if len(line) > 4 else 1.0
            page.draw_line((line[0], line[1]), (line[2], line[3]), color=(0.45, 0.45, 0.45), width=width, overlay=True)

        for image in block.get("images", []):
            image_path_text = _format_line(str(image.get("path", "")), values, False)
            image_path = _resolve_asset_path(image_path_text, _skill_dir())
            if image_path:
                page.insert_image(fitz.Rect(*image["rect"]), filename=str(image_path), overlay=True)

        insert_at = block.get("insert_at")
        if insert_at:
            x0, y0 = float(insert_at[0]), float(insert_at[1])
        else:
            x0, y0 = rect.x0, rect.y0
        font_size = float(block.get("font_size", 10))
        leading = float(block.get("leading", font_size + 3))
        fontname = str(block.get("fontname", "helv"))
        uppercase = bool(block.get("uppercase", False))
        if "runs" in block:
            x = x0
            y = y0 + leading
            for run in block["runs"]:
                text = _format_line(str(run["text"]), values, uppercase)
                run_font_size = float(run.get("font_size", font_size))
                run_fontname = str(run.get("fontname", fontname))
                x += _insert_text_run(page, (x, y), text, run_font_size, run_fontname)
            continue

        for index, line_template in enumerate(block.get("lines", [])):
            line = _format_line(line_template, values, uppercase)
            _insert_text_run(page, (x0, y0 + (index + 1) * leading), line, font_size, fontname)


def _search_replace(doc: Any, replacements: dict[str, str]) -> None:
    import fitz  # type: ignore[import-not-found]

    for page in doc:
        insertions = []
        for old, new in replacements.items():
            if not old or old == new:
                continue
            rects = page.search_for(old)
            for rect in rects:
                expanded = fitz.Rect(rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 1)
                page.add_redact_annot(expanded, fill=(1, 1, 1))
                insertions.append((rect, new))
        if insertions:
            page.apply_redactions()
        for rect, new in insertions:
            page.insert_text(
                (rect.x0, rect.y1 - 2),
                new,
                fontsize=max(7, rect.height * 0.75),
                fontname="helv",
                color=(0, 0, 0),
                overlay=True,
            )


def render_contract(data: dict[str, Any], output: Path | None = None) -> Path:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Install PyMuPDF first: python3 -m pip install pymupdf") from exc

    skill_dir = _skill_dir()
    plans_config = _load_json(skill_dir / "references" / "plans.json")
    fields_config = _load_json(skill_dir / "references" / "fields.json")
    plan = data["plan"]
    plan_config = plans_config["plans"][plan]
    template_path = skill_dir / plan_config["template"]
    if not template_path.exists():
        raise FileNotFoundError(f"template not found: {template_path}")

    values = {**data, **_professional_values(plans_config)}
    doc = fitz.open(template_path)
    blocks = fields_config["plans"][plan].get("manual_blocks", [])
    _add_manual_blocks(doc, blocks, values)

    if output is None:
        out_dir = skill_dir / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = _slugify(data["company_name"])
        output = out_dir / f"{plan_config['output_prefix']}-{slug}-{plan}-{data['generated_date']}.pdf"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output


def _upload_drive_result(
    output: Path,
    folder_id: str | None = None,
    share_email: str | None = None,
) -> dict[str, Any] | None:
    config = _load_json(_skill_dir() / "references" / "plans.json")
    drive_config = dict(config.get("google_drive") or {})
    if not drive_config.get("upload_automatically", False) and not folder_id:
        return None

    try:
        from upload_contract_to_drive import upload_contract

        return upload_contract(output, name=output.name, folder_id=folder_id, share_email=share_email, config=config)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a company contract PDF.")
    parser.add_argument("--input", help="JSON file with contract form fields.")
    parser.add_argument("--output", help="Output PDF path. Defaults to skill output directory.")
    parser.add_argument("--contract-date", help="Contract date as YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY.")
    parser.add_argument("--no-drive-upload", action="store_true", help="Generate only the local PDF.")
    parser.add_argument("--drive-folder-id", default="", help="Override configured Google Drive folder ID.")
    parser.add_argument("--share-email", default="", help="Email address to share uploaded PDFs with when share_type=user.")
    for field in REQUIRED_FIELDS:
        parser.add_argument(f"--{field.replace('_', '-')}", dest=field)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        data = _load_input(args)
        output = render_contract(data, Path(args.output) if args.output else None)
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    result: dict[str, Any] = {"success": True, "output": str(output)}
    if not args.no_drive_upload:
        drive_result = _upload_drive_result(
            output,
            folder_id=args.drive_folder_id or None,
            share_email=args.share_email or data.get("owner_email"),
        )
        if drive_result is not None:
            result["drive"] = drive_result
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
