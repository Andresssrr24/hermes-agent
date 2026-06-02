#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from campaign_common import EXPECTED_SOCIAL_KEYS, LEGACY_STRINGS, add_config_arg, load_config


class VerificationError(AssertionError):
    pass


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def verify(config_path: Path, emails_dir: Path | None = None) -> list[str]:
    config = load_config(config_path)
    errors: list[str] = []
    emails_dir = emails_dir or (config_path.parent / "emails")
    files = sorted(emails_dir.glob("email-*.html"))
    if len(files) != 10:
        fail(errors, f"Expected 10 email files, found {len(files)} in {emails_dir}")

    for path in files:
        text = path.read_text(encoding="utf-8")
        for legacy in LEGACY_STRINGS:
            if legacy in text:
                fail(errors, f"{path.name} contains legacy string: {legacy}")
        if config["calendly_url"] not in text:
            fail(errors, f"{path.name} is missing calendly_url")
        if "{{{RESEND_UNSUBSCRIBE_URL}}}" not in text:
            fail(errors, f"{path.name} is missing RESEND_UNSUBSCRIBE_URL")
        if "{{{NOMBRE}}}" not in text:
            fail(errors, f"{path.name} is missing NOMBRE variable")
        if "{{{CORREO}}}" not in text:
            fail(errors, f"{path.name} is missing CORREO variable")
        for removed in ("{{{EMPRESA}}}", "{{{PROYECTO}}}"):
            if removed in text:
                fail(errors, f"{path.name} contains removed variable {removed}")
        for placeholder in ("CLIENT_NAME", "TODO", "{{TITLE}}", "{{CALENDLY_URL}}"):
            if placeholder in text:
                fail(errors, f"{path.name} contains unreplaced placeholder {placeholder}")
        if config["primary_color"] not in text:
            fail(errors, f"{path.name} is missing primary color")
        if config["secondary_color"] not in text:
            fail(errors, f"{path.name} is missing secondary color")
        for key in EXPECTED_SOCIAL_KEYS:
            url = str(config["social_urls"].get(key) or "")
            if url and url not in text:
                fail(errors, f"{path.name} is missing configured social URL: {key}")
            if not url and f">{key.title()}<" in text:
                fail(errors, f"{path.name} renders empty social URL: {key}")

    automation_path = config_path.parent / "automation.generated.json"
    if not automation_path.exists():
        fail(errors, "automation.generated.json does not exist")
    else:
        automation = json.loads(automation_path.read_text(encoding="utf-8"))
        steps = automation.get("steps", [])
        connections = automation.get("connections", [])
        triggers = [s for s in steps if s.get("type") == "trigger"]
        emails = [s for s in steps if s.get("type") == "send_email"]
        delays = [s for s in steps if s.get("type") == "delay"]
        if len(triggers) != 1:
            fail(errors, f"Expected 1 trigger step, found {len(triggers)}")
        if len(emails) != 10:
            fail(errors, f"Expected 10 send_email steps, found {len(emails)}")
        if len(delays) != 9:
            fail(errors, f"Expected 9 delay steps, found {len(delays)}")
        for delay in delays:
            if delay.get("config", {}).get("duration") != "3 days":
                fail(errors, f"Delay {delay.get('key')} does not use duration '3 days'")
        expected_edges = [("start", "email01")]
        for index in range(1, 10):
            expected_edges.append((f"email{index:02d}", f"delay{index:02d}"))
            expected_edges.append((f"delay{index:02d}", f"email{index + 1:02d}"))
        actual_edges = {(c.get("from"), c.get("to")) for c in connections}
        for edge in expected_edges:
            if edge not in actual_edges:
                fail(errors, f"Missing automation edge {edge[0]} -> {edge[1]}")

    if errors:
        raise VerificationError("\n".join(errors))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify generated campaign templates and automation graph.")
    add_config_arg(parser)
    parser.add_argument("--emails-dir", help="Directory containing generated email HTML files.")
    args = parser.parse_args()
    config_path = Path(args.config).expanduser().resolve()
    emails_dir = Path(args.emails_dir).expanduser().resolve() if args.emails_dir else None
    files = verify(config_path, emails_dir)
    print(f"Verified {len(files)} email templates and automation graph")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
