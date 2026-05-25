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
- To enable Drive uploads, complete Google Workspace OAuth with the bundled `google-workspace` skill.
- Set `google_drive.folder_id` in `references/plans.json` to your fixed Drive folder and enable `upload_automatically` if desired.

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
| Generate PDF without Drive upload | `scripts/render_contract.py --no-drive-upload` |
| Upload existing PDF | `scripts/upload_contract_to_drive.py` |
| Process confirmed n8n jobs | `scripts/poll_ready_contracts.py` |
| Check pending confirmed jobs | `scripts/poll_ready_contracts.py --summary --insecure-skip-verify` |
| Generate calibration grid | `scripts/calibrate_template.py` |
| Adjust layout | `references/fields.json` |
| Configure plans and professional data | `references/plans.json` |

## Procedure

1. Confirm the selected plan exists in `references/plans.json`.
2. Check every required form field is present.
3. Normalize the ad budget to a USD number without changing the user's value.
4. Run `scripts/render_contract.py` with structured input.
5. Verify the command returns `success: true` and an output path.
6. If Drive upload is enabled, verify `drive.webViewLink` and return it with the PDF path.

If placement looks wrong, generate a grid with `scripts/calibrate_template.py` and adjust `references/fields.json`.

## n8n Onboarding Flow

The client form can send intake data to n8n without a plan. n8n should ask an internal user on WhatsApp to confirm which plan/price was paid before Hermes generates a contract.

Accepted WhatsApp replies are `650`, `$650`, `Plan de Inicio`, `1500`, `$1500`, `Plan Pro`, `2500`, `$2500`, or `Plan Elite`. If more than one submission is pending, n8n should require the submission ID in the reply.

After n8n marks a job as `ready_for_contract`, run:

```bash
N8N_READY_CONTRACTS_URL="https://n8n.example/webhook/ready-contracts" \
N8N_CONTRACT_COMPLETED_URL="https://n8n.example/webhook/contract-completed" \
N8N_CONTRACTS_TOKEN="..." \
python3 scripts/poll_ready_contracts.py
```

The ready-job payload may be either a single object, a list, or an object with `jobs`, `data`, `items`, or `ready`. Each job must include `submission_id`, `plan`, and all required contract fields. The poller posts the renderer result back to n8n so n8n can send the final link over WhatsApp.

## Pending Contract Questions

When the user asks `Tenemos contratos pendientes?`, `Hay contratos pendientes?`, `Revisa contratos pendientes`, or similar, interpret this as a request to check n8n for confirmed jobs with `ready_for_contract` status. These are submissions where an internal user already confirmed the paid plan.

Check without generating contracts first:

```bash
N8N_READY_CONTRACTS_URL="https://n8n.example/webhook/ready-contracts" \
N8N_CONTRACTS_TOKEN="..." \
N8N_INSECURE_SKIP_VERIFY=true \
python3 scripts/poll_ready_contracts.py --summary --insecure-skip-verify
```

If `ready_count` is `0`, tell the user there are no confirmed contracts ready to generate. If jobs are returned, summarize each one by `submission_id`, `company_name`, `owner_name`, `owner_email`, `plan`, and `ad_budget_30_days_usd`, then ask whether to generate them unless the user already asked to process/generate.

When the user asks to process or generate pending contracts, run:

```bash
N8N_READY_CONTRACTS_URL="https://n8n.example/webhook/ready-contracts" \
N8N_CONTRACT_COMPLETED_URL="https://n8n.example/webhook/contract-completed" \
N8N_CONTRACTS_TOKEN="..." \
N8N_INSECURE_SKIP_VERIFY=true \
python3 scripts/poll_ready_contracts.py --insecure-skip-verify
```

After processing, report successful contracts with local PDF paths and Drive links. Report failed jobs with their `submission_id` and error. Do not generate contracts for submissions still awaiting plan confirmation.

## Pitfalls

- Do not include fields that your intake form does not collect.
- Do not invent missing identity numbers, company documents, email addresses, or phone numbers.
- Do not change legal clauses, prices, plan deliverables, renewal terms, or cancellation terms.
- Do not use example client data from templates in a generated contract.
- Replace all placeholder professional-party data before production use.
- If `drive.success` is false but top-level `success` is true, the local PDF was created; fix OAuth or folder permissions and upload the same PDF with `scripts/upload_contract_to_drive.py`.
- Do not generate contracts for n8n onboarding submissions until the company user confirms the paid plan/price.
- `Pending contracts` means confirmed `ready_for_contract` jobs, not every submitted onboarding form.
- Do not infer the plan from campaign budget; use only the confirmed plan from n8n/WhatsApp.

## Verification

- The output PDF exists.
- The old example client name is not visible in the filled sections.
- The new company and owner data are visible.
- The configured professional-party data is present where expected.
- No unapproved fields were added.
- Signature areas remain ready to sign manually.
- If Drive upload is enabled, the shared link opens without requesting access.
