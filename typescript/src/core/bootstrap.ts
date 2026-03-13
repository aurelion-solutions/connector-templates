import type { ConnectorConfig } from './config.js';
import { initConfig } from './config.js';
import { handleCommand } from './handler.js';
import { emitLog } from './logger.js';
import { ConnectorMqRuntime } from './mqRuntime.js';
import { publishRegistration, startHeartbeatLoop } from './registration.js';
import type { OperationExecutor } from './types.js';

export async function bootstrap(opts: {
  cfg?: ConnectorConfig;
  ops?: OperationExecutor;
  opsFactory?: (cfg: ConnectorConfig) => OperationExecutor;
}): Promise<void> {
  const cfg = initConfig(opts.cfg);

  await publishRegistration({
    eventType: 'connector.registered',
    instanceId: cfg.instanceId,
    tags: cfg.tags,
  });

  startHeartbeatLoop({
    instanceId: cfg.instanceId,
    tags: cfg.tags,
    intervalSeconds: cfg.heartbeatSeconds,
  });

  await emitLog({
    level: 'info',
    eventType: 'connector.instance.started',
    message: 'Connector instance runtime started',
    payload: { instance_id: cfg.instanceId, tags: cfg.tags },
  });

  console.log(
    new Date().toISOString(),
    'connector instance listening',
    `instance_id=${cfg.instanceId}`,
    cfg.tags,
    `${cfg.rabbitmqHost}:${cfg.rabbitmqPort}`,
    cfg.commandsExchange,
  );

  const ops = opts.ops ?? opts.opsFactory?.(cfg);
  if (!ops) throw new Error('Either ops or opsFactory must be provided');

  const runtime = new ConnectorMqRuntime(cfg);

  await runtime.consumeCommands(cfg.instanceId, (command) =>
    handleCommand(command, {
      instanceId: cfg.instanceId,
      ops,
      sendResponse: runtime.publishCommandResponse,
    }),
  );
}
