# Contract Skill Installation Context

## Purpose

This package is a sanitized private-skill template for generating ready-to-sign service contract PDFs from approved templates.

It is not a legal drafting system. It does not create new contract terms, negotiate clauses, alter pricing logic, or modify service scope. Its purpose is to take validated client form data and render that data into fixed contract templates supplied by the installing company.

## What Is Being Installed

The installation adds a Hermes skill named `company-contracts`.

The skill contains:

- A `SKILL.md` file that tells Hermes when and how to use the contract generator.
- A PDF renderer script that fills approved contract templates.
- JSON reference files that define plan metadata, professional-party data, and PDF field placement.
- A calibration helper for adjusting PDF coordinates if a template layout changes.
- An output directory where generated contracts can be written.

This sanitized public copy intentionally does not include production PDF templates or real company/client data.

## Available Plans

The default sample configuration uses three plan keys:

- `650`
- `1500`
- `2500`

These plan keys are placeholders and can be changed in `references/plans.json` and `references/fields.json`.

Each plan can have its own PDF template and field map because contract layouts often differ by plan.

## Core Behavior

When Hermes uses this skill, it should:

1. Identify which configured plan the user wants.
2. Collect the required company and owner form fields.
3. Validate that no required data is missing.
4. Use the correct PDF template for the selected plan.
5. Redact old sample client data from the template.
6. Insert the new client data into calibrated positions.
7. Preserve the approved legal language and plan structure.
8. Generate a PDF ready for manual signature.
9. Return the generated PDF path.

The generated contract is intended to be sent or shared externally after human review.

## Required Client Data

The sample skill expects data from a client intake form:

- `plan`
- `company_name`
- `company_sector`
- `company_whatsapp`
- `company_document`
- `owner_name`
- `owner_whatsapp`
- `owner_email`
- `owner_identity_document`
- `ad_budget_30_days_usd`

The skill can also accept an optional contract date. If no contract date is provided, the renderer uses the current date.

For configured templates that include contract dates, the date can be rendered in Spanish format, for example:

`23 DE MAYO DE 2026`

## Professional-Party Data

Professional-party metadata is stored in:

`references/plans.json`

This includes placeholder values for:

- Company legal name
- DBA
- Representative name
- Representative title
- Representative identity number
- Company tax ID
- Company address

Replace these placeholders before using the skill in production.

## Client Address Policy

The sample intake data does not include a client address.

Generated contracts should not include a client address unless the business process is changed and the intake form begins collecting it.

This is intentional. Templates may contain old sample data, but final rendered contracts should use only approved intake fields.

## Template Strategy

The skill uses static PDF templates as the source of truth.

It does not rebuild contracts from Markdown, HTML, or generated prose. Instead, it overlays validated data onto existing PDFs using calibrated coordinates.

This approach preserves:

- Contract layout
- Branding
- Page count
- Signature areas
- Existing legal language
- Approved plan structure

## PDF Rendering Model

The renderer works by applying manual redaction blocks and text insertion blocks.

Each plan has field definitions in:

`references/fields.json`

The field map controls:

- Which page to edit
- Which rectangle to redact
- Where new text should be inserted
- Font size
- Font style
- Line spacing
- Uppercase formatting
- Multi-run text formatting for bold labels and regular sentence text

Some blocks use separate redaction and insertion positions. This allows the script to remove old sample text while placing new text in a visually better position.

## Important Rendering Details

The renderer uses PyMuPDF to manipulate PDFs.

It performs real PDF redactions before inserting new text. This removes old sample data from the PDF text layer instead of only covering it visually with white boxes.

The renderer also supports:

- Spanish month names
- Contract date normalization
- Plan normalization
- Budget normalization
- Deterministic output filenames
- Bold and regular font runs
- Separate `redact_rect` and `insert_at` placement controls

## Output Behavior

Generated PDFs are written to the skill output directory unless a custom output path is provided.

The output filename is based on:

- Contract prefix
- Client company slug
- Selected plan
- Generation date

Generated PDFs are operational artifacts and should not be treated as source files.

## Safety Boundaries

Hermes should not:

- Invent missing client data.
- Add fields that are not collected by the intake process.
- Change legal terms.
- Change cancellation terms.
- Change renewal terms.
- Change plan pricing.
- Change deliverables.
- Add custom legal clauses.
- Add digital signatures.
- Recreate the contract from scratch.

If a user asks for legal wording changes, Hermes should make it clear that this changes approved contract terms and should be reviewed by a qualified legal professional.

## Verification Expectations

After generation, Hermes should verify:

- The PDF exists.
- The selected plan is correct.
- The old sample client data is removed.
- The new company name is present.
- The new owner name is present.
- The owner identity document is present.
- The company document is present.
- The contract date is correct where applicable.
- The professional-party data is present.
- No unapproved fields were added.
- Signature areas remain ready for manual signing.

## Known Layout Notes

PDFs are coordinate-based. Small visual changes in templates can require field-map calibration.

Use `references/fields.json` to adjust placement and `scripts/calibrate_template.py` to create coordinate-grid PDFs when tuning layout.

## Operational Assumptions

The installed Hermes environment must be able to run Python scripts and manipulate PDFs.

The skill assumes that production templates are approved business templates and that changes to pricing, scope, or legal language are managed outside the renderer.

This sanitized package is a public-safe framework copy. Production templates, real company data, and real client examples should remain private.
