import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({
  name: 'make-local-inspector',
  version: '1.0.0'
});

const transport = new StdioClientTransport({
  command: 'node',
  args: ['server.js'],
  cwd: process.cwd(),
  env: {
    ...process.env,
    MAKE_API_TOKEN: process.env.MAKE_API_TOKEN || 'inspection-only-token',
    MAKE_API_ZONE: process.env.MAKE_API_ZONE || 'us2'
  },
  stderr: 'pipe'
});

try {
  await client.connect(transport);
  const result = await client.listTools();
  console.log(JSON.stringify(result, null, 2));
} finally {
  await client.close();
}
