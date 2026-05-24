# Company Contracts Hermes Skill Template

This repository contains a sanitized Hermes skill template for generating ready-to-sign contract PDFs from approved company templates.

This public-safe copy intentionally excludes production PDF templates, real company identifiers, real representative data, and real client examples. Treat it as a framework for a private deployment, not as a finished production contract package.

## Contents

- `SKILL.md` describes how Hermes should use the skill.
- `INSTALL_CONTEXT.md` explains the operational context for a Hermes agent.
- `scripts/render_contract.py` renders contract PDFs from fixed templates.
- `scripts/calibrate_template.py` creates coordinate grids for PDF layout tuning.
- `references/plans.json` contains placeholder plan and professional-party metadata.
- `references/fields.json` contains sample field placement coordinates.
- `templates/` is intentionally empty except for documentation; private templates belong there in production.
- `output/` is for generated PDFs and sample input data.

## Production Use

Before using this template in production, provide private PDF templates, replace all placeholder metadata, recalibrate `references/fields.json`, and review all generated contracts with appropriate business/legal approval.

Generated PDFs should not be committed to version control.
