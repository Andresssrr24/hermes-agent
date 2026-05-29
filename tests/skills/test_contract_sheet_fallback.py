import importlib.util
from pathlib import Path

import pytest


POLL_SCRIPT = Path(__file__).resolve().parents[2] / "contract_skill_public/scripts/poll_ready_contracts.py"


class FakeSheetsService:
    def __init__(self, rows):
        self.rows = rows
        self.request = None

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def get(self, **kwargs):
        self.request = kwargs
        return self

    def execute(self):
        return {"values": self.rows}


@pytest.fixture
def poller():
    spec = importlib.util.spec_from_file_location("contract_poller_test", POLL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_normalize_job_fills_missing_fields_from_sheet(poller, monkeypatch):
    service = FakeSheetsService([
        [
            "submission_id",
            "company_sector",
            "company_whatsapp",
            "company_document",
            "owner_whatsapp",
            "owner_identity_document",
            "confirmed_plan",
        ],
        ["sub-1", "inmobiliario", "+1 809 000 0000", "130000000", "+1 809 111 1111", "00100000000", "2500"],
    ])
    monkeypatch.setattr(poller, "_build_sheets_service", lambda token_path="": service)

    job = {
        "submission_id": "sub-1",
        "company_name": "ACME REAL ESTATE SRL",
        "owner_name": "Jane Doe",
        "owner_email": "jane@example.com",
        "ad_budget_30_days_usd": "2500",
    }
    sheet_config = {
        "sheet_id": "sheet-id",
        "tab_name": "Responses",
        "range": "A:Z",
        "submission_id_column": "submission_id",
        "fallback_enabled": True,
        "field_columns": {"plan": "confirmed_plan"},
    }

    normalized = poller._normalize_job(job, sheet_config, {})

    assert normalized["plan"] == "2500"
    assert normalized["company_sector"] == "inmobiliario"
    assert normalized["company_whatsapp"] == "+1 809 000 0000"
    assert normalized["company_document"] == "130000000"
    assert normalized["owner_whatsapp"] == "+1 809 111 1111"
    assert normalized["owner_identity_document"] == "00100000000"
    assert service.request == {"spreadsheetId": "sheet-id", "range": "'Responses'!A:Z"}


def test_normalize_job_without_fallback_reports_missing_fields(poller):
    job = {
        "submission_id": "sub-1",
        "plan": "2500",
        "company_name": "ACME REAL ESTATE SRL",
        "owner_name": "Jane Doe",
        "owner_email": "jane@example.com",
        "ad_budget_30_days_usd": "2500",
    }

    with pytest.raises(ValueError) as exc:
        poller._normalize_job(job)

    assert "company_sector" in str(exc.value)
    assert "company_whatsapp" in str(exc.value)


def test_validate_safe_path_allows_regular_token_path(poller, tmp_path):
    token_path = tmp_path / "google_token.json"

    assert poller._validate_safe_path(str(token_path)) == token_path.resolve()


@pytest.mark.parametrize("path", ["/etc/passwd", "/usr/local/token.json"])
def test_validate_safe_path_blocks_system_paths(poller, path):
    with pytest.raises(PermissionError):
        poller._validate_safe_path(path)


def test_validate_safe_path_blocks_sensitive_home_file(poller, monkeypatch, tmp_path):
    monkeypatch.setattr(poller.os.path, "expanduser", lambda p: str(tmp_path) if p == "~" else p)

    with pytest.raises(PermissionError):
        poller._validate_safe_path(str(tmp_path / ".netrc"))
