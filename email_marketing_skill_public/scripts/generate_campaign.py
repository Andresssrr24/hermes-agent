#!/usr/bin/env python3
import argparse
import html
from pathlib import Path

from campaign_common import (
    add_config_arg,
    build_automation,
    default_body_html,
    load_config,
    read_logo_html,
    render_social_html,
    skill_root,
    write_json,
)


def render_template(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def generate(config_path: Path, output_dir: Path | None = None) -> list[Path]:
    config = load_config(config_path)
    root = skill_root()
    output_dir = output_dir or (config_path.parent / "emails")
    output_dir.mkdir(parents=True, exist_ok=True)

    template = (root / "templates" / "email_base.html").read_text(encoding="utf-8")
    logo_html = read_logo_html(config, config_path)
    social_html = render_social_html(config)
    language = str(config.get("language") or "es")
    labels = {
        "es": {
            "cta": "Agendar llamada",
            "signoff": "Un saludo,",
            "unsubscribe": "Cancelar suscripcion",
            "footer": "Secuencia de seguimiento comercial",
        },
        "en": {
            "cta": "Schedule a call",
            "signoff": "Best,",
            "unsubscribe": "Unsubscribe",
            "footer": "Commercial follow-up sequence",
        },
    }.get(language, {})
    labels = labels or {
        "cta": "Agendar llamada",
        "signoff": "Un saludo,",
        "unsubscribe": "Cancelar suscripcion",
        "footer": "Secuencia de seguimiento comercial",
    }

    written: list[Path] = []
    for index, title in enumerate(config["template_titles"], start=1):
        body_html = default_body_html(config, index, title)
        replacements = {
            "LANG": html.escape(language),
            "TITLE": html.escape(f"Email {index:02d} - {config['company_name']}"),
            "PRIMARY_COLOR": html.escape(config["primary_color"]),
            "SECONDARY_COLOR": html.escape(config["secondary_color"]),
            "LOGO_HTML": logo_html,
            "HEADING": html.escape(title),
            "BODY_HTML": body_html,
            "CALENDLY_URL": html.escape(config["calendly_url"], quote=True),
            "CTA_LABEL": labels["cta"],
            "SIGNOFF": labels["signoff"],
            "COMPANY_NAME": html.escape(config["company_name"]),
            "SOCIAL_HTML": social_html,
            "UNSUBSCRIBE_LABEL": labels["unsubscribe"],
            "FOOTER_TEXT": labels["footer"],
        }
        html_out = render_template(template, replacements)
        out_path = output_dir / f"email-{index:02d}.html"
        out_path.write_text(html_out, encoding="utf-8")
        written.append(out_path)

    automation = build_automation(config)
    write_json(config_path.parent / "automation.generated.json", automation)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate branded email campaign templates.")
    add_config_arg(parser)
    parser.add_argument("--output-dir", help="Directory for generated emails. Defaults to ./emails next to config.")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else None
    written = generate(config_path, output_dir)
    print(f"Generated {len(written)} email templates")
    print(f"Generated automation: {config_path.parent / 'automation.generated.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
