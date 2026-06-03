---
name: email-marketing-campaign
description: Generate branded Resend drip campaigns.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    category: productivity
    tags:
      - email
      - marketing
      - resend
      - automation
---

# Email Marketing Campaign Skill

This skill generates a 10-email branded drip campaign and prepares a Resend Automation that sends one template every 3 days. It does not activate or trigger live sends until the user explicitly approves the Resend apply/trigger steps.

It uses the client's logo, colors, company name, template titles, social URLs, and Calendly link. The client's Calendly URL is the only CTA source and must appear in every generated template.

## When to Use

Use this skill when a client needs a complete email marketing sequence with reusable HTML templates and Resend automation setup.

Use it for B2B prospecting, onboarding, nurture campaigns, and sales follow-up flows where recipients should receive 10 emails spaced 3 days apart.

Do not use it for one-off transactional emails, password resets, legal notices, or campaigns without recipient consent.

## Prerequisites

Required client inputs:

- Company name.
- Verified Resend sender email.
- Reply-to email.
- Client Calendly URL.
- Logo file path, preferably SVG or PNG.
- Primary and secondary brand colors as hex values.
- 10 template titles/subjects.
- Resend event name, such as `client_company.prospect.created`.
- `social_urls` object with all supported keys present: `instagram`, `linkedin`, `facebook`, `whatsapp`. Values can be empty strings.

Required tools:

- `read_file` to inspect config and templates.
- `patch` to edit generated files or scripts.
- `terminal` to run the generator, verifier, tests, and Resend setup scripts.

Required secret for live Resend calls:

- `RESEND_API_KEY` in the execution environment.

Expected Resend setup:

- Resend account exists.
- Sending domain is verified.
- Sender email belongs to the verified domain.
- The user has confirmed the campaign can be created in the client's Resend account.

## How to Run

Create a campaign config from `examples/campaign.config.example.json`, then run:

```bash
python scripts/generate_campaign.py --config campaign.config.json
python scripts/verify_campaign.py --config campaign.config.json
python scripts/setup_resend.py --config campaign.config.json --dry-run
```

Only after the user approves live Resend changes:

```bash
python scripts/setup_resend.py --config campaign.config.json --apply
```

Only after setup is verified and the user approves a test event:

```bash
python scripts/trigger_resend_event.py --config campaign.config.json --email test@example.com --nombre "Test User" --test-recipient
```

## Quick Reference

Config keys:

- `company_name`: Used as brand name and sender display name.
- `from_email`: Verified Resend sender address.
- `reply_to`: Reply-to address.
- `calendly_url`: Required CTA URL for every email.
- `logo_path`: Logo file used in the header.
- `primary_color`: Main CTA/accent color.
- `secondary_color`: Header gradient color.
- `language`: Campaign language, currently `es` or `en`.
- `event_name`: Resend custom event trigger name.
- `template_titles`: Exactly 10 subject/title strings.
- `social_urls`: Object with `instagram`, `linkedin`, `facebook`, `whatsapp`; values can be empty.
- `prospect_variables`: Must be `NOMBRE` and `CORREO`.

Generated files:

- `emails/email-01.html` through `emails/email-10.html`.
- `automation.generated.json`.
- `resend.generated.json` after live setup.

## Procedure

1. Inspect the campaign config and confirm required client inputs are present.
2. Ensure `calendly_url` is the client's Calendly link and uses HTTPS.
3. Generate the templates with `generate_campaign.py`.
4. Run `verify_campaign.py` and fix every failure before touching Resend.
5. Run `setup_resend.py --dry-run` and review the planned template and automation actions.
6. Ask the user for explicit approval before `--apply`.
7. Run `setup_resend.py --apply` to create and publish templates and create a disabled automation.
8. Verify the created automation graph has 1 trigger, 10 email steps, and 9 delays of `3 days`.
9. Ask the user before sending a test event.
10. Trigger only a test recipient unless the user explicitly asks to connect production CRM/contact flows.

## Pitfalls

- Do not hard-code a non-client Calendly link. Every CTA must come from `calendly_url`.
- Do not keep legacy client copy, URLs, colors, or sender identity in generated output.
- Do not use `EMPRESA` or `PROYECTO` variables. This skill's fixed variables are `NOMBRE` and `CORREO`.
- Do not activate the automation during setup unless the user explicitly asks for activation.
- Do not commit `.env`, API keys, generated Resend IDs for a private client, or Python cache files.
- Do not send live events from CRM data during template verification.

## Verification

Before applying Resend changes, verify:

- Exactly 10 email HTML files exist.
- Every email contains the configured Calendly URL.
- Every email contains `{{{RESEND_UNSUBSCRIBE_URL}}}`.
- Every email contains `{{{NOMBRE}}}`.
- No email contains `{{{EMPRESA}}}` or `{{{PROYECTO}}}`.
- Configured social URLs appear in all templates, and empty social URLs are omitted.
- The generated automation graph has 1 trigger, 10 send-email steps, 9 delay steps, and `3 days` delay duration.
- `setup_resend.py --dry-run` makes no network calls.
