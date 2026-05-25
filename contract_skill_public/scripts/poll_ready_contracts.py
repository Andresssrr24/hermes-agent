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


def _normalize_job(job: dict[str, Any]) -> dict[str, Any]:
    contract = dict(job.get("contract") or {})
    merged = {**contract, **{k: v for k, v in job.items() if k != "contract"}}
    submission_id = str(merged.get("submission_id") or merged.get("id") or "").strip()
    if not submission_id:
        raise ValueError("job is missing submission_id")

    normalized = {field: str(merged.get(field, "")).strip() for field in REQUIRED_CONTRACT_FIELDS}
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
        command = [sys.executable, str(render_script), "--input", str(input_path)]
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


def process_job(job: dict[str, Any], no_drive_upload: bool = False) -> dict[str, Any]:
    try:
        normalized = _normalize_job(job)
        result = _run_renderer(normalized, no_drive_upload=no_drive_upload)
        return {"submission_id": normalized["submission_id"], **result}
    except Exception as exc:
        submission_id = str(job.get("submission_id") or job.get("id") or "unknown")
        return {"submission_id": submission_id, "success": False, "error": str(exc)}


def summarize_job(job: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_job(job)
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
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate jobs without rendering or posting completion.")
    parser.add_argument("--summary", action="store_true", help="Return ready job details without rendering or posting completion.")
    parser.add_argument("--insecure-skip-verify", action="store_true", help="Skip TLS certificate verification for n8n requests.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.insecure_skip_verify:
        os.environ["N8N_INSECURE_SKIP_VERIFY"] = "true"
    if not args.ready_url:
        print(json.dumps({"success": False, "error": "Set N8N_READY_CONTRACTS_URL or pass --ready-url"}), file=sys.stderr)
        return 1

    payload = _request_json("GET", args.ready_url, token=args.ready_token)
    jobs = _extract_jobs(payload)[: max(args.limit, 0)]
    results = []

    if args.summary:
        summary_jobs = []
        for job in jobs:
            try:
                summary_jobs.append(summarize_job(job))
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
                normalized = _normalize_job(job)
                result = {"submission_id": normalized["submission_id"], "success": True, "dry_run": True}
            except Exception as exc:
                result = {"submission_id": str(job.get("submission_id") or job.get("id") or "unknown"), "success": False, "error": str(exc), "dry_run": True}
        else:
            result = process_job(job, no_drive_upload=args.no_drive_upload)
            if args.complete_url:
                _request_json("POST", args.complete_url, payload=result, token=args.complete_token)
        results.append(result)

    print(json.dumps({"success": True, "processed": len(results), "results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
