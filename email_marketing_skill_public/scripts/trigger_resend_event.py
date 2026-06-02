#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from campaign_common import add_config_arg, load_config


def send_event(api_key: str, event_name: str, email: str, nombre: str) -> dict:
    payload = {
        "event": event_name,
        "email": email,
        "payload": {
            "NOMBRE": nombre,
            "CORREO": email,
        },
    }
    request = Request(
        "https://api.resend.com/events/send",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "hermes-email-marketing-skill/0.1",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Resend API error {exc.code}: {detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger a Resend automation event for a test recipient.")
    add_config_arg(parser)
    parser.add_argument("--email", required=True, help="Recipient email for the event")
    parser.add_argument("--nombre", required=True, help="Recipient name for NOMBRE")
    parser.add_argument("--test-recipient", action="store_true", help="Required safety confirmation for sending the event")
    args = parser.parse_args()

    if not args.test_recipient:
        raise SystemExit("Refusing to send event without --test-recipient")

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise SystemExit("RESEND_API_KEY is required")

    config = load_config(Path(args.config).expanduser().resolve())
    result = send_event(api_key, config["event_name"], args.email, args.nombre)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
