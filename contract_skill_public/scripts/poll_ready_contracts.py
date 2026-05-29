#!/usr/bin/env python3
"""Poll n8n for confirmed contract jobs and process them."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REQUIRED_CONTRACT_FIELDS = [
    "plan",
    "company_name",
    "company_sector",
    "company_whatsapp",
    "company_document",
    "owner_name",
    "owner_whatsapp",
    "owner_email",
    "owner_identity_document",
    "ad_budget_30_days_usd",
]

SHEETS_READONLY_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _auth_headers(token: str = "") -> dict[str, str]:
    resolved = token or _env("N8N_CONTRACTS_TOKEN")
    headers = {"Content-Type": "application/json"}
    if resolved:
        headers["Authorization"] = f"Bearer {resolved}"
    return headers


def _skip_verify() -> bool:
    return _env("N8N_INSECURE_SKIP_VERIFY").lower() in {"1", "true", "yes", "on"}


def _renderer_python() -> str:
    return _env("CONTRACT_RENDER_PYTHON") or sys.executable


def _hermes_home() -> Path:
    return Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def _load_plans_config() -> dict[str, Any]:
    path = _skill_dir() / "references" / "plans.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _stored_token_scopes(token_path: Path) -> list[str]:
    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
    except Exception:
        return list(SHEETS_READONLY_SCOPES)
    scopes = data.get("scopes")
    if isinstance(scopes, list) and scopes:
        return scopes
    return list(SHEETS_READONLY_SCOPES)


def _build_sheets_service(token_path: str = "") -> Any:
    resolved_token = Path(token_path).expanduser() if token_path else _hermes_home() / "google_token.json"
    if not resolved_token.exists():
        raise RuntimeError(
            f"Google token not found: {resolved_token}. Run Google Workspace OAuth setup first."
        )
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Google Sheets fallback requires google-api-python-client and google-auth. "
            "Install this skill's requirements first."
        ) from exc

    creds = Credentials.from_authorized_user_file(
        str(resolved_token), _stored_token_scopes(resolved_token)
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        payload = json.loads(creds.to_json())
        payload.setdefault("type", "authorized_user")
        resolved_token.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if not creds.valid:
        raise RuntimeError("Google token is invalid. Re-run Google Workspace OAuth setup.")
    return build("sheets", "v4", credentials=creds)


def _quote_sheet_range(tab_name: str, data_range: str) -> str:
    escaped = tab_name.replace("'", "''")
    return f"'{escaped}'!{data_range}"


def _fetch_sheet_row(submission_id: str, sheet_config: dict[str, Any], sheets_service: Any) -> dict[str, str]:
    sheet_id = str(sheet_config.get("sheet_id") or "").strip()
    tab_name = str(sheet_config.get("tab_name") or "").strip()
    data_range = str(sheet_config.get("range") or "A:Z").strip()
    submission_id_column = str(sheet_config.get("submission_id_column") or "submission_id").strip()
    if not sheet_id or not tab_name:
        raise RuntimeError("google_sheet.sheet_id and google_sheet.tab_name are required for fallback")

    result = (
        sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=_quote_sheet_range(tab_name, data_range))
        .execute()
    )
    rows = result.get("values", [])
    if not rows:
        return {}
    headers = [str(cell).strip() for cell in rows[0]]
    try:
        submission_index = headers.index(submission_id_column)
    except ValueError as exc:
        raise RuntimeError(
            f"Google Sheet is missing submission ID column: {submission_id_column}"
        ) from exc

    for row in rows[1:]:
        row_submission_id = str(row[submission_index]).strip() if submission_index < len(row) else ""
        if row_submission_id != submission_id:
            continue
        return {
            header: str(row[index]).strip() if index < len(row) else ""
            for index, header in enumerate(headers)
        }
    return {}


def _resolve_sheet_value(field: str, row: dict[str, str], sheet_config: dict[str, Any]) -> str:
    field_columns = sheet_config.get("field_columns") or {}
    candidate_columns = []
    if isinstance(field_columns, dict) and field_columns.get(field):
        candidate_columns.append(str(field_columns[field]))
    candidate_columns.append(field)
    if field == "plan":
        candidate_columns.append("confirmed_plan")
    for column in candidate_columns:
        value = str(row.get(column, "")).strip()
        if value:
            return value
    return ""


def _google_sheet_config(args: argparse.Namespace) -> dict[str, Any] | None:
    config = _load_plans_config().get("google_sheet") or {}
    if not isinstance(config, dict):
        config = {}
    resolved = dict(config)
    if args.google_sheet_id:
        resolved["sheet_id"] = args.google_sheet_id
    if args.google_sheet_tab:
        resolved["tab_name"] = args.google_sheet_tab
    if args.google_sheet_range:
        resolved["range"] = args.google_sheet_range
    if args.google_sheet_fallback:
        resolved["fallback_enabled"] = True
    if args.google_token_path:
        resolved["token_path"] = args.google_token_path
    return resolved if resolved.get("fallback_enabled") else None


def _check_renderer_runtime(python_executable: str, no_drive_upload: bool = False) -> list[str]:
    errors: list[str] = []
    render_script = _skill_dir() / "scripts" / "render_contract.py"
    references = _skill_dir() / "references" / "plans.json"
    templates = [_skill_dir() / "templates" / f"{plan}.pdf" for plan in ("650", "1500", "2500")]

    if not Path(python_executable).exists() and Path(python_executable).is_absolute():
        errors.append(f"Renderer Python not found: {python_executable}")
    if not render_script.exists():
        errors.append(f"Renderer script not found: {render_script}")
    if not references.exists():
        errors.append(f"Plans config not found: {references}")
    for template in templates:
        if not template.exists():
            errors.append(f"Contract template not found: {template}")

    try:
        completed = subprocess.run(
            [python_executable, "-c", "import fitz"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        errors.append(f"Renderer Python cannot be executed: {python_executable} ({exc})")
    else:
        if completed.returncode != 0:
            errors.append(
                f"Renderer Python is missing PyMuPDF. Install it with: {python_executable} -m pip install pymupdf"
            )

    if not no_drive_upload:
        upload_script = _skill_dir() / "scripts" / "upload_contract_to_drive.py"
        if not upload_script.exists():
            errors.append(f"Drive upload script not found: {upload_script}")

    return errors


def _print_error(error: str) -> None:
    print(json.dumps({"success": False, "error": error}, ensure_ascii=False), file=sys.stderr)


def _request_json(method: str, url: str, payload: Any = None, token: str = "") -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers=_auth_headers(token),
        method=method,
    )
    try:
        context = ssl._create_unverified_context() if _skip_verify() else None
        with urllib.request.urlopen(req, timeout=30, context=context) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"n8n {method} {url} failed with {exc.code}: {detail}") from exc
    if not body.strip():
        return None
    return json.loads(body)


def _extract_jobs(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("jobs", "data", "items", "ready"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if payload.get("submission_id") or payload.get("contract"):
            return [payload]
    raise ValueError("Ready-jobs response must be a job object, list, or object with jobs/data/items")


def _normalize_job(
    job: dict[str, Any],
    sheet_config: dict[str, Any] | None = None,
    sheets_service_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = dict(job.get("contract") or {})
    merged = {**contract, **{k: v for k, v in job.items() if k != "contract"}}
    submission_id = str(merged.get("submission_id") or merged.get("id") or "").strip()
    if not submission_id:
        raise ValueError("job is missing submission_id")

    normalized = {field: str(merged.get(field, "")).strip() for field in REQUIRED_CONTRACT_FIELDS}
    missing = [field for field, value in normalized.items() if not value]
    if missing and sheet_config:
        cache = sheets_service_cache if sheets_service_cache is not None else {}
        service = cache.get("service")
        if service is None:
            service = _build_sheets_service(str(sheet_config.get("token_path") or ""))
            cache["service"] = service
        row = _fetch_sheet_row(submission_id, sheet_config, service)
        for field in missing:
            normalized[field] = _resolve_sheet_value(field, row, sheet_config)
        missing = [field for field, value in normalized.items() if not value]
    if missing:
        raise ValueError(f"job {submission_id} missing required fields: {', '.join(missing)}")

    normalized["submission_id"] = submission_id
    if merged.get("contract_date"):
        normalized["contract_date"] = str(merged["contract_date"]).strip()
    return normalized


def _run_renderer(job: dict[str, Any], no_drive_upload: bool = False) -> dict[str, Any]:
    render_script = _skill_dir() / "scripts" / "render_contract.py"
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as fh:
        json.dump(job, fh, ensure_ascii=False)
        input_path = Path(fh.name)
    try:
        command = [_renderer_python(), str(render_script), "--input", str(input_path)]
        if no_drive_upload:
            command.append("--no-drive-upload")
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    finally:
        input_path.unlink(missing_ok=True)

    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip() or "contract rendering failed"
        return {"success": False, "error": error}
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"success": False, "error": f"renderer returned non-JSON output: {completed.stdout.strip()}"}


def _setup_client_folder(
    normalized: dict[str, Any],
    no_client_folder: bool = False,
) -> dict[str, Any] | None:
    if no_client_folder:
        return None
    config = _load_plans_config()
    cf = config.get("client_folder")
    if not isinstance(cf, dict) or not cf.get("enabled"):
        return None
    try:
        from setup_client_folder import setup_client_folder as _do_setup
    except ImportError:
        setup_script = _skill_dir() / "scripts" / "setup_client_folder.py"
        if not setup_script.exists():
            return {"success": False, "error": "setup_client_folder.py not found"}
        completed = subprocess.run(
            [_renderer_python(), str(setup_script),
             "--company-name", normalized["company_name"],
             "--owner-name", normalized["owner_name"],
             "--owner-email", normalized["owner_email"]],
            check=False, capture_output=True, text=True,
        )
        if completed.returncode != 0:
            return {"success": False, "error": completed.stderr.strip() or completed.stdout.strip() or "client folder setup failed"}
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {"success": False, "error": f"setup_client_folder returned non-JSON: {completed.stdout.strip()}"}

    try:
        return _do_setup(
            company_name=normalized["company_name"],
            owner_name=normalized["owner_name"],
            owner_email=normalized["owner_email"],
            config=config,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def process_job(
    job: dict[str, Any],
    no_drive_upload: bool = False,
    no_client_folder: bool = False,
    sheet_config: dict[str, Any] | None = None,
    sheets_service_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        normalized = _normalize_job(job, sheet_config, sheets_service_cache)
        result = _run_renderer(normalized, no_drive_upload=no_drive_upload)
        if result.get("success"):
            folder_result = _setup_client_folder(normalized, no_client_folder=no_client_folder)
            if folder_result is not None:
                result["client_folder"] = folder_result
        return {"submission_id": normalized["submission_id"], **result}
    except Exception as exc:
        submission_id = str(job.get("submission_id") or job.get("id") or "unknown")
        return {"submission_id": submission_id, "success": False, "error": str(exc)}


def summarize_job(
    job: dict[str, Any],
    sheet_config: dict[str, Any] | None = None,
    sheets_service_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _normalize_job(job, sheet_config, sheets_service_cache)
    return {
        "submission_id": normalized["submission_id"],
        "company_name": normalized["company_name"],
        "owner_name": normalized["owner_name"],
        "owner_email": normalized["owner_email"],
        "plan": normalized["plan"],
        "ad_budget_30_days_usd": normalized["ad_budget_30_days_usd"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Poll n8n for confirmed contract jobs.")
    parser.add_argument("--ready-url", default=_env("N8N_READY_CONTRACTS_URL"), help="n8n endpoint that returns ready jobs.")
    parser.add_argument("--complete-url", default=_env("N8N_CONTRACT_COMPLETED_URL"), help="n8n endpoint that receives processing results.")
    parser.add_argument("--ready-token", default=_env("N8N_READY_CONTRACTS_TOKEN"), help="Bearer token for ready-job endpoint.")
    parser.add_argument("--complete-token", default=_env("N8N_CONTRACT_COMPLETED_TOKEN"), help="Bearer token for completion endpoint.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum jobs to process in one run.")
    parser.add_argument("--no-drive-upload", action="store_true", help="Generate local PDFs without Drive upload.")
    parser.add_argument("--no-client-folder", action="store_true", help="Skip client folder creation and email.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate jobs without rendering or posting completion.")
    parser.add_argument("--summary", action="store_true", help="Return ready job details without rendering or posting completion.")
    parser.add_argument("--generate", action="store_true", help="Generate contracts for all returned ready jobs. Requires explicit flag; default is --summary.")
    parser.add_argument("--preflight", action="store_true", help="Validate runtime dependencies without polling or processing jobs.")
    parser.add_argument("--insecure-skip-verify", action="store_true", help="Skip TLS certificate verification for n8n requests.")
    parser.add_argument("--google-sheet-fallback", action="store_true", help="Fill missing job fields from the configured Google Sheet.")
    parser.add_argument("--google-sheet-id", default="", help="Override google_sheet.sheet_id from references/plans.json.")
    parser.add_argument("--google-sheet-tab", default="", help="Override google_sheet.tab_name from references/plans.json.")
    parser.add_argument("--google-sheet-range", default="", help="Override google_sheet.range from references/plans.json.")
    parser.add_argument("--google-token-path", default="", help="Override Google OAuth token path. Defaults to $HERMES_HOME/google_token.json.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.insecure_skip_verify:
        os.environ["N8N_INSECURE_SKIP_VERIFY"] = "true"
    renderer_python = _renderer_python()
    runtime_errors = _check_renderer_runtime(renderer_python, no_drive_upload=args.no_drive_upload)

    if args.preflight:
        print(json.dumps({
            "success": not runtime_errors,
            "renderer_python": renderer_python,
            "pymupdf": not any("PyMuPDF" in error for error in runtime_errors),
            "errors": runtime_errors,
        }, ensure_ascii=False))
        return 0 if not runtime_errors else 1

    if not args.ready_url:
        _print_error("Set N8N_READY_CONTRACTS_URL or pass --ready-url")
        return 1
    if not (args.ready_token or _env("N8N_CONTRACTS_TOKEN")):
        _print_error("Set N8N_READY_CONTRACTS_TOKEN or N8N_CONTRACTS_TOKEN before polling n8n")
        return 1
    if args.complete_url and not (args.complete_token or _env("N8N_CONTRACTS_TOKEN")):
        _print_error("Set N8N_CONTRACT_COMPLETED_TOKEN or N8N_CONTRACTS_TOKEN before posting completion")
        return 1
    if not (args.summary or args.dry_run) and runtime_errors:
        _print_error("; ".join(runtime_errors))
        return 1

    if not (args.generate or args.dry_run):
        args.summary = True

    payload = _request_json("GET", args.ready_url, token=args.ready_token)
    jobs = _extract_jobs(payload)[: max(args.limit, 0)]
    results = []
    sheet_config = _google_sheet_config(args)
    sheets_service_cache: dict[str, Any] = {}

    if args.summary:
        summary_jobs = []
        for job in jobs:
            try:
                summary_jobs.append(summarize_job(job, sheet_config, sheets_service_cache))
            except Exception as exc:
                summary_jobs.append({
                    "submission_id": str(job.get("submission_id") or job.get("id") or "unknown"),
                    "success": False,
                    "error": str(exc),
                })
        print(json.dumps({"success": True, "ready_count": len(jobs), "jobs": summary_jobs}, ensure_ascii=False))
        return 0

    for job in jobs:
        if args.dry_run:
            try:
                normalized = _normalize_job(job, sheet_config, sheets_service_cache)
                result = {"submission_id": normalized["submission_id"], "success": True, "dry_run": True}
            except Exception as exc:
                result = {"submission_id": str(job.get("submission_id") or job.get("id") or "unknown"), "success": False, "error": str(exc), "dry_run": True}
        else:
            result = process_job(
                job,
                no_drive_upload=args.no_drive_upload,
                no_client_folder=args.no_client_folder,
                sheet_config=sheet_config,
                sheets_service_cache=sheets_service_cache,
            )
            if args.complete_url:
                _request_json("POST", args.complete_url, payload=result, token=args.complete_token)
        results.append(result)

    print(json.dumps({"success": True, "processed": len(results), "results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
