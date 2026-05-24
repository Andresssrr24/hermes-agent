#!/usr/bin/env python3
"""Upload generated contract PDFs to Google Drive."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _google_api_script() -> Path:
    configured = os.getenv("GOOGLE_WORKSPACE_API_SCRIPT")
    if configured:
        path = Path(configured).expanduser()
        if path.exists():
            return path

    hermes_home = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    candidates = [
        Path(__file__).resolve().parents[2]
        / "skills"
        / "productivity"
        / "google-workspace"
        / "scripts"
        / "google_api.py",
        Path.cwd() / "skills" / "productivity" / "google-workspace" / "scripts" / "google_api.py",
        hermes_home / "skills" / "productivity" / "google-workspace" / "scripts" / "google_api.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Google Workspace API script not found. Install the google-workspace skill "
        "or set GOOGLE_WORKSPACE_API_SCRIPT."
    )


def _run_google_api(args: list[str]) -> dict[str, Any]:
    script = _google_api_script()
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip() or "Google API command failed"
        raise RuntimeError(error)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Google API returned non-JSON output: {completed.stdout.strip()}") from exc


def _drive_config(config: dict[str, Any]) -> dict[str, Any]:
    return dict(config.get("google_drive") or {})


def upload_contract(
    pdf: Path,
    name: str | None = None,
    folder_id: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pdf = pdf.expanduser().resolve()
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf}")

    if config is None:
        config = _load_json(_skill_dir() / "references" / "plans.json")
    drive = _drive_config(config)
    resolved_folder_id = (folder_id or drive.get("folder_id") or "").strip()
    if not resolved_folder_id or resolved_folder_id == "CONFIGURE_GOOGLE_DRIVE_FOLDER_ID":
        raise ValueError("Set google_drive.folder_id in references/plans.json before uploading.")

    upload_args = ["drive", "upload", str(pdf), "--name", name or pdf.name, "--parent", resolved_folder_id]
    upload_result = _run_google_api(upload_args)
    file_id = upload_result.get("id")
    if not file_id:
        raise RuntimeError(f"Drive upload did not return a file id: {upload_result}")

    share_type = str(drive.get("share_type") or "anyone")
    share_role = str(drive.get("share_role") or "reader")
    share_result = _run_google_api(
        ["drive", "share", file_id, "--type", share_type, "--role", share_role]
    )

    return {
        "success": True,
        "file_id": file_id,
        "name": upload_result.get("name") or name or pdf.name,
        "webViewLink": upload_result.get("webViewLink", ""),
        "shared": True,
        "share": share_result,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload a generated contract PDF to Google Drive.")
    parser.add_argument("--pdf", required=True, help="Local PDF path to upload.")
    parser.add_argument("--name", default="", help="Drive file name. Defaults to the PDF file name.")
    parser.add_argument("--folder-id", default="", help="Override configured Drive folder ID.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = upload_contract(
            Path(args.pdf),
            name=args.name or None,
            folder_id=args.folder_id or None,
        )
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
