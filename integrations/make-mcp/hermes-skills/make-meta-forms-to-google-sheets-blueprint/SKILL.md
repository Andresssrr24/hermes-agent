---
name: make-meta-forms-to-google-sheets-blueprint
description: Use when a user needs a ready-to-import Make blueprint that sends Meta/Facebook Lead Ads form submissions into Google Sheets.
version: 1.0.0
metadata:
  hermes:
    tags: [make, meta, facebook-leads, google-sheets, automation]
    category: automation
---

# Make Blueprint Generator: Meta Lead Forms to Google Sheets

## Purpose

Use this skill to generate a ready-to-import Make blueprint JSON for a scenario that receives Meta/Facebook Lead Ads submissions and appends each lead to a Google Sheet row.

This is a blueprint-generation skill, not a manual setup checklist. The final result must include valid JSON that can be saved as a `.blueprint.json` file and imported into Make.

## When to Use

Use this skill when the user wants to:

- Create a Make blueprint for Meta/Facebook Lead Ads to Google Sheets.
- Send Facebook or Instagram lead form submissions into Google Sheets.
- Map Meta lead fields and campaign/ad metadata to spreadsheet columns.
- Produce a reusable `.blueprint.json` artifact for Make import.

Do not use this skill for non-Meta lead sources, non-Google-Sheets destinations, or generic Make scenario advice.

## Make MCP Limitation

Current Make MCP availability must be treated separately from blueprint generation.

- If the local `make-local` MCP server exposes `make_create_meta_lead_ads_hook`, use it to create the Meta Lead Ads hook before generating the final blueprint.
- Use the returned `hook.id` as `make_meta_webhook_id` and as the blueprint `__IMTHOOK__` value.
- If the hook tool is unavailable, ask the user for `make_meta_webhook_id` or an exported source blueprint whose hook should be reused.
- Do not claim the scenario was created in Make unless an MCP tool or Make API operation actually created it.
- Only execute scenario creation/import through MCP when an explicit tool such as `create_scenario`, `import_blueprint`, or equivalent is available.
- If no scenario import tool is available, the status is `Blueprint generated - manual import required` even when the hook was created successfully.

## Required Information

Ask for any missing required information before generating the blueprint.

```yaml
scenario_name: ""
meta_page_id: ""
meta_form_id: ""
google_sheets_url: ""
spreadsheet_id: ""
sheet_name: ""
sheet_id: ""
has_headers: true
make_meta_webhook_id: null
make_google_connection_id: null
make_team_id: null
make_meta_connection_id: null
column_names:
  - ""
fields_to_map:
  - make_source_path: ""
    sheet_column: ""
meta_connection_label: ""
google_connection_label: ""
```

### Required Field Notes

- `scenario_name` is the Make scenario name.
- `meta_page_id` and `meta_form_id` identify the intended Lead Ads source and must not be invented.
- `google_sheets_url` must be a Google Sheets URL.
- `spreadsheet_id` is the value between `/d/` and the next `/` in the Google Sheets URL. Derive it when possible and ask the user to confirm it.
- `sheet_name` is the visible tab name.
- `sheet_id` is usually the visible tab name for the Make `google-sheets:addRow` mapper. If the user has an existing Make-exported blueprint that uses another value, use that value.
- `has_headers` should normally be `true`.
- `make_meta_webhook_id` is the numeric Make webhook ID for the Facebook Lead Ads trigger. It is required for ready-to-import output unless the user provides an exported source blueprint whose hook should be reused.
- `make_google_connection_id` is the numeric Make Google connection ID. It is required for ready-to-import output unless the user provides an exported source blueprint whose connection should be reused.
- `make_team_id` is required when the agent will create the Meta Lead Ads hook through MCP.
- `make_meta_connection_id` is required when the agent will create the Meta Lead Ads hook through MCP. Use `make_list_connections` if available to help the user find it.
- `column_names` must match the Google Sheet headers exactly when `has_headers` is `true`.
- `fields_to_map` must use Make mapper paths, not only friendly field labels.
- `meta_connection_label` and `google_connection_label` are human labels to document which accounts must be selected during import. Do not fabricate numeric connection IDs.

