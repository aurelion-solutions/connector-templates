export interface ConnectorConfig {
  readonly rabbitmqHost: string;
  readonly rabbitmqPort: number;
  readonly rabbitmqUsername: string;
  readonly rabbitmqPassword: string;
  readonly instanceId: string;
  readonly tags: string[];
  readonly dbPath: string | undefined;
  readonly commandsExchange: string;
  readonly registryExchange: string;
  readonly logsExchange: string;
  readonly component: string;
  readonly heartbeatSeconds: number;
  readonly autoSeedMockData: boolean;
}

function parseTags(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function env(key: string, fallback: string): string {
  return process.env[key] ?? fallback;
}

function resolveAutoSeed(component: string): boolean {
  const raw = process.env['AURELION_MOCK_AUTO_SEED'];
  if (raw !== undefined) {
    const lower = raw.trim().toLowerCase();
    return lower === '1' || lower === 'true' || lower === 'yes';
  }
  const normalized = component.trim().toLowerCase();
  return normalized === 'mock-connector' || normalized === 'mock_connector';
}

export function configFromEnv(
  overrides: Partial<ConnectorConfig> = {},
): ConnectorConfig {
  const component = overrides.component ?? env('AURELION_CONNECTOR_COMPONENT', '');
  const autoSeedMockData = overrides.autoSeedMockData ?? resolveAutoSeed(component);

  const base: ConnectorConfig = {
    rabbitmqHost: env('AURELION_RABBITMQ_HOST', 'localhost'),
    rabbitmqPort: Number(env('AURELION_RABBITMQ_PORT', '5672')),
    rabbitmqUsername: env('AURELION_RABBITMQ_USERNAME', 'guest'),
    rabbitmqPassword: env('AURELION_RABBITMQ_PASSWORD', 'guest'),
    instanceId: env('AURELION_CONNECTOR_INSTANCE_ID', ''),
    tags: parseTags(process.env['AURELION_CONNECTOR_TAGS']),
    dbPath: process.env['MOCK_CONNECTOR_DB'],
    commandsExchange: env(
      'AURELION_CONNECTOR_COMMANDS_EXCHANGE',
      'aurelion.connectors.commands',
    ),
    registryExchange: env(
      'AURELION_CONNECTOR_REGISTRY_EXCHANGE',
      'aurelion.connectors.registry',
    ),
    logsExchange: env('AURELION_LOGS_EXCHANGE', 'aurelion.logs'),
    component,
    heartbeatSeconds: Number(
      env('AURELION_CONNECTOR_HEARTBEAT_SECONDS', '60'),
    ),
    autoSeedMockData,
  };

  return { ...base, ...stripUndefined(overrides) };
}

function stripUndefined(
  obj: Partial<ConnectorConfig>,
): Partial<ConnectorConfig> {
  const result: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined) result[k] = v;
  }
  return result as Partial<ConnectorConfig>;
}

let _cfg: ConnectorConfig | null = null;

export function initConfig(cfg?: ConnectorConfig): ConnectorConfig {
  _cfg = cfg ?? configFromEnv();
  return _cfg;
}

export function getConfig(): ConnectorConfig {
  if (!_cfg) throw new Error('ConnectorConfig not initialised — call initConfig() first');
  return _cfg;
}
