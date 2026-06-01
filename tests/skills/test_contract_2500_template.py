import importlib.util
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RENDER_SCRIPT = ROOT / "contract_skill_public/scripts/render_contract.py"
FIELDS_CONFIG = ROOT / "contract_skill_public/references/fields.json"


def _load_render_module():
    spec = importlib.util.spec_from_file_location("contract_render_2500_template_test", RENDER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _block(blocks, name):
    for block in blocks:
        if block.get("name") == name:
            return block
    raise AssertionError(f"missing block: {name}")


def test_contract_month_year_uses_contract_date():
    render = _load_render_module()

    assert render._spanish_month_year(date(2026, 6, 1)) == "JUNIO 2026"


def test_2500_cover_date_replaces_static_template_date():
    fields = json.loads(FIELDS_CONFIG.read_text(encoding="utf-8"))
    blocks = fields["plans"]["2500"]["manual_blocks"]
    cover_date = _block(blocks, "cover_date")

    assert cover_date["page"] == 0
    assert cover_date["lines"] == ["{contract_month_year_es}"]
    assert cover_date["redact_rect"][0] <= 248
    assert cover_date["redact_rect"][1] <= 759
    assert cover_date["redact_rect"][2] >= 348
    assert cover_date["redact_rect"][3] >= 781


def test_2500_intro_blocks_are_left_aligned_and_redact_right_side():
    fields = json.loads(FIELDS_CONFIG.read_text(encoding="utf-8"))
    blocks = fields["plans"]["2500"]["manual_blocks"]

    professional_intro = _block(blocks, "professional_intro")
    client_intro = _block(blocks, "client_intro")

    assert professional_intro["insert_at"][0] == 59.5
    assert client_intro["insert_at"][0] == 59.5
    assert professional_intro["redact_rect"][2] >= 590
    assert client_intro["redact_rect"][2] >= 590


def test_client_signature_blocks_do_not_include_signature_underline():
    fields = json.loads(FIELDS_CONFIG.read_text(encoding="utf-8"))

    for plan, plan_config in fields["plans"].items():
        client_signature = _block(plan_config["manual_blocks"], "client_signature")
        assert "Firma:" in client_signature["lines"]
        assert all("____" not in line for line in client_signature["lines"]), plan
