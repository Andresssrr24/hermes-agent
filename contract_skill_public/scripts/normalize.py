#!/usr/bin/env python3
"""Form-field normalization for company contract generation.

All normalization functions accept any value type and return a string.
Raises ValueError for critically malformed data (e.g. unrecognised plan).
Non-blocking warnings are collected in a list and surfaced to callers
so generation can proceed with review.
"""

from __future__ import annotations

import re
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

# Use negative lookahead for end boundary instead of \b because suffixes
# ending with "." (e.g. "S. DE R.L.") have a non-word char at the end
# and \b won't match at end-of-string after a period.
_NAME_SUFFIXES = re.compile(
    r"\b("
    r"S\. DE R\.L\.|S\. DE C\.V\.|S DE RL|SRL DE CV|"
    r"S\.A\.S\.|S A S|S\.A\.|S\.R\.L\.|"
    r"S\. EN C\.|C\. POR A\.|C POR A|"
    r"E\.I\.R\.L\.|"
    r"S\.C\.|S\.C|S\.C\.|S\.L\.|S\.L|"
    r"SRL|LLC|SA|SAS|EIRL|INC|CORP|LTD|SAPI|SPA|LTDA|CA|RNC"
    r")(?![a-zA-Z\u00C0-\u024F])",
    re.IGNORECASE,
)

_TLD_TYPOS: dict[str, str] = {
    "comm": "com",
    "con": "com",
    "cmo": "com",
    "ner": "net",
    "ogr": "org",
}

_CM_WARNING_SENTINEL = "__WARN_CM_TLD__"


def normalize_name(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    text = re.sub(r"\s+", " ", value.strip())
    result = text.title()
    result = _NAME_SUFFIXES.sub(lambda m: m.group(0).upper(), result)
    return result


def normalize_phone(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    digits = re.sub(r"\D", "", value.strip())
    if len(digits) == 10:
        return f"+1 {digits[:3]} {digits[3:6]} {digits[6:]}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+1 {digits[1:4]} {digits[4:7]} {digits[7:]}"
    if len(digits) >= 12 and digits.startswith("1"):
        return f"+{digits[:1]} {digits[1:4]} {digits[4:7]} {digits[7:11]}"
    return "+" + digits


def normalize_email(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    email = value.strip().lower()
    email = re.sub(r"\s+", "", email)
    email = re.sub(r"\.com\.com$", ".com", email)
    for typo, fix in _TLD_TYPOS.items():
        email = re.sub(rf"\.{typo}$", f".{fix}", email)
    if email.endswith(".cm"):
        email += _CM_WARNING_SENTINEL
    return email


def normalize_plan(value: Any) -> str:
    text = str(value or "").strip().lower().replace("$", "")
    match = re.search(r"(650|1500|2500)", text)
    if not match:
        raise ValueError("plan must be one of 650, 1500, or 2500")
    return match.group(1)


def normalize_budget(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("USD", "").replace("usd", "").replace("$", "").strip()
    text = re.sub(r"[^0-9.,]", "", text)
    if not text:
        raise ValueError("ad_budget_30_days_usd is required")
    return text


def _strip(value: Any) -> str:
    return str(value or "").strip()


_FIELD_NORMALIZERS: dict[str, Any] = {
    "plan": normalize_plan,
    "company_name": normalize_name,
    "company_sector": lambda v: _strip(v).lower(),
    "company_whatsapp": normalize_phone,
    "company_document": _strip,
    "owner_name": normalize_name,
    "owner_whatsapp": normalize_phone,
    "owner_email": normalize_email,
    "owner_identity_document": _strip,
    "ad_budget_30_days_usd": normalize_budget,
}


def normalize_form_data(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    normalized: dict[str, Any] = {}
    warnings: list[str] = []

    for field, normalizer in _FIELD_NORMALIZERS.items():
        raw = data.get(field)
        try:
            value = normalizer(raw)
        except ValueError as exc:
            value = ""
            warnings.append(f"{field}: {exc}")

        if field == "owner_email" and isinstance(value, str) and value.endswith(_CM_WARNING_SENTINEL):
            value = value[: -len(_CM_WARNING_SENTINEL)]
            warnings.append(
                f"owner_email: .cm TLD preserved (Cameroon ccTLD); "
                "if you meant .com, correct manually"
            )

        normalized[field] = value

    for key, value in data.items():
        if key not in normalized:
            normalized[key] = value

    return normalized, warnings
