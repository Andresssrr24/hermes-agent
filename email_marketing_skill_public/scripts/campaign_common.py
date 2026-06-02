import argparse
import base64
import html
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EXPECTED_SOCIAL_KEYS = ("instagram", "linkedin", "facebook", "whatsapp")
EXPECTED_VARIABLES = ("NOMBRE", "CORREO")
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LEGACY_STRINGS = (
    "Private Client",
    "private-client.example",
    "legacy_brand",
    "legacy-domain.example",
)


class CampaignError(ValueError):
    pass


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (config_path.parent / path).resolve()


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path).expanduser().resolve()
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    validate_config(config, path)
    return config


def is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_config(config: dict[str, Any], config_path: Path | None = None) -> None:
    required_strings = (
        "company_name",
        "from_email",
        "reply_to",
        "calendly_url",
        "logo_path",
        "primary_color",
        "secondary_color",
        "language",
        "event_name",
    )
    missing = [key for key in required_strings if not str(config.get(key, "")).strip()]
    if missing:
        raise CampaignError(f"Missing required config field(s): {', '.join(missing)}")

    for key in ("from_email", "reply_to"):
        if not EMAIL_RE.match(str(config[key])):
            raise CampaignError(f"{key} must be a valid email address")

    if not is_https_url(str(config["calendly_url"])):
        raise CampaignError("calendly_url must be an HTTPS URL")

    for key in ("primary_color", "secondary_color"):
        if not HEX_COLOR_RE.match(str(config[key])):
            raise CampaignError(f"{key} must be a #RRGGBB hex color")

    titles = config.get("template_titles")
    if not isinstance(titles, list) or len(titles) != 10 or not all(str(t).strip() for t in titles):
        raise CampaignError("template_titles must contain exactly 10 non-empty titles")

    social_urls = config.get("social_urls")
    if not isinstance(social_urls, dict):
        raise CampaignError("social_urls must be an object")
    missing_social = [key for key in EXPECTED_SOCIAL_KEYS if key not in social_urls]
    if missing_social:
        raise CampaignError(f"social_urls missing key(s): {', '.join(missing_social)}")
    for key in EXPECTED_SOCIAL_KEYS:
        value = str(social_urls.get(key) or "")
        if value and not is_https_url(value):
            raise CampaignError(f"social_urls.{key} must be empty or an HTTPS URL")

    variables = config.get("prospect_variables")
    if variables != list(EXPECTED_VARIABLES):
        raise CampaignError('prospect_variables must be exactly ["NOMBRE", "CORREO"]')

    if config_path is not None:
        logo_path = resolve_path(config_path, str(config["logo_path"]))
        if not logo_path.exists():
            raise CampaignError(f"logo_path does not exist: {logo_path}")


def read_logo_html(config: dict[str, Any], config_path: Path) -> str:
    logo_path = resolve_path(config_path, str(config["logo_path"]))
    suffix = logo_path.suffix.lower()
    if suffix == ".svg":
        svg = logo_path.read_text(encoding="utf-8").strip()
        return svg.replace("<svg", '<svg class="email-logo" style="width:220px;height:auto;display:block;margin:0 auto;"', 1)
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else f"image/{suffix[1:]}"
        encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        alt = html.escape(str(config["company_name"]))
        return f'<img class="email-logo" src="data:{mime};base64,{encoded}" alt="{alt}" style="width:220px;height:auto;display:block;margin:0 auto;">'
    raise CampaignError("logo_path must point to an SVG, PNG, JPG, GIF, or WEBP file")