## Supported Make Modules

Use these Make blueprint module IDs:

| Purpose | UI label | Blueprint module ID |
|---|---|---|
| Meta Lead Ads trigger | Facebook Lead Ads / New Lead | `facebook-lead-ads:NewLeadMultiple` |
| Google Sheets row append | Google Sheets / Add a Row | `google-sheets:addRow` |

Do not use generic module names in the blueprint JSON. UI labels may be included in the summary only.

## Common Make Source Paths

Use these common Make output paths when the user confirms the field exists:

| Lead value | Make source path |
|---|---|
| Full name | `{{1.data.full_name}}` |
| Email | `{{1.data.email}}` |
| Phone number | `{{1.data.phone_number}}` |
| Country | `{{1.data.country}}` |
| Lead ID | `{{1.leadgenId}}` |
| Form ID | `{{1.formId}}` |
| Page ID | `{{1.pageId}}` |
| Created date | `{{1.dateCreated}}` |
| Campaign name | `{{1.campaignName}}` |
| Ad set name | `{{1.adsetName}}` |
| Ad name | `{{1.adName}}` |
| Platform | `{{1.platform}}` |

Custom question fields are usually under `{{1.data.<normalized_question_key>}}`. Ask the user for the exact Make field key or infer it only from an exported Make bundle/interface supplied by the user.

Do not assume Meta API field names such as `created_time`, `campaign_name`, or `adset_name` are valid Make mapper paths. Convert them to Make paths only after confirmation.

## Input Validation

Before generating JSON, validate that:

- `scenario_name` is present.
- `meta_page_id` is present.
- `meta_form_id` is present.
- `google_sheets_url` starts with `https://docs.google.com/spreadsheets/d/`.
- `spreadsheet_id` is present or derived from the URL.
- `sheet_name` and `sheet_id` are present.
- `make_meta_webhook_id` is present, numeric, created through `make_create_meta_lead_ads_hook`, or explicitly sourced from a user-provided blueprint.
- `make_google_connection_id` is present, numeric, or explicitly sourced from a user-provided blueprint.
- `column_names` is non-empty.
- Every `fields_to_map` item has both `make_source_path` and `sheet_column`.
- Every `sheet_column` exists in `column_names` when `has_headers` is `true`.
- No numeric Make connection ID or webhook ID is invented.

If any item is missing, ask one concise question listing only the missing fields.

## MCP Hook Creation Flow

When the local Make MCP tools are available, create the Meta Lead Ads hook before generating the blueprint:

1. If `make_team_id` is missing and `MAKE_TEAM_ID` is not configured, ask for the Make team ID or use `make_list_teams` if the organization ID is available.
2. If `make_meta_connection_id` is missing, use `make_list_connections` with the team ID to find the Meta/Facebook Lead Ads connection, or ask the user to provide the connection ID.
3. Call `make_create_meta_lead_ads_hook` with:
   - `name`: a clear hook name derived from `scenario_name`, max 128 characters
   - `teamId`: `make_team_id`
   - `connectionId`: `make_meta_connection_id`
   - `pageId`: `meta_page_id`
   - `formId`: `meta_form_id`
   - `typeName`: default `facebook-lead-ads-new-event` unless the user provides a different verified type
4. If Make returns an error about `typeName`, stop and report the error. Ask the user for an existing hook export or verified hook type rather than guessing.
5. Store the returned `hook.id` as `make_meta_webhook_id`.
6. Use `make_ping_hook` when available to inspect hook status, but do not require the hook to be attached before generating the blueprint.

Do not create duplicate hooks if the user already provided a valid `make_meta_webhook_id` and asked to reuse it.

## Blueprint Generation Rules

Generate a Make blueprint JSON object with this structure:

- Top-level `name` equal to `scenario_name`.
- Top-level `flow` array with exactly two modules unless the user asks for additional logic.
- Module `id: 1` is `facebook-lead-ads:NewLeadMultiple`.
- Module `id: 2` is `google-sheets:addRow`.
- The Google Sheets module maps `values` by exact Google Sheet column header.
- The Google Sheets module uses:
  - `spreadsheetId: <spreadsheet_id>`
  - `sheetId: <sheet_id>`
  - `includesHeaders: true` when headers are present
  - `useColumnHeaders: true` when mapping by headers
  - `insertDataOption: INSERT_ROWS`
  - `valueInputOption: USER_ENTERED`
  - `insertUnformatted: false`

