import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = ROOT / "contract_skill_public/scripts/setup_client_folder.py"
UPLOAD_SCRIPT = ROOT / "contract_skill_public/scripts/upload_contract_to_drive.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def setup_client_folder():
    return _load_module("contract_setup_client_folder_test", SETUP_SCRIPT)


@pytest.fixture
def upload_contract():
    return _load_module("contract_upload_contract_test", UPLOAD_SCRIPT)


def test_client_folder_user_share_uses_owner_email(setup_client_folder, monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        if args[1] == "create-folder":
            return {"id": "folder-123", "webViewLink": "https://drive/folder-123"}
        return {"status": "shared"}

    monkeypatch.setattr(setup_client_folder, "_run_google_api", fake_run)
    result = setup_client_folder.setup_client_folder(
        company_name="ACME",
        owner_name="Jane Doe",
        owner_email="jane@example.com",
        config={
            "client_folder": {
                "enabled": True,
                "parent_folder_id": "parent-123",
                "share_type": "user",
                "share_role": "reader",
                "allow_public_link": False,
                "send_email": False,
            }
        },
    )

    assert result["success"] is True
    assert calls[1] == [
        "drive",
        "share",
        "folder-123",
        "--type",
        "user",
        "--role",
        "reader",
        "--email",
        "jane@example.com",
    ]


def test_client_folder_public_link_requires_opt_in(setup_client_folder, monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        return {"id": "folder-123", "webViewLink": "https://drive/folder-123"}

    monkeypatch.setattr(setup_client_folder, "_run_google_api", fake_run)

    with pytest.raises(ValueError, match="allow_public_link=true"):
        setup_client_folder.setup_client_folder(
            company_name="ACME",
            owner_name="Jane Doe",
            owner_email="jane@example.com",
            config={
                "client_folder": {
                    "enabled": True,
                    "parent_folder_id": "parent-123",
                    "share_type": "anyone",
                    "share_role": "reader",
                    "allow_public_link": False,
                    "send_email": False,
                }
            },
        )

    assert calls == []


def test_client_folder_public_link_allowed_when_explicit(setup_client_folder, monkeypatch):
    calls = []

    def fake_run(args):
        calls.append(args)
        if args[1] == "create-folder":
            return {"id": "folder-123", "webViewLink": "https://drive/folder-123"}
        return {"status": "shared"}

    monkeypatch.setattr(setup_client_folder, "_run_google_api", fake_run)
    setup_client_folder.setup_client_folder(
        company_name="ACME",
        owner_name="Jane Doe",
        owner_email="jane@example.com",
        config={
            "client_folder": {
                "enabled": True,
                "parent_folder_id": "parent-123",
                "share_type": "anyone",
                "share_role": "reader",
                "allow_public_link": True,
                "send_email": False,
            }
        },
    )

    assert calls[1] == ["drive", "share", "folder-123", "--type", "anyone", "--role", "reader"]


def test_upload_contract_user_share_requires_email_before_upload(upload_contract, tmp_path, monkeypatch):
    pdf = tmp_path / "contract.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    calls = []
    monkeypatch.setattr(upload_contract, "_run_google_api", lambda args: calls.append(args) or {})

    with pytest.raises(ValueError, match="share_type=user"):
        upload_contract.upload_contract(
            pdf,
            config={
                "google_drive": {
                    "folder_id": "parent-123",
                    "share_type": "user",
                    "share_role": "reader",
                    "allow_public_link": False,
                }
            },
        )

    assert calls == []


def test_upload_contract_user_share_uses_share_email(upload_contract, tmp_path, monkeypatch):
    pdf = tmp_path / "contract.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    calls = []

    def fake_run(args):
        calls.append(args)
        if args[1] == "upload":
            return {"id": "file-123", "name": "contract.pdf", "webViewLink": "https://drive/file-123"}
        return {"status": "shared"}

    monkeypatch.setattr(upload_contract, "_run_google_api", fake_run)
    result = upload_contract.upload_contract(
        pdf,
        share_email="jane@example.com",
        config={
            "google_drive": {
                "folder_id": "parent-123",
                "share_type": "user",
                "share_role": "reader",
                "allow_public_link": False,
            }
        },
    )

    assert result["success"] is True
    assert calls[1] == [
        "drive",
        "share",
        "file-123",
        "--type",
        "user",
        "--role",
        "reader",
        "--email",
        "jane@example.com",
    ]


def test_upload_contract_public_link_requires_opt_in(upload_contract, tmp_path, monkeypatch):
    pdf = tmp_path / "contract.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    calls = []
    monkeypatch.setattr(upload_contract, "_run_google_api", lambda args: calls.append(args) or {})

    with pytest.raises(ValueError, match="allow_public_link=true"):
        upload_contract.upload_contract(
            pdf,
            config={
                "google_drive": {
                    "folder_id": "parent-123",
                    "share_type": "anyone",
                    "share_role": "reader",
                    "allow_public_link": False,
                }
            },
        )

    assert calls == []
