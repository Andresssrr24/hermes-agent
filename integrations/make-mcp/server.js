#!/usr/bin/env node
import dotenv from 'dotenv';
import { z } from 'zod';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createMakeApiClientFromEnv, getDefaultTeamId, MakeApiError } from './make-api.js';

dotenv.config();

const DEFAULT_META_LEAD_ADS_HOOK_TYPE = 'facebook-lead-ads-new-event';

const server = new McpServer({
  name: 'make-local-tools',
  version: '1.0.0'
});

function make() {
  return createMakeApiClientFromEnv();
}

function numberLike(description) {
  return z.union([z.number().int(), z.string().min(1)]).transform((value) => Number(value)).describe(description);
}

function optionalNumberLike(description) {
  return z
    .union([z.number().int(), z.string().min(1)])
    .optional()
    .transform((value) => {
      if (value === undefined) return undefined;
      return Number(value);
    })
    .describe(description);
}

function withDefaultTeamId(args) {
  if (args.teamId !== undefined && args.teamId !== null && args.teamId !== '' && args.teamId !== 0 && args.teamId !== '0') {
    return args;
  }

  const defaultTeamId = getDefaultTeamId();

  if (defaultTeamId) {
    return {
      ...args,
      teamId: Number(defaultTeamId)
    };
  }

  throw new Error('teamId is required unless MAKE_TEAM_ID is configured');
}

function cleanArray(value) {
  if (!Array.isArray(value) || value.length === 0) return undefined;
  return value;
}

function toolResult(data) {
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(data, null, 2)
      }
    ]
  };
}

function toolError(error) {
  const payload = {
    error: error.message,
    ...(error instanceof MakeApiError
      ? {
          status: error.status,
          responseBody: error.responseBody
        }
      : {})
  };

  return {
    isError: true,
    content: [
      {
        type: 'text',
        text: JSON.stringify(payload, null, 2)
      }
    ]
  };
}

function registerTool(name, config, handler) {
  server.registerTool(name, config, async (args) => {
    try {
      return toolResult(await handler(args));
    } catch (error) {
      return toolError(error);
    }
  });
}

registerTool(
  'make_list_teams',
  {
    title: 'List Make Teams',
    description: 'List Make teams for an organization. Requires teams:read scope.',
    inputSchema: {
      organizationId: numberLike('Make organization ID.')
    }
  },
  (args) => make().listTeams(args)
);

registerTool(
  'make_get_team',
  {
    title: 'Get Make Team',
    description: 'Get details for one Make team. Requires teams:read scope.',
    inputSchema: {
      teamId: numberLike('Make team ID.')
    }
  },
  (args) => make().getTeam(args)
);

registerTool(
  'make_list_connections',
  {
    title: 'List Make Connections',
    description: 'List Make connections for a team. Requires connections:read scope.',
    inputSchema: {
      teamId: optionalNumberLike('Make team ID. Optional when MAKE_TEAM_ID is configured.'),
      type: z.array(z.string()).optional().describe('Optional connection type filters, for example facebook or google.'),
      cols: z.array(z.string()).optional().describe('Optional response columns to request from Make.')
    }
  },
  (args) => make().listConnections(withDefaultTeamId(args))
);

registerTool(
  'make_list_hooks',
  {
    title: 'List Make Hooks',
    description: 'List Make hooks for a team. Requires hooks:read scope.',
    inputSchema: {
      teamId: optionalNumberLike('Make team ID. Optional when MAKE_TEAM_ID is configured.'),
      typeName: z.string().optional().describe('Optional hook type name filter.'),
      assigned: z.boolean().optional().describe('When true, return hooks assigned to a scenario.'),
      viewForScenarioId: optionalNumberLike('Optional scenario ID to show hooks available for that scenario.')
    }
  },
  (args) => make().listHooks(withDefaultTeamId(args))
);

registerTool(
  'make_create_hook',
  {
    title: 'Create Make Hook',
    description: 'Create a generic Make hook. Requires hooks:write scope. Does not delete or modify scenarios.',
    inputSchema: {
      name: z.string().min(1).max(128).describe('Hook name, max 128 characters.'),
      teamId: optionalNumberLike('Make team ID where the hook will be created. Optional when MAKE_TEAM_ID is configured.'),
      typeName: z.string().min(1).describe('Make hook type name, such as gateway-webhook or an app-specific hook type.'),
      method: z.boolean().default(false).describe('Whether to include HTTP method in incoming request body for gateway hooks.'),
      headers: z.boolean().default(false).describe('Whether to include HTTP headers in incoming request body for gateway hooks.'),
      stringify: z.boolean().default(false).describe('Whether to stringify JSON payloads.'),
      connectionId: optionalNumberLike('Optional Make connection ID, sent as __IMTCONN__.'),
      formId: z.string().optional().describe('Optional external form ID for app-specific hooks.'),
      pageId: z.string().optional().describe('Optional external page ID for app-specific hooks such as Meta Lead Ads.')
    }
  },
  (args) => make().createHook(withDefaultTeamId(args))
);