### Connection and Hook IDs

Make blueprints exported from active scenarios often include numeric values such as `__IMTCONN__` and `__IMTHOOK__`. These are environment-specific.

- Do not fabricate production connection IDs.
- Do not fabricate production webhook IDs.
- If the user provides actual Make connection IDs or an exported source blueprint to reuse, include them exactly.
- A ready-to-import blueprint must contain real numeric values for `__IMTCONN__` and `__IMTHOOK__`.
- If the user does not provide IDs, stop and ask for them. Do not produce a final ready-to-import blueprint.
- Only if the user explicitly accepts a draft blueprint, use obvious placeholders that force review before import:
  - `"__IMTCONN__": "REPLACE_WITH_GOOGLE_CONNECTION_ID"`
  - `"__IMTHOOK__": "REPLACE_WITH_META_LEAD_ADS_WEBHOOK_ID"`
- If placeholders are used, the status must be `Draft blueprint - replace placeholders before import`, not `Blueprint generated - manual import required`.

## Minimal Blueprint Template

Use this template as the baseline and fill all placeholder values from validated input. Add metadata only when helpful; keep the blueprint minimal. For final ready-to-import output, replace `REPLACE_WITH_META_LEAD_ADS_WEBHOOK_ID` and `REPLACE_WITH_GOOGLE_CONNECTION_ID` with real numeric Make IDs without quotes.

```json
{
  "name": "<scenario_name>",
  "flow": [
    {
      "id": 1,
      "module": "facebook-lead-ads:NewLeadMultiple",
      "version": 2,
      "parameters": {
        "v": "2",
        "fields": [],
        "__IMTHOOK__": "REPLACE_WITH_META_LEAD_ADS_WEBHOOK_ID"
      },
      "mapper": {},
      "metadata": {
        "designer": {
          "x": 0,
          "y": 0
        },
        "parameters": [
          {
            "name": "__IMTHOOK__",
            "type": "hook:facebook-lead-ads-new-event",
            "label": "Webhook",
            "required": true
          },
          {
            "name": "v",
            "type": "hidden"
          },
          {
            "name": "fields",
            "type": "select",
            "label": "Fields",
            "multiple": true
          }
        ]
      }
    },
    {
      "id": 2,
      "module": "google-sheets:addRow",
      "version": 2,
      "parameters": {
        "__IMTCONN__": "REPLACE_WITH_GOOGLE_CONNECTION_ID"
      },
      "mapper": {
        "mode": "fromAll",
        "values": {
          "<Column Header>": "<Make source path>"
        },
        "sheetId": "<sheet_id>",
        "spreadsheetId": "<spreadsheet_id>",
        "includesHeaders": true,
        "insertDataOption": "INSERT_ROWS",
        "useColumnHeaders": true,
        "valueInputOption": "USER_ENTERED",
        "insertUnformatted": false
      },
      "metadata": {
        "designer": {
          "x": 300,
          "y": 0
        }
      }
    }
  ],
  "metadata": {
    "instant": true,
    "version": 1,
    "scenario": {
      "roundtrips": 1,
      "maxErrors": 3,
      "autoCommit": true,
      "autoCommitTriggerLast": true,
      "sequential": false,
      "slots": null,
      "confidential": false,
      "dataloss": false,
      "dlq": false
    },
    "designer": {
      "orphans": []
    }
  }
}
```

## Required Output

Return the result in this order:

1. A short status line.
2. The generated file name, using a safe slug such as `<scenario_name>.blueprint.json`.
3. A mapping table.
4. The complete blueprint JSON in a fenced `json` code block.
5. Import notes and test checklist.

Use this final structure:

````markdown
# Make Blueprint Generated

Status: Blueprint generated - manual import required

File name: <safe-name>.blueprint.json

## Field Mapping

