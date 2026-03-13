import { getConfig } from './config.js';
import { publishJsonMessage } from './mqPublisher.js';

export async function publishRegistration(opts: {
  eventType: string;
  instanceId: string;
  tags?: string[];
}): Promise<void> {
  const cfg = getConfig();

  await publishJsonMessage({
    cfg,
    exchange: cfg.registryExchange,
    exchangeType: 'topic',
    routingKey: opts.eventType,
    message: {
      event_type: opts.eventType,
      instance_id: opts.instanceId,
      tags: opts.tags ?? [],
    },
  });
}

export function startHeartbeatLoop(opts: {
  instanceId: string;
  tags?: string[];
  intervalSeconds: number;
}): void {
  const tick = async () => {
    try {
      await publishRegistration({
        eventType: 'connector.heartbeat',
        instanceId: opts.instanceId,
        tags: opts.tags,
      });
    } catch {
      /* heartbeat failures are non-fatal */
    }
  };

  setInterval(tick, opts.intervalSeconds * 1000);
}
