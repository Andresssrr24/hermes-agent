# Resend Automation Notes

Use Resend Templates and Automations for the 10-email drip campaign.

## Resend MCP

If a Resend MCP server is available, agents can use it instead of direct API scripts.

Stdio setup:

```bash
npx -y resend-mcp
```

Required environment variable:

```bash
RESEND_API_KEY=your_resend_api_key
```

Required capabilities:

- Create and publish templates.
- Create automations.
- Send events.
- List automation runs for verification.

## Automation Shape

The campaign automation must have:

- 1 trigger step using the configured `event_name`.
- 10 send-email steps using published template IDs.
- 9 delay steps with duration `3 days`.
- Sequential connections: `start -> email01 -> delay01 -> email02 -> ... -> email10`.

## Template Variables

Use only:

- `NOMBRE`
- `CORREO`

The event payload should include both variables. The event recipient email should match `CORREO`.

## Safety

- Run static verification before Resend setup.
- Create automations as disabled by default.
- Do not activate automations without explicit user approval.
- Do not trigger live contacts during verification.