| Google Sheet Column | Make Source Path |
|---|---|
| Full Name | {{1.data.full_name}} |

## Blueprint JSON

```json
{
  "name": "..."
}
```

## Import Notes

- Import this JSON into Make as a blueprint.
- Reconnect/select the Meta Lead Ads webhook for Page ID `<meta_page_id>` and Form ID `<meta_form_id>`.
- Reconnect/select the Google Sheets connection for `<google_connection_label>`.
- Confirm the spreadsheet ID is `<spreadsheet_id>` and the sheet/tab is `<sheet_name>`.

## Test Checklist

- [ ] Blueprint imported into Make
- [ ] Meta Lead Ads webhook selected
- [ ] Correct Meta Page ID selected
- [ ] Correct Meta Form ID selected
- [ ] Google Sheets connection selected
- [ ] Spreadsheet and sheet/tab confirmed
- [ ] Column mappings confirmed
- [ ] Scenario run once
- [ ] Test lead submitted
- [ ] Lead appears as a new Google Sheet row
- [ ] Scenario turned on
````

## Guardrails

- Do not invent Meta Page IDs, Meta Form IDs, Google Sheets URLs, spreadsheet IDs, sheet names, column names, field mappings, connection IDs, or webhook IDs.
- Do not claim the blueprint has been imported unless an actual import action happened.
- Do not claim the scenario is connected until a test lead appears in the Google Sheet.
- Do not output a final ready-to-import blueprint with placeholders for `__IMTCONN__` or `__IMTHOOK__`.
- If using placeholders for a draft blueprint, explicitly call them out in the import notes and state that the file must be edited before import.
- If the user provides only column names, ask which Make source path maps to each column.
- If the user provides friendly Meta field labels, translate them to Make source paths only when unambiguous; otherwise ask for confirmation.
- If the Meta form contains custom questions, ask for the exact Make field keys or an exported Make bundle/interface.
- If the Google Sheet has existing headers, use those headers as the source of truth.
- Keep authorization, blueprint import, scenario run, trigger receipt, row append, and lead-delivery confirmation as separate statuses.

## Troubleshooting Logic

If leads do not appear in Google Sheets, check in this order:

1. Was a test lead submitted after the scenario was enabled or run once?
2. Does the lead appear in Meta Leads Center?
3. Is the Make scenario turned on?
4. Did the Make scenario run in history?
5. Did module `facebook-lead-ads:NewLeadMultiple` receive a bundle?
6. Does the trigger use the correct Page ID and Form ID?
7. Does the Google Sheets module use the correct `spreadsheetId` and `sheetId`?
8. Do the mapped `values` keys exactly match Google Sheet headers?
9. Does the Google account have edit access to the spreadsheet?
10. Does the target sheet/tab exist?
11. Are protected ranges, filters, or required columns blocking row creation?
12. Are custom question paths normalized differently than expected?

## Example Input

```yaml
scenario_name: "Meta Leads to Google Sheets"
meta_page_id: "123456789012345"
meta_form_id: "987654321098765"
google_sheets_url: "https://docs.google.com/spreadsheets/d/1abcDEFghiJKLmnopQRstuVWxyz/edit#gid=0"
spreadsheet_id: "1abcDEFghiJKLmnopQRstuVWxyz"
sheet_name: "Leads"
sheet_id: "Leads"
has_headers: true
make_meta_webhook_id: 2222900
make_google_connection_id: 8285635
make_team_id: 123456
make_meta_connection_id: 654321
column_names:
  - "Full Name"
  - "Email"
  - "Phone"
  - "Created At"
  - "Campaign"
fields_to_map:
  - make_source_path: "{{1.data.full_name}}"
    sheet_column: "Full Name"
  - make_source_path: "{{1.data.email}}"
    sheet_column: "Email"
  - make_source_path: "{{1.data.phone_number}}"
    sheet_column: "Phone"
  - make_source_path: "{{1.dateCreated}}"
    sheet_column: "Created At"
  - make_source_path: "{{1.campaignName}}"
    sheet_column: "Campaign"
meta_connection_label: "Client Meta account"
google_connection_label: "Client Google account"
```
