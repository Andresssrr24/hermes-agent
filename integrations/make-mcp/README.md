# Make MCP Integration

This project integrates Make.com's MCP (Model Context Protocol) server.

## ✅ Connection Status

**Status**: Successfully connected to Make MCP server

**Server Details:**
- **URL**: `https://us2.make.com/mcp/server/c7e46032-add9-4716-8735-43f9127d27ce`
- **Protocol Version**: 2024-11-05
- **Server**: MakeMCPVHost (Opencode)
- **Status**: Active and accessible

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Test Connection

```bash
npm start
```

This will connect to the Make MCP server and list available capabilities.

### 3. Run Examples

```bash
node examples.js
```

This demonstrates various MCP operations.

### 4. Run Local Make MCP Tools

This repo also includes a local MCP server that exposes Make REST API tools for teams, connections, and hooks.

```bash
npm run mcp:inspect
```

Use the local MCP server with OpenCode/Hermes by registering `server.js` as a local MCP server.

## Project Structure

```
make-mcp/
├── index.js          # Main connection test script
├── examples.js       # Example usage demonstrations
├── package.json      # Project dependencies
├── .env             # Environment variables (contains credentials)
├── .env.example     # Example environment file
├── .gitignore       # Git ignore rules
└── README.md        # This file
```

## Configuration

Environment variables (configured in `.env`):

| Variable | Description |
|----------|-------------|
| `MAKE_MCP_SERVER_URL` | Make MCP server URL |
| `MAKE_MCP_API_KEY` | API key for authentication |
| `MAKE_API_TOKEN` | Make REST API token for local MCP tools |
| `MAKE_API_ZONE` | Make zone, for example `us2`, `us1`, `eu1`, or `eu2` |
| `MAKE_TEAM_ID` | Optional default Make team ID |

## Current Status

The integration successfully connects to the Make MCP server and can:

- ✅ Establish a session
- ✅ Communicate via HTTP/SSE
- ✅ List available tools (currently none configured)
- ✅ List available resources (currently none configured)
- ✅ List available prompts (currently none configured)

The local MCP server in `server.js` exposes:

- `make_list_teams`
- `make_get_team`
- `make_list_connections`
- `make_list_hooks`
- `make_create_hook`
- `make_create_meta_lead_ads_hook`
- `make_get_hook`
- `make_ping_hook`
- `make_enable_hook`
- `make_disable_hook`
- `make_list_scenarios`
- `make_list_team_scenarios`
- `make_list_organization_scenarios`
- `make_create_scenario`
- `make_get_scenario`
- `make_get_scenario_blueprint`
- `make_update_scenario`

It intentionally does not expose hook deletion.

For Meta/Facebook connections, use the connection type filter `facebook`. For Google Sheets, use `google`.

Meta Lead Ads hook creation requires both `pageId` and `formId` in addition to the Facebook connection ID.

For scenario listing, prefer `make_list_team_scenarios` or `make_list_organization_scenarios` over the advanced `make_list_scenarios` tool. Do not pass `0` for unused optional IDs such as `organizationId`, `folderId`, or `teamId`; omit the fields instead. The local server sanitizes common `0` and empty-array values to protect against agent auto-fill mistakes.

Required Make API scopes for all local tools:

- `teams:read`
- `connections:read`
- `hooks:read`
- `hooks:write`
- `scenarios:read`
- `scenarios:write`

### OpenCode MCP Configuration

Register the local server in OpenCode config:

```json
{
  "mcp": {
    "make-local": {
      "type": "local",
      "command": ["node", "/Users/admin/Projects/make-mcp/server.js"],
      "enabled": true,
      "env": {
        "MAKE_API_TOKEN": "${MAKE_API_TOKEN}",
        "MAKE_API_ZONE": "us2",
        "MAKE_TEAM_ID": "${MAKE_TEAM_ID}"
      }
    }
  }
}
```

Restart OpenCode after changing MCP configuration.

### Next Steps

To make use of this integration, you need to **configure tools, resources, and prompts** on the Make.com MCP server:

1. Log in to your Make.com account
2. Navigate to the MCP server configuration
3. Add scenarios, connections, and other resources you want to expose via MCP
4. Re-run this client to see and use the configured capabilities

## Usage

### Basic Connection

```javascript
import { SimpleMakeMCPClient } from './index.js';

const client = new SimpleMakeMCPClient(
  'https://us2.make.com/mcp/server/c7e46032-add9-4716-8735-43f9127d27ce',
  'yB1t0chcDwBj9ICAbcokuRlR-XPRkpcVJ9MMkq9n7H'
);

// List tools
const tools = await client.listTools();

// Call a tool
const result = await client.callTool('toolName', { param: 'value' });
```

### Available Operations

Once tools are configured on the server:

```javascript
// List all tools
const { tools } = await client.listTools();

// Call a tool
const result = await client.callTool('scenario_name', {
  input: 'value'
});

// List resources
const { resources } = await client.listResources();

// Read a resource
const data = await client.readResource('resource://uri');
```

## Security

⚠️ **Important Security Notes**:

1. The `.env` file contains sensitive credentials. Never commit it to version control.
2. The `.gitignore` file is already configured to exclude `.env`.
3. Keep your API key secure and rotate it regularly.
4. Use environment variables in production instead of hardcoded values.

## Troubleshooting

### Connection Errors

If you see connection errors:

1. **Verify the Server URL**: Ensure the URL matches your Make MCP server
2. **Check API Key**: Confirm the API key is valid and hasn't expired
3. **Network Access**: Ensure your network allows HTTPS connections to `us2.make.com`

### No Tools/Resources Available

If the server reports no tools or resources:

1. **Configure on Make.com**: Tools and resources must be configured in your Make.com MCP dashboard
2. **Check Permissions**: Ensure your API key has access to the scenarios you want to expose
3. **Re-check Server URL**: Different servers may have different configurations

## Documentation

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [Make.com Help Center](https://www.make.com/en/help)

## License

MIT
