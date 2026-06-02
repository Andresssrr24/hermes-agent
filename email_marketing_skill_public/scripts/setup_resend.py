#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from campaign_common import EXPECTED_VARIABLES, add_config_arg, build_automation, load_config, write_json


API_BASE = "https://api.resend.com"


def api_request(api_key: str, path: str, method: str = "POST", body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "hermes-email-marketing-skill/0.1",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Resend API error {exc.code}: {detail}") from exc


def setup_resend(config_path: Path, apply: bool = False, force: bool = False) -> dict[str, Any]:
    config = load_config(config_path)
    emails_dir = config_path.parent / "emails"
    email_files = [emails_dir / f"email-{index:02d}.html" for index in range(1, 11)]
    missing = [str(path) for path in email_files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing generated email files: {', '.join(missing)}")

    state_path = config_path.parent / "resend.generated.json"
    if state_path.exists() and apply and not force:
        raise RuntimeError(f"{state_path} already exists. Pass --force to create new Resend resources.")

    planned_templates = [
        {
            "name": f'{config["company_name"]} - Email {index:02d}',
            "subject": config["template_titles"][index - 1],
            "from": f'{config["company_name"]} <{config["from_email"]}>',
            "reply_to": config["reply_to"],
            "html_path": str(path),
            "variables": [{"key": key, "type": "string"} for key in EXPECTED_VARIABLES],
        }
        for index, path in enumerate(email_files, start=1)
    ]

    if not apply:
        automation = build_automation(config)
        return {
            "mode": "dry-run",
            "templates": planned_templates,
            "automation": automation,
            "message": "No network calls were made.",
        }

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is required for --apply")

    template_ids: list[str] = []
    created_templates = []
    for planned in planned_templates:
        html_body = Path(planned["html_path"]).read_text(encoding="utf-8")
        payload = {
            "name": planned["name"],
            "html": html_body,
            "subject": planned["subject"],
            "from": planned["from"],
            "reply_to": planned["reply_to"],
            "variables": planned["variables"],
        }
        template = api_request(api_key, "/templates", "POST", payload)
        template_id = template["id"]
        api_request(api_key, f"/templates/{template_id}/publish", "POST")
        template_ids.append(template_id)
        created_templates.append({**planned, "id": template_id})

    automation = build_automation(config, template_ids)
    automation_payload = {
        "name": automation["name"],
        "status": "disabled",
        "steps": automation["steps"],
        "connections": automation["connections"],
    }
    created_automation = api_request(api_key, "/automations", "POST", automation_payload)
    state = {
        "templates": created_templates,
        "automation": {**automation, "id": created_automation.get("id")},
    }
    write_json(state_path, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Resend templates and a disabled automation.")
    add_config_arg(parser)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print planned actions without network calls.")
    mode.add_argument("--apply", action="store_true", help="Create templates and automation in Resend.")
    parser.add_argument("--force", action="store_true", help="Allow creating new resources when resend.generated.json exists.")
    args = parser.parse_args()
    config_path = Path(args.config).expanduser().resolve()
    result = setup_resend(config_path, apply=args.apply, force=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