def render_social_html(config: dict[str, Any]) -> str:
    links = []
    icons = {
        "instagram": '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="5"/><circle cx="17.5" cy="6.5" r="1.4" fill="#ffffff" stroke="none"/></svg>',
        "linkedin": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#ffffff" aria-hidden="true"><path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.55V9h3.57v11.45zM22.23 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.23 0z"/></svg>',
        "facebook": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#ffffff" aria-hidden="true"><path d="M24 12.07C24 5.4 18.63 0 12 0S0 5.4 0 12.07c0 6.02 4.39 11.01 10.13 11.93v-8.44H7.08v-3.49h3.05V9.41c0-3.02 1.79-4.69 4.53-4.69 1.31 0 2.69.24 2.69.24v2.97h-1.51c-1.49 0-1.96.93-1.96 1.88v2.26h3.33l-.53 3.49h-2.8V24C19.61 23.08 24 18.09 24 12.07z"/></svg>',
        "whatsapp": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#ffffff" aria-hidden="true"><path d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.16-.17.2-.35.22-.64.08-.3-.15-1.26-.46-2.39-1.48-.88-.79-1.48-1.76-1.65-2.06-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.03-.52-.07-.15-.67-1.61-.92-2.21-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.21 3.07c.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.69.63.71.23 1.36.2 1.87.12.57-.09 1.76-.72 2.01-1.41.25-.69.25-1.29.17-1.41-.07-.12-.27-.2-.57-.35zM12.05 21.79h-.01a9.87 9.87 0 0 1-5.03-1.38l-.36-.21-3.74.98 1-3.65-.24-.37a9.86 9.86 0 0 1-1.51-5.26C2.16 6.45 6.59 2.01 12.05 2.01c2.64 0 5.12 1.03 6.99 2.9a9.83 9.83 0 0 1 2.89 6.99c0 5.45-4.44 9.89-9.88 9.89zM20.46 3.49A11.82 11.82 0 0 0 12.05 0C5.49 0 .16 5.34.16 11.89c0 2.1.55 4.14 1.59 5.95L.06 24l6.31-1.65a11.88 11.88 0 0 0 5.68 1.45h.01c6.55 0 11.89-5.34 11.89-11.89 0-3.18-1.24-6.17-3.49-8.42z"/></svg>',
    }
    labels = {"instagram": "Instagram", "linkedin": "LinkedIn", "facebook": "Facebook", "whatsapp": "WhatsApp"}
    for key in EXPECTED_SOCIAL_KEYS:
        url = str(config["social_urls"].get(key) or "").strip()
        if not url:
            continue
        label = labels[key]
        links.append(
            '<td style="padding:0 5px;">'
            f'<a href="{html.escape(url, quote=True)}" target="_blank" '
            f'aria-label="{label}" title="{label}" '
            f'style="display:inline-block;width:38px;height:38px;line-height:38px;background-color:{html.escape(config["primary_color"])};border-radius:999px;text-align:center;text-decoration:none;">'
            f'{icons[key]}</a></td>'
        )
    if not links:
        return ""
    return (
        '<p style="font-size:13px;color:#888888;margin:0 0 14px 0;text-transform:uppercase;letter-spacing:1.5px;">Siguenos</p>'
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;"><tr>'
        + "".join(links)
        + "</tr></table>"
    )


def paragraph(text: str) -> str:
    return f'<p style="font-size:16px;color:#444444;line-height:1.7;margin:0 0 18px 0;" class="email-text">{text}</p>'


def default_body_html(config: dict[str, Any], index: int, title: str) -> str:
    company = html.escape(str(config["company_name"]))
    title_escaped = html.escape(title)
    sequences = [
        "identificar los puntos donde se pierden oportunidades antes de que el equipo pueda darles seguimiento.",
        "ordenar el proceso comercial para que cada contacto reciba una respuesta clara y oportuna.",
        "mantener conversaciones activas sin depender de recordatorios manuales o informacion dispersa.",
        "dar visibilidad al estado real de cada oportunidad y a los proximos pasos del equipo.",
        "convertir interes inicial en reuniones calificadas con un proceso mas consistente.",
        "detectar fricciones operativas que reducen la conversion sin que el equipo las note a tiempo.",
        "medir la consistencia del seguimiento y mejorar la velocidad de respuesta.",
        "aplicar mejoras simples que hacen mas predecible el avance de los prospectos.",
        "priorizar acciones comerciales que tienen impacto directo en conversion y agenda.",
        "dar el siguiente paso y revisar juntos como mejorar el proceso actual.",
    ]
    return "".join(
        [
            paragraph(f"Hola, {{{{{{NOMBRE}}}}}}."),
            paragraph(f"En este correo queremos hablar de <strong style=\"color:{html.escape(config['primary_color'])};\">{title_escaped}</strong> y de como puede ayudar a mejorar la operacion comercial."),
            paragraph(f"Para {company}, el objetivo es {sequences[index - 1]}"),
            paragraph("Si este tema es relevante para tu equipo, agenda una llamada y revisamos el caso con contexto real."),
            paragraph("Este mensaje fue preparado para {{{CORREO}}} como parte de una secuencia de seguimiento solicitada."),
        ]
    )


def build_automation(config: dict[str, Any], template_ids: list[str] | None = None) -> dict[str, Any]:
    template_ids = template_ids or [f"TEMPLATE_ID_{i:02d}" for i in range(1, 11)]
    if len(template_ids) != 10:
        raise CampaignError("Exactly 10 template IDs are required")

    steps: list[dict[str, Any]] = [
        {"key": "start", "type": "trigger", "config": {"event_name": config["event_name"]}}
    ]
    connections: list[dict[str, str]] = []
    for index in range(10):
        number = index + 1
        email_key = f"email{number:02d}"
        delay_key = f"delay{number:02d}"
        steps.append(
            {
                "key": email_key,
                "type": "send_email",
                "config": {
                    "template": {"id": template_ids[index]},
                    "subject": config["template_titles"][index],
                    "from": f'{config["company_name"]} <{config["from_email"]}>',
                    "reply_to": config["reply_to"],
                },
            }
        )
        connections.append({"from": "start" if index == 0 else f"delay{index:02d}", "to": email_key, "type": "default"})
        if index < 9:
            steps.append({"key": delay_key, "type": "delay", "config": {"duration": "3 days"}})
            connections.append({"from": email_key, "to": delay_key, "type": "default"})

    return {
        "name": f'{config["company_name"]} - Drip Campaign (10 emails)',
        "status": "disabled",
        "event_name": config["event_name"],
        "steps": steps,
        "connections": connections,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_config_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", required=True, help="Path to campaign.config.json")
