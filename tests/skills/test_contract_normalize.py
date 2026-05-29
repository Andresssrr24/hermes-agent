import importlib.util
from pathlib import Path

import pytest


NORMALIZE_PATH = Path(__file__).resolve().parents[2] / "contract_skill_public/scripts/normalize.py"


@pytest.fixture
def norm():
    spec = importlib.util.spec_from_file_location("contract_normalize_test", NORMALIZE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestNormalizeName:
    def test_title_case(self, norm):
        assert norm.normalize_name("jane doe") == "Jane Doe"
        assert norm.normalize_name("JANE DOE") == "Jane Doe"
        assert norm.normalize_name("acme real estate srl") == "Acme Real Estate SRL"

    def test_preserves_business_suffixes(self, norm):
        assert norm.normalize_name("grupo arpa sa") == "Grupo Arpa SA"
        assert norm.normalize_name("corp name llc") == "CORP Name LLC"
        assert norm.normalize_name("algotech sas") == "Algotech SAS"
        assert norm.normalize_name("inversiones eirl") == "Inversiones EIRL"
        assert norm.normalize_name("comercial ltda") == "Comercial LTDA"

    def test_compound_suffixes(self, norm):
        assert norm.normalize_name("inmobiliaria s. de r.l.") == "Inmobiliaria S. DE R.L."
        assert norm.normalize_name("constructora srl de cv") == "Constructora SRL DE CV"

    def test_strips_whitespace(self, norm):
        assert norm.normalize_name("  extra   spaces  ") == "Extra Spaces"

    def test_empty_and_non_string(self, norm):
        assert norm.normalize_name("") == ""
        assert norm.normalize_name("   ") == ""
        assert norm.normalize_name(None) == ""
        assert norm.normalize_name(42) == ""


class TestNormalizePhone:
    def test_10_digit(self, norm):
        assert norm.normalize_phone("8091234567") == "+1 809 123 4567"

    def test_11_digit_leading_1(self, norm):
        assert norm.normalize_phone("18091234567") == "+1 809 123 4567"

    def test_formatted_variants(self, norm):
        assert norm.normalize_phone("(809) 123-4567") == "+1 809 123 4567"
        assert norm.normalize_phone("809-123-4567") == "+1 809 123 4567"
        assert norm.normalize_phone("+1 809-123-4567") == "+1 809 123 4567"
        assert norm.normalize_phone("+1 (809) 123-4567") == "+1 809 123 4567"
        assert norm.normalize_phone("809.123.4567") == "+1 809 123 4567"

    def test_strips_whitespace(self, norm):
        assert norm.normalize_phone("  809 123 4567  ") == "+1 809 123 4567"

    def test_unknown_length_preserved(self, norm):
        assert norm.normalize_phone("12345") == "+12345"
        assert norm.normalize_phone("444555666") == "+444555666"

    def test_empty_and_non_string(self, norm):
        assert norm.normalize_phone("") == ""
        assert norm.normalize_phone("   ") == ""
        assert norm.normalize_phone(None) == ""


class TestNormalizeEmail:
    def test_typo_fixes(self, norm):
        assert norm.normalize_email("jane@example.comm") == "jane@example.com"
        assert norm.normalize_email("jane@example.con") == "jane@example.com"
        assert norm.normalize_email("jane@example.cmo") == "jane@example.com"
        assert norm.normalize_email("jane@example.ner") == "jane@example.net"
        assert norm.normalize_email("jane@example.ogr") == "jane@example.org"

    def test_double_com(self, norm):
        assert norm.normalize_email("jane@example.com.com") == "jane@example.com"

    def test_lowercase(self, norm):
        assert norm.normalize_email("Jane@Example.COM") == "jane@example.com"

    def test_valid_tlds_preserved(self, norm):
        assert norm.normalize_email("jane@example.com.br") == "jane@example.com.br"
        assert norm.normalize_email("jane@example.com.do") == "jane@example.com.do"
        assert norm.normalize_email("jane@example.net") == "jane@example.net"
        assert norm.normalize_email("jane@example.org") == "jane@example.org"
        assert norm.normalize_email("jane@example.co") == "jane@example.co"

    def test_cm_flagged_with_sentinel(self, norm):
        result = norm.normalize_email("jane@example.cm")
        assert norm._CM_WARNING_SENTINEL in result
        assert result.startswith("jane@example.cm")

    def test_strips_whitespace(self, norm):
        assert norm.normalize_email("  jane@example.com  ") == "jane@example.com"

    def test_empty_and_non_string(self, norm):
        assert norm.normalize_email("") == ""
        assert norm.normalize_email("   ") == ""
        assert norm.normalize_email(None) == ""


class TestNormalizePlan:
    def test_recognised_plans(self, norm):
        assert norm.normalize_plan("650") == "650"
        assert norm.normalize_plan("1500") == "1500"
        assert norm.normalize_plan("2500") == "2500"

    def test_dollar_sign(self, norm):
        assert norm.normalize_plan("$650") == "650"
        assert norm.normalize_plan("$2500") == "2500"

    def test_plan_with_extra_text(self, norm):
        assert norm.normalize_plan("Plan de Inicio 650") == "650"
        assert norm.normalize_plan("Plan Elite $2500") == "2500"
        assert norm.normalize_plan("1500 extra") == "1500"

    def test_unrecognised_plan_raises(self, norm):
        with pytest.raises(ValueError, match="plan must be one of"):
            norm.normalize_plan("999")
        with pytest.raises(ValueError, match="plan must be one of"):
            norm.normalize_plan("")
        with pytest.raises(ValueError, match="plan must be one of"):
            norm.normalize_plan("bogus")


class TestNormalizeBudget:
    def test_numeric_values(self, norm):
        assert norm.normalize_budget("2500") == "2500"

    def test_currency_formats(self, norm):
        assert norm.normalize_budget("$2,500") == "2,500"
        assert norm.normalize_budget("2500 USD") == "2500"
        assert norm.normalize_budget("2500 usd") == "2500"

    def test_missing_raises(self, norm):
        with pytest.raises(ValueError, match="ad_budget_30_days_usd is required"):
            norm.normalize_budget("")
        with pytest.raises(ValueError, match="ad_budget_30_days_usd is required"):
            norm.normalize_budget("   ")


class TestNormalizeFormData:
    def test_smoke_complete_dict(self, norm):
        data = {
            "plan": "2500",
            "company_name": "ACME REAL ESTATE SRL",
            "company_sector": "Inmobiliario",
            "company_whatsapp": "+1 809 000 0000",
            "company_document": "130000000",
            "owner_name": "Jane Doe",
            "owner_whatsapp": "+1 809 111 1111",
            "owner_email": "jane@example.com",
            "owner_identity_document": "00100000000",
            "ad_budget_30_days_usd": "2500",
        }
        normalized, warnings = norm.normalize_form_data(data)

        assert warnings == []
        assert normalized["plan"] == "2500"
        assert normalized["company_name"] == "Acme Real Estate SRL"
        assert normalized["company_sector"] == "inmobiliario"
        assert normalized["company_whatsapp"] == "+1 809 000 0000"
        assert normalized["company_document"] == "130000000"
        assert normalized["owner_name"] == "Jane Doe"
        assert normalized["owner_whatsapp"] == "+1 809 111 1111"
        assert normalized["owner_email"] == "jane@example.com"
        assert normalized["owner_identity_document"] == "00100000000"
        assert normalized["ad_budget_30_days_usd"] == "2500"

    def test_fixes_messy_data(self, norm):
        data = {
            "plan": "plan elite $2500",
            "company_name": "acme real estate srl",
            "company_sector": "  INMOBILIARIO  ",
            "company_whatsapp": "809-000-0000",
            "company_document": " 130000000 ",
            "owner_name": "JANE DOE",
            "owner_whatsapp": "+1 (809) 111-1111",
            "owner_email": "JANE@EXAMPLE.COMM",
            "owner_identity_document": "00100000000",
            "ad_budget_30_days_usd": "$2,500 usd",
        }
        normalized, warnings = norm.normalize_form_data(data)

        assert warnings == []
        assert normalized["plan"] == "2500"
        assert normalized["company_name"] == "Acme Real Estate SRL"
        assert normalized["company_sector"] == "inmobiliario"
        assert normalized["company_whatsapp"] == "+1 809 000 0000"
        assert normalized["owner_name"] == "Jane Doe"
        assert normalized["owner_whatsapp"] == "+1 809 111 1111"
        assert normalized["owner_email"] == "jane@example.com"
        assert normalized["ad_budget_30_days_usd"] == "2,500"

    def test_cm_email_produces_warning(self, norm):
        data = {
            "plan": "650",
            "company_name": "Test",
            "company_sector": "tech",
            "company_whatsapp": "8091234567",
            "company_document": "123",
            "owner_name": "Alice",
            "owner_whatsapp": "8091234567",
            "owner_email": "alice@example.cm",
            "owner_identity_document": "456",
            "ad_budget_30_days_usd": "1000",
        }
        normalized, warnings = norm.normalize_form_data(data)

        assert len(warnings) == 1
        assert ".cm TLD preserved" in warnings[0]
        assert normalized["owner_email"] == "alice@example.cm"

    def test_warning_on_unrecognised_plan(self, norm):
        data = {
            "plan": "999",
            "company_name": "Test",
            "company_sector": "tech",
            "company_whatsapp": "8091234567",
            "company_document": "123",
            "owner_name": "Alice",
            "owner_whatsapp": "8091234567",
            "owner_email": "alice@example.com",
            "owner_identity_document": "456",
            "ad_budget_30_days_usd": "1000",
        }
        normalized, warnings = norm.normalize_form_data(data)

        assert len(warnings) == 1
        assert "plan:" in warnings[0]
        assert normalized["plan"] == ""

    def test_passthrough_unknown_keys(self, norm):
        data = {
            "plan": "650",
            "company_name": "Test",
            "company_sector": "tech",
            "company_whatsapp": "8091234567",
            "company_document": "123",
            "owner_name": "Alice",
            "owner_whatsapp": "8091234567",
            "owner_email": "alice@example.com",
            "owner_identity_document": "456",
            "ad_budget_30_days_usd": "1000",
            "submission_id": "sub-42",
            "contract_date": "2026-05-28",
        }
        normalized, warnings = norm.normalize_form_data(data)

        assert warnings == []
        assert normalized["submission_id"] == "sub-42"
        assert normalized["contract_date"] == "2026-05-28"
        assert normalized["company_name"] == "Test"

    def test_missing_fields_become_empty(self, norm):
        data = {"plan": "650", "company_name": "Test", "ad_budget_30_days_usd": "1000"}
        normalized, warnings = norm.normalize_form_data(data)

        assert normalized["company_sector"] == ""
        assert normalized["company_whatsapp"] == ""
        assert normalized["owner_email"] == ""

    def test_non_string_values(self, norm):
        data = {
            "plan": 1500,
            "company_name": "Test",
            "company_sector": "tech",
            "company_whatsapp": "8091234567",
            "company_document": 130000000,
            "owner_name": "Alice",
            "owner_whatsapp": "8091234567",
            "owner_email": "alice@example.com",
            "owner_identity_document": "456",
            "ad_budget_30_days_usd": 2500.0,
        }
        normalized, warnings = norm.normalize_form_data(data)

        assert warnings == []
        assert normalized["plan"] == "1500"
        assert normalized["company_document"] == "130000000"
        assert normalized["ad_budget_30_days_usd"] == "2500.0"