registerTool(
  'make_create_meta_lead_ads_hook',
  {
    title: 'Create Meta Lead Ads Hook',
    description: 'Create a Facebook/Meta Lead Ads hook and return hook.id for use as __IMTHOOK__ in Make blueprints. Requires hooks:write scope.',
    inputSchema: {
      name: z.string().min(1).max(128).describe('Hook name, max 128 characters.'),
      teamId: optionalNumberLike('Make team ID where the hook will be created. Optional when MAKE_TEAM_ID is configured.'),
      connectionId: numberLike('Make Meta/Facebook Lead Ads connection ID.'),
      pageId: z.string().min(1).describe('Meta page ID.'),
      formId: z.string().min(1).describe('Meta lead form ID.'),
      typeName: z.string().default(DEFAULT_META_LEAD_ADS_HOOK_TYPE).describe('Hook type name. Defaults to facebook-lead-ads-new-event and can be overridden if Make returns a type error.')
    }
  },
  (args) =>
    make().createHook({
        ...withDefaultTeamId(args),
      method: false,
      headers: false,
      stringify: false
    })
);

registerTool(
  'make_get_hook',
  {
    title: 'Get Make Hook',
    description: 'Get details for a Make hook. Requires hooks:read scope.',
    inputSchema: {
      hookId: numberLike('Make hook ID.')
    }
  },
  (args) => make().getHook(args)
);

registerTool(
  'make_ping_hook',
  {
    title: 'Ping Make Hook',
    description: 'Ping a Make hook to inspect active/attached/learning status. Requires hooks:read scope.',
    inputSchema: {
      hookId: numberLike('Make hook ID.')
    }
  },
  (args) => make().pingHook(args)
);

registerTool(
  'make_enable_hook',
  {
    title: 'Enable Make Hook',
    description: 'Enable a Make hook. Requires hooks:write scope.',
    inputSchema: {
      hookId: numberLike('Make hook ID.')
    }
  },
  (args) => make().enableHook(args)
);

registerTool(
  'make_disable_hook',
  {
    title: 'Disable Make Hook',
    description: 'Disable a Make hook. Requires hooks:write scope. Use only when explicitly requested.',
    inputSchema: {
      hookId: numberLike('Make hook ID.')
    }
  },
  (args) => make().disableHook(args)
);

registerTool(
  'make_list_scenarios',
  {
    title: 'List Make Scenarios',
    description: 'List Make scenarios for a team or organization. Requires scenarios:read scope.',
    inputSchema: {
      teamId: optionalNumberLike('Make team ID. Optional when MAKE_TEAM_ID is configured unless organizationId is supplied. Omit when not used; do not pass 0.'),
      organizationId: optionalNumberLike('Optional Make organization ID. If supplied, omit teamId. Omit when not used; do not pass 0.'),
      ids: z.array(z.union([z.number().int(), z.string().min(1)])).optional().describe('Optional scenario IDs to retrieve. Omit when empty.'),
      folderId: optionalNumberLike('Optional folder ID filter. Omit when not used; do not pass 0.'),
      isActive: z.boolean().optional().describe('Filter active or inactive scenarios.'),
      concept: z.boolean().optional().describe('When true, return only scenario concepts.'),
      type: z.enum(['scenario', 'tool']).optional().describe('Scenario type filter.'),
      cols: z.array(z.string()).optional().describe('Optional response columns. Omit when empty.'),
      limit: optionalNumberLike('Optional page limit.'),
      offset: optionalNumberLike('Optional page offset.')
    }
  },
  (args) => make().listScenarios(args.organizationId ? args : withDefaultTeamId(args))
);

registerTool(
  'make_list_team_scenarios',
  {
    title: 'List Team Make Scenarios',
    description: 'List Make scenarios for one team. Prefer this over make_list_scenarios when working within the configured team. Requires scenarios:read scope.',
    inputSchema: {
      teamId: optionalNumberLike('Make team ID. Optional when MAKE_TEAM_ID is configured. Omit when not used; do not pass 0.'),
      ids: z.array(z.union([z.number().int(), z.string().min(1)])).optional().describe('Optional scenario IDs to retrieve. Omit when empty.'),
      folderId: optionalNumberLike('Optional folder ID filter. Omit when not used; do not pass 0.'),
      isActive: z.boolean().optional().describe('Filter active or inactive scenarios.'),
      concept: z.boolean().optional().describe('When true, return only scenario concepts.'),
      type: z.enum(['scenario', 'tool']).optional().describe('Scenario type filter.'),
      cols: z.array(z.string()).optional().describe('Optional response columns. Omit when empty.'),
      limit: optionalNumberLike('Optional page limit.'),
      offset: optionalNumberLike('Optional page offset.')
    }
  },
  (args) =>
    make().listScenarios(
      withDefaultTeamId({
        ...args,
        ids: cleanArray(args.ids),
        cols: cleanArray(args.cols)
      })
    )
);

