# Make MCP Documentation

## Overview

This project integrates Make.com's Model Context Protocol (MCP) server to enable programmatic access to your Make.com automations.

## Quick Start

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the integration:
   ```bash
   npm start
   ```

## Available Operations

The Make MCP server may expose the following operations (depending on your configuration):

### Tools
- `list_scenarios` - List all scenarios in your organization
- `run_scenario` - Execute a specific scenario
- `trigger_webhook` - Trigger a webhook manually
- `create_connection` - Create a new connection
- `list_connections` - List all connections

### Local Make REST MCP Tools

The local server at `server.js` exposes Make REST API tools over stdio MCP:

- `make_list_teams` - List teams for an organization
- `make_get_team` - Get one team
- `make_list_connections` - List connections for a team
- `make_list_hooks` - List hooks for a team
- `make_create_hook` - Create a generic Make hook
- `make_create_meta_lead_ads_hook` - Create a Meta/Facebook Lead Ads hook and return `hook.id` for `__IMTHOOK__`
- `make_get_hook` - Get one hook
- `make_ping_hook` - Check hook active/attached/learning status
- `make_enable_hook` - Enable a hook
- `make_disable_hook` - Disable a hook
- `make_list_scenarios` - List scenarios
- `make_list_team_scenarios` - List scenarios for the configured/current team
- `make_list_organization_scenarios` - List scenarios for an organization
- `make_create_scenario` - Create a scenario from a blueprint
- `make_get_scenario` - Get scenario details
- `make_get_scenario_blueprint` - Get a scenario blueprint
- `make_update_scenario` - Update scenario blueprint, scheduling, folder, or name

Hook deletion is intentionally not exposed.

For Meta/Facebook connections, use the connection type filter `facebook`. For Google Sheets, use `google`.

Meta Lead Ads hook creation requires both `pageId` and `formId` in addition to the Facebook connection ID.

For scenario listing, prefer `make_list_team_scenarios` or `make_list_organization_scenarios` over the advanced `make_list_scenarios` tool. Do not pass `0` for unused optional IDs such as `organizationId`, `folderId`, or `teamId`; omit the fields instead. The local server sanitizes common `0` and empty-array values to protect against agent auto-fill mistakes.

### Resources
- `organization://info` - Organization information
- `scenario://{id}` - Specific scenario details
- `webhook://{id}` - Webhook configuration

## Security

⚠️ **Important**: Never commit your `.env` file or expose your API key in public repositories.

## Support

- [Make.com Help Center](https://www.make.com/en/help)
- [MCP Documentation](https://modelcontextprotocol.io/)
