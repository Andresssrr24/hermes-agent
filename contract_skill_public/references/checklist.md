# Contract Generation Checklist

- Confirm the selected plan is exactly one of the supported plan keys.
- Confirm every required form field is present.
- Do not add a client address unless your intake form explicitly collects one.
- Use configured professional-party data from `references/plans.json` when company address text is needed.
- Do not change legal terms, prices, renewal terms, cancellation terms, or plan deliverables without explicit business approval.
- Generate a PDF ready for manual signature; do not add digital signature automation.
- Verify the output PDF exists and opens before returning it.
- If field placement looks wrong, use `scripts/calibrate_template.py` and update `references/fields.json`.