registerTool(
  'make_list_organization_scenarios',
  {
    title: 'List Organization Make Scenarios',
    description: 'List Make scenarios for one organization. Requires scenarios:read scope.',
    inputSchema: {
      organizationId: numberLike('Make organization ID.'),
      ids: z.array(z.union([z.number().int(), z.string().min(1)])).optional().describe('Optional scenario IDs to retrieve. Omit when empty.'),
      folderId: optionalNumberLike('Optional folder ID filter. Omit when not used; do not pass 0.'),
      isActive: z.boolean().optional().describe('Filter active or inactive scenarios.'),
      concept: z.boolean().optional().describe('When true, return only scenario concepts.'),
      type: z.enum(['scenario', 'tool']).optional().describe('Scenario type filter.'),
      cols: z.array(z.string()).optional().describe('Optional response columns. Omit when empty.'),
      limit: optionalNumberLike('Optional page limit.'),
      offset: optionalNumberLike('Optional page offset.')
    }
  },
  (args) =>
    make().listScenarios({
      ...args,
      ids: cleanArray(args.ids),
      cols: cleanArray(args.cols)
    })
);

registerTool(
  'make_create_scenario',
  {
    title: 'Create Make Scenario',
    description: 'Create a Make scenario from a blueprint. Requires scenarios:write scope. Does not activate or run the scenario.',
    inputSchema: {
      teamId: optionalNumberLike('Make team ID where the scenario will be created. Optional when MAKE_TEAM_ID is configured.'),
      blueprint: z.union([z.string(), z.record(z.any())]).describe('Scenario blueprint as a JSON string or object.'),
      scheduling: z.union([z.string(), z.record(z.any())]).default({ type: 'indefinitely', interval: 900 }).describe('Scenario scheduling as a JSON string or object.'),
      folderId: optionalNumberLike('Optional folder ID.'),
      basedon: optionalNumberLike('Optional template ID.'),
      confirmed: z.boolean().default(false).describe('Confirm first-time app installation if Make requires it.'),
      cols: z.array(z.string()).optional().describe('Optional response columns.')
    }
  },
  (args) => make().createScenario(withDefaultTeamId(args))
);

registerTool(
  'make_get_scenario',
  {
    title: 'Get Make Scenario',
    description: 'Get details for a Make scenario. Requires scenarios:read scope.',
    inputSchema: {
      scenarioId: numberLike('Make scenario ID.'),
      cols: z.array(z.string()).optional().describe('Optional response columns.')
    }
  },
  (args) => make().getScenario(args)
);

registerTool(
  'make_get_scenario_blueprint',
  {
    title: 'Get Make Scenario Blueprint',
    description: 'Get a Make scenario blueprint. Requires scenarios:read scope.',
    inputSchema: {
      scenarioId: numberLike('Make scenario ID.'),
      blueprintId: optionalNumberLike('Optional blueprint version ID.'),
      draft: z.boolean().optional().describe('When true, return draft blueprint. Ignored if blueprintId is set.')
    }
  },
  (args) => make().getScenarioBlueprint(args)
);

registerTool(
  'make_update_scenario',
  {
    title: 'Update Make Scenario',
    description: 'Update a Make scenario blueprint, scheduling, folder, or name. Requires scenarios:write scope. Does not activate or run the scenario.',
    inputSchema: {
      scenarioId: numberLike('Make scenario ID.'),
      blueprint: z.union([z.string(), z.record(z.any())]).optional().describe('Optional scenario blueprint as a JSON string or object.'),
      scheduling: z.union([z.string(), z.record(z.any())]).optional().describe('Optional scenario scheduling as a JSON string or object.'),
      folderId: optionalNumberLike('Optional folder ID.'),
      name: z.string().optional().describe('Optional scenario name.'),
      confirmed: z.boolean().default(false).describe('Confirm first-time app installation if Make requires it.'),
      cols: z.array(z.string()).optional().describe('Optional response columns.')
    }
  },
  (args) => make().updateScenario(args)
);

const transport = new StdioServerTransport();
await server.connect(transport);
