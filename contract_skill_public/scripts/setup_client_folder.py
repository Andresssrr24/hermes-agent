#!/usr/bin/env python3
"""Create a Google Drive folder for a client and send an email with the folder link."""

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

    try:
        config_path = _skill_dir() / "references" / "plans.json"
        if config_path.exists():
            config = _load_json(config_path)
            api_script = config.get("google_api_script")
            if api_script:
                path = Path(api_script).expanduser()
                if path.exists():
                    return path
    except Exception:
        pass

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


def _client_folder_config(config: dict[str, Any]) -> dict[str, Any]:
    return dict(config.get("client_folder") or {})


def _resolve_placeholders(template: str, **kwargs: str) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def _share_args_for_config(
    cf: dict[str, Any],
    folder_id: str,
    owner_email: str,
) -> list[str]:
    share_type = str(cf.get("share_type") or "user").strip()
    share_role = str(cf.get("share_role") or "reader").strip()
    args = ["drive", "share", folder_id, "--type", share_type, "--role", share_role]

    if share_type == "user":
        email = str(cf.get("share_email") or owner_email or "").strip()
        if not email:
            raise ValueError("client_folder.share_type=user requires owner_email or client_folder.share_email")
        args.extend(["--email", email])
    elif share_type == "group":
        email = str(cf.get("share_email") or "").strip()
        if not email:
            raise ValueError("client_folder.share_type=group requires client_folder.share_email")
        args.extend(["--email", email])
    elif share_type == "domain":
        domain = str(cf.get("share_domain") or "").strip()
        if not domain:
            raise ValueError("client_folder.share_type=domain requires client_folder.share_domain")
        args.extend(["--domain", domain])
    elif share_type == "anyone":
        if cf.get("allow_public_link") is not True:
            raise ValueError("client_folder.share_type=anyone requires allow_public_link=true")
    else:
        raise ValueError("client_folder.share_type must be user, group, domain, or anyone")

    return args


def setup_client_folder(
    company_name: str,
    owner_name: str,
    owner_email: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if config is None:
        config = _load_json(_skill_dir() / "references" / "plans.json")

    cf = _client_folder_config(config)
    if not cf.get("enabled"):
        return {"success": True, "skipped": True, "reason": "client_folder.enabled is false"}

    parent_folder_id = str(cf.get("parent_folder_id") or "").strip()
    if not parent_folder_id or parent_folder_id.startswith("CONFIGURE_"):
        raise ValueError("Set client_folder.parent_folder_id in references/plans.json")
    share_args = _share_args_for_config(cf, "PENDING_FOLDER_ID", owner_email)

    folder_name = f"MATERIAL {company_name}"
    create_result = _run_google_api(
        ["drive", "create-folder", folder_name, "--parent", parent_folder_id]
    )
    folder_id = create_result.get("id")
    if not folder_id:
        raise RuntimeError(f"Drive folder creation did not return an id: {create_result}")
    folder_link = create_result.get("webViewLink", "")

    share_args[2] = folder_id
    share_result = _run_google_api(share_args)

    email_sent = False
    if cf.get("send_email", False) and owner_email:
        subject = str(cf.get("email_subject") or "Your Growth Estate Documents Folder")
        body_template = str(cf.get("email_body_template") or "Your Google Drive folder link: {folder_link}")
        body = _resolve_placeholders(
            body_template,
            owner_name=owner_name or "Valued Client",
            company_name=company_name,
            folder_link=folder_link,
        )
        gmail_args = [
            "gmail", "send",
            "--to", owner_email,
            "--subject", subject,
            "--body", body,
        ]
        email_from = str(cf.get("email_from") or "").strip()
        if email_from:
            gmail_args.extend(["--from", email_from])
        _run_google_api(gmail_args)
        email_sent = True

    return {
        "success": True,
        "folder_id": folder_id,
        "folder_name": folder_name,
        "folder_link": folder_link,
        "share": share_result,
        "email_sent": email_sent,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a Google Drive folder for a client and optionally email the link.")
    parser.add_argument("--company-name", required=True, help="Client company name.")
    parser.add_argument("--owner-name", required=True, help="Client owner name.")
    parser.add_argument("--owner-email", required=True, help="Client owner email address.")
    parser.add_argument("--no-email", action="store_true", help="Create folder without sending email.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load_json(_skill_dir() / "references" / "plans.json")
        if args.no_email:
            config.setdefault("client_folder", {})["send_email"] = False
        result = setup_client_folder(
            company_name=args.company_name,
            owner_name=args.owner_name,
            owner_email=args.owner_email,
            config=config,
        )
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
