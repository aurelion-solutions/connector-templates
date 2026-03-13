import 'dotenv/config';
import { bootstrap, configFromEnv } from './core/index.js';
import { Service } from './service.js';

const cfg = configFromEnv({
  component: 'mock-connector',
  dbPath: process.env['MOCK_CONNECTOR_DB'],
});

await bootstrap({
  cfg,
  opsFactory: (c) => new Service(c.dbPath, c.autoSeedMockData),
});
