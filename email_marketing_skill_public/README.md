# Email Marketing Skill Agent Notes

This folder is being converted from a one-client prototype into a reusable coding-agent skill. The skill generates 10 branded email templates, verifies them, and creates a Resend drip automation that sends one email every 3 days.

## Current Contract

The reusable config schema is the source of truth.

Required fields:

- `company_name`
- `from_email`
- `reply_to`
- `calendly_url`
- `logo_path`
- `primary_color`
- `secondary_color`
- `language`
- `event_name`
- `template_titles` with exactly 10 entries
- `social_urls` with keys `instagram`, `linkedin`, `facebook`, `whatsapp`
- `prospect_variables` equal to `NOMBRE` and `CORREO`

`social_urls` keys must exist, but each URL value can be an empty string. Empty social URLs are omitted from generated templates.

The client Calendly URL is the only CTA URL. Do not hard-code any other scheduling link.

## Agent Workflow

1. Read the campaign config.
2. Generate templates with `scripts/generate_campaign.py`.
3. Verify static output with `scripts/verify_campaign.py`.
4. Run `scripts/setup_resend.py --dry-run`.
5. Ask for explicit approval before `--apply`.
6. Ask for explicit approval before any test or live event trigger.

## Files Agents Should Edit

- `SKILL.md`
- `README.md`
- `templates/email_base.html`
- `scripts/generate_campaign.py`
- `scripts/verify_campaign.py`
- `scripts/setup_resend.py`
- `scripts/trigger_resend_event.py`
- `examples/campaign.config.example.json`
- `references/resend_automation_notes.md`
- `tests/test_email_marketing_skill.py`

## Files Agents Should Not Edit Without Explicit Need

- `.env`
- Generated `emails/*.html` unless regenerating the campaign.
- Generated `automation.generated.json` unless regenerating the campaign.
- Generated `resend.generated.json` unless applying Resend setup.
- `scripts/node_modules/`
- Legacy client prototype files unless the task is migration cleanup.

## Future Changes Queue

- Add multilingual copy packs.
- Add industry-specific campaign angles.
- Add HTML preview screenshot generation.
- Add a Resend MCP execution path.
- Add CRM adapter examples.
- Add unsubscribe topic support.
- Add deliverability linting for spammy phrases, missing plain text, and image-heavy emails.
- Add brand color extraction from logos.

## Safety Rules

- No live Resend calls without `--apply`.
- No automation activation without explicit approval.
- No secrets in committed files.
- Run the verifier before Resend setup.
- Keep `calendly_url` as the only CTA source.
- Keep template variables limited to `NOMBRE` and `CORREO` until the schema changes.
