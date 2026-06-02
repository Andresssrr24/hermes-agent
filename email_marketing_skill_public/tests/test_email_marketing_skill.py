import json
import sys
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from campaign_common import CampaignError, build_automation, load_config  # noqa: E402
from generate_campaign import generate  # noqa: E402
from setup_resend import setup_resend  # noqa: E402
from verify_campaign import verify  # noqa: E402


def write_config(tmp_path: Path, **overrides) -> Path:
    logo = tmp_path / "logo.svg"
    logo.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><text>Client</text></svg>',
        encoding="utf-8",
    )
    config = {
        "company_name": "Client Company",
        "from_email": "hello@clientdomain.com",
        "reply_to": "hello@clientdomain.com",
        "calendly_url": "https://calendly.com/client/30min",
        "logo_path": str(logo),
        "primary_color": "#3066b6",
        "secondary_color": "#1a3d6e",
        "language": "es",
        "event_name": "client_company.prospect.created",
        "template_titles": [f"Template title {index:02d}" for index in range(1, 11)],
        "social_urls": {
            "instagram": "",
            "linkedin": "https://www.linkedin.com/company/client-company",
            "facebook": "",
            "whatsapp": "",
        },
        "prospect_variables": ["NOMBRE", "CORREO"],
    }
    config.update(overrides)
    path = tmp_path / "campaign.config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_config_requires_https_calendly_url(tmp_path):
    config_path = write_config(tmp_path, calendly_url="http://calendly.com/client/30min")

    with pytest.raises(CampaignError, match="calendly_url"):
        load_config(config_path)


def test_config_requires_all_social_keys_but_values_can_be_empty(tmp_path):
    config_path = write_config(
        tmp_path,
        social_urls={"instagram": "", "linkedin": "", "facebook": "", "whatsapp": ""},
    )

    config = load_config(config_path)

    assert set(config["social_urls"]) == {"instagram", "linkedin", "facebook", "whatsapp"}


def test_config_rejects_removed_prospect_variables(tmp_path):
    config_path = write_config(tmp_path, prospect_variables=["NOMBRE", "EMPRESA", "PROYECTO"])

    with pytest.raises(CampaignError, match="prospect_variables"):
        load_config(config_path)


def test_generate_creates_ten_emails_with_calendly_and_variables(tmp_path):
    config_path = write_config(tmp_path)


    written = generate(config_path)

    assert len(written) == 10
    for path in written:
        text = path.read_text(encoding="utf-8")
        assert "https://calendly.com/client/30min" in text
        assert "{{{RESEND_UNSUBSCRIBE_URL}}}" in text
        assert "{{{NOMBRE}}}" in text
        assert "{{{CORREO}}}" in text
        assert "{{{EMPRESA}}}" not in text
        assert "{{{PROYECTO}}}" not in text
        assert "https://www.linkedin.com/company/client-company" in text
        assert 'aria-label="LinkedIn"' in text
        assert "<svg viewBox=\"0 0 24 24\"" in text
        assert "legacy_brand" not in text


def test_generate_omits_empty_social_icon_links(tmp_path):
    config_path = write_config(
        tmp_path,
        social_urls={
            "instagram": "https://www.instagram.com/client/",
            "linkedin": "",
            "facebook": "",
            "whatsapp": "",
        },
    )

    written = generate(config_path)
    text = written[0].read_text(encoding="utf-8")

    assert "https://www.instagram.com/client/" in text
    assert 'aria-label="Instagram"' in text
    assert 'aria-label="LinkedIn"' not in text
    assert 'aria-label="Facebook"' not in text
    assert 'aria-label="WhatsApp"' not in text


def test_verify_accepts_generated_campaign(tmp_path):
    config_path = write_config(tmp_path)
    generate(config_path)

    files = verify(config_path)

    assert len(files) == 10


def test_verify_fails_when_calendly_missing(tmp_path):
    config_path = write_config(tmp_path)
    generate(config_path)
    first = tmp_path / "emails" / "email-01.html"
    first.write_text(first.read_text(encoding="utf-8").replace("https://calendly.com/client/30min", ""), encoding="utf-8")

    with pytest.raises(AssertionError, match="calendly_url"):
        verify(config_path)


def test_automation_graph_has_expected_steps(tmp_path):
    config_path = write_config(tmp_path)
    config = load_config(config_path)

    automation = build_automation(config)

    assert len([s for s in automation["steps"] if s["type"] == "trigger"]) == 1
    assert len([s for s in automation["steps"] if s["type"] == "send_email"]) == 10
    assert len([s for s in automation["steps"] if s["type"] == "delay"]) == 9
    assert all(s["config"]["duration"] == "3 days" for s in automation["steps"] if s["type"] == "delay")


def test_setup_dry_run_does_not_call_network(tmp_path, monkeypatch):
    config_path = write_config(tmp_path)
    generate(config_path)

    def explode(*args, **kwargs):
        raise AssertionError("network should not be called during dry-run")

    monkeypatch.setattr("setup_resend.urlopen", explode)

    result = setup_resend(config_path, apply=False)

    assert result["mode"] == "dry-run"
    assert result["message"] == "No network calls were made."
    assert len(result["templates"]) == 10
