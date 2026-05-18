import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const DEFAULT_ZONE = 'us2';
const OPTIONAL_ID_QUERY_KEYS = new Set([
  'teamId',
  'organizationId',
  'folderId',
  'viewForScenarioId',
  'blueprintId',
  'basedon'
]);

export class MakeApiError extends Error {
  constructor(message, { status, responseBody } = {}) {
    super(message);
    this.name = 'MakeApiError';
    this.status = status;
    this.responseBody = responseBody;
  }
}

export class MakeApiClient {
  constructor({ apiToken, zone = DEFAULT_ZONE } = {}) {
    if (!apiToken) {
      throw new Error('MAKE_API_TOKEN is required');
    }

    this.apiToken = apiToken;
    this.baseUrl = `https://${zone}.make.com/api/v2`;
  }

  async request(method, path, { query, body } = {}) {
    const url = new URL(`${this.baseUrl}${path}`);

    if (query) {
      for (const [key, value] of Object.entries(query)) {
        if (shouldOmitQueryValue(key, value)) continue;
        if (Array.isArray(value)) {
          for (const item of value) {
            if (!shouldOmitQueryValue(key, item)) {
              url.searchParams.append(key, String(item));
            }
          }
        } else {
          url.searchParams.set(key, String(value));
        }
      }
    }

    const response = await fetch(url, {
      method,
      headers: {
        Authorization: `Token ${this.apiToken}`,
        Accept: 'application/json',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' })
      },
      body: body === undefined ? undefined : JSON.stringify(body)
    });

    const responseText = await response.text();
    const responseBody = responseText ? parseJson(responseText) : null;

    if (!response.ok) {
      throw new MakeApiError(`Make API ${method} ${path} failed with HTTP ${response.status}`, {
        status: response.status,
        responseBody
      });
    }

    return responseBody;
  }

  listTeams({ organizationId }) {
    return this.request('GET', '/teams', { query: { organizationId } });
  }

  getTeam({ teamId }) {
    return this.request('GET', `/teams/${teamId}`);
  }

  listConnections({ teamId, type, cols } = {}) {
    return this.request('GET', '/connections', {
      query: {
        teamId,
        'type[]': type,
        'cols[]': cols
      }
    });
  }

  listHooks({ teamId, typeName, assigned, viewForScenarioId } = {}) {
    return this.request('GET', '/hooks', {
      query: sanitizeQuery({ teamId, typeName, assigned, viewForScenarioId })
    });
  }

  createHook({ name, teamId, typeName, method = false, headers = false, stringify = false, connectionId, formId, pageId }) {
    const body = {
      name,
      teamId: String(teamId),
      typeName,
      method,
      headers,
      stringify
    };

    if (!isEmptyValue(connectionId) && !isZeroValue(connectionId)) {
      body.__IMTCONN__ = Number(connectionId);
    }

    if (!isEmptyValue(formId)) {
      body.formId = String(formId);
    }

    if (!isEmptyValue(pageId)) {
      body.pageId = String(pageId);
    }

    return this.request('POST', '/hooks', { body });
  }

  getHook({ hookId }) {
    return this.request('GET', `/hooks/${hookId}`);
  }

  pingHook({ hookId }) {
    return this.request('GET', `/hooks/${hookId}/ping`);
  }

  enableHook({ hookId }) {
    return this.request('POST', `/hooks/${hookId}/enable`);
  }

  disableHook({ hookId }) {
    return this.request('POST', `/hooks/${hookId}/disable`);
  }

  listScenarios({ teamId, organizationId, ids, folderId, isActive, concept, type, cols, limit, offset } = {}) {
    const query = sanitizeScenarioListQuery({ teamId, organizationId, ids, folderId, isActive, concept, type, cols, limit, offset });

    return this.request('GET', '/scenarios', {
      query
    });
  }

  createScenario({ teamId, blueprint, scheduling, folderId, basedon, confirmed = false, cols } = {}) {
    return this.request('POST', '/scenarios', {
      query: {
        confirmed,
        'cols[]': cols
      },
      body: {
        teamId: Number(teamId),
        blueprint: stringifyIfObject(blueprint),
        scheduling: stringifyIfObject(scheduling),
        ...(isEmptyValue(folderId) || isZeroValue(folderId) ? {} : { folderId: Number(folderId) }),
        ...(isEmptyValue(basedon) || isZeroValue(basedon) ? {} : { basedon: Number(basedon) })
      }
    });
  }

  getScenario({ scenarioId, cols }) {
    return this.request('GET', `/scenarios/${scenarioId}`, {
      query: {
        'cols[]': cols
      }
    });
  }

  getScenarioBlueprint({ scenarioId, blueprintId, draft } = {}) {
    return this.request('GET', `/scenarios/${scenarioId}/blueprint`, {
      query: sanitizeQuery({ blueprintId, draft })
    });
  }

  updateScenario({ scenarioId, blueprint, scheduling, folderId, name, confirmed = false, cols } = {}) {
    const body = {};

    if (blueprint !== undefined) body.blueprint = stringifyIfObject(blueprint);
    if (scheduling !== undefined) body.scheduling = stringifyIfObject(scheduling);
    if (!isEmptyValue(folderId) && !isZeroValue(folderId)) body.folderId = Number(folderId);
    if (name !== undefined) body.name = name;

    return this.request('PATCH', `/scenarios/${scenarioId}`, {
      query: {
        confirmed,
        'cols[]': cols
      },
      body
    });
  }
}

export function createMakeApiClientFromEnv(env = process.env) {
  const configEnv = readOpenCodeMakeLocalEnv();

  return new MakeApiClient({
    apiToken: env.MAKE_API_TOKEN || configEnv.MAKE_API_TOKEN,
    zone: env.MAKE_API_ZONE || configEnv.MAKE_API_ZONE || DEFAULT_ZONE
  });
}

export function getDefaultTeamId(env = process.env) {
  const configEnv = readOpenCodeMakeLocalEnv();
  return env.MAKE_TEAM_ID || configEnv.MAKE_TEAM_ID;
}

function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function stringifyIfObject(value) {
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

function sanitizeScenarioListQuery({ teamId, organizationId, ids, folderId, isActive, concept, type, cols, limit, offset }) {
  const query = {
    folderId,
    isActive,
    concept,
    type,
    'id[]': ids,
    'cols[]': cols,
    'pg[limit]': limit,
    'pg[offset]': offset
  };

  if (!isEmptyValue(organizationId) && !isZeroValue(organizationId)) {
    query.organizationId = organizationId;
  } else if (!isEmptyValue(teamId) && !isZeroValue(teamId)) {
    query.teamId = teamId;
  }

  return sanitizeQuery(query);
}

function sanitizeQuery(query) {
  return Object.fromEntries(Object.entries(query).filter(([key, value]) => !shouldOmitQueryValue(key, value)));
}

function shouldOmitQueryValue(key, value) {
  if (isEmptyValue(value)) return true;
  if (Array.isArray(value) && value.length === 0) return true;
  if (OPTIONAL_ID_QUERY_KEYS.has(key) && isZeroValue(value)) return true;
  return false;
}

function isEmptyValue(value) {
  return value === undefined || value === null || value === '';
}

function isZeroValue(value) {
  return value === 0 || value === '0';
}

function readOpenCodeMakeLocalEnv() {
  const configPath = path.join(os.homedir(), '.config', 'opencode', 'opencode.json');

  try {
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    return config.mcp?.['make-local']?.env || {};
  } catch {
    return {};
  }
}
