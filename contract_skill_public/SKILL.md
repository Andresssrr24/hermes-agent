---
name: company-contracts
description: Generate fixed company contract PDFs.
version: 1.0.0
author: Your Company, Hermes Agent
license: Private Template
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [contracts, pdf, private]
    category: productivity
    related_skills: [ocr-and-documents]
---

# Company Contracts Skill

This private-skill template generates ready-to-sign service contract PDFs from approved templates. It does not draft new legal terms, change plan scope, or modify payment and cancellation clauses.

Use the helper script in `scripts/render_contract.py` for final PDF generation. Do not manually rewrite the contract body unless the user explicitly requests legal text changes and acknowledges that legal review is required.

## When to Use

- Generate a contract for one of the configured plans.
- Replace example client data in approved PDF templates with form data.
- Produce a PDF ready for manual signature.
- Regenerate a contract after a typo correction in client data.

Do not use this skill to negotiate terms, add clauses, generate a different service agreement, or produce digital signatures.

## Prerequisites

- Add your private PDF templates to `templates/650.pdf`, `templates/1500.pdf`, and `templates/2500.pdf` or update `references/plans.json` to match your plan keys.
- Ensure PyMuPDF is available in the Python environment used by Hermes.
- Before production use, set professional-party metadata in `references/plans.json`.

The sample configuration intentionally uses placeholder company and client data.

## Required Fields

Collect these required fields from the intake form:

- `plan`: plan key, such as `650`, `1500`, or `2500`.
- `company_name`: client company name.
- `company_sector`: client company sector.
- `company_whatsapp`: client company WhatsApp or phone number.
- `company_document`: company identification document.
- `owner_name`: owner or authorized signer name.
- `owner_whatsapp`: owner WhatsApp or phone number.
- `owner_email`: owner email.
- `owner_identity_document`: owner identity document.
- `ad_budget_30_days_usd`: advertising budget for 30 days, in USD.

Prefer JSON input for fewer quoting issues:

```json
{
  "plan": "2500",
  "company_name": "SAMPLE CLIENT LLC",
  "company_sector": "real estate",
  "company_whatsapp": "+1 000 000 0000",
  "company_document": "SAMPLE-COMPANY-ID",
  "owner_name": "Sample Owner",
  "owner_whatsapp": "+1 000 000 0000",
  "owner_email": "owner@example.invalid",
  "owner_identity_document": "SAMPLE-OWNER-ID",
  "ad_budget_30_days_usd": "2500"
}
```

## Quick Reference

| Task | Tool |
| --- | --- |
| Generate PDF | `scripts/render_contract.py` |
| Generate calibration grid | `scripts/calibrate_template.py` |
| Adjust layout | `references/fields.json` |
| Configure plans and professional data | `references/plans.json` |

## Procedure

1. Confirm the selected plan exists in `references/plans.json`.
2. Check every required form field is present.
3. Normalize the ad budget to a USD number without changing the user's value.
4. Run `scripts/render_contract.py` with structured input.
5. Verify the command returns `success: true` and an output path.
6. Return the PDF path to the user.

If placement looks wrong, generate a grid with `scripts/calibrate_template.py` and adjust `references/fields.json`.

## Pitfalls

- Do not include fields that your intake form does not collect.
- Do not invent missing identity numbers, company documents, email addresses, or phone numbers.
- Do not change legal clauses, prices, plan deliverables, renewal terms, or cancellation terms.
- Do not use example client data from templates in a generated contract.
- Replace all placeholder professional-party data before production use.

## Verification

- The output PDF exists.
- The old example client name is not visible in the filled sections.
- The new company and owner data are visible.
- The configured professional-party data is present where expected.
- No unapproved fields were added.
- Signature areas remain ready to sign manually.
