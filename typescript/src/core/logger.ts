import { randomUUID } from 'node:crypto';

import { getConfig } from './config.js';
import { publishJsonMessage } from './mqPublisher.js';

export type EmitLogOpts = {
  level: string;
  eventType: string;
  message: string;
  payload: Record<string, unknown>;
  correlationId?: string | null;
  causationId?: string | null;
  initiatorType?: string | null;
  initiatorId?: string | null;
  actorType?: string | null;
  actorId?: string | null;
  targetType?: string | null;
  targetId?: string | null;
};

export async function emitLog(opts: EmitLogOpts): Promise<string> {
  const cfg = getConfig();
  const eventId = randomUUID();
  const correlationId = opts.correlationId ?? randomUUID();

  const initiatorType = opts.initiatorType ?? 'system';
  const initiatorId = opts.initiatorId ?? 'platform';
  const actorType = opts.actorType ?? 'connector';
  const actorId = opts.actorId ?? cfg.instanceId;
  const targetType = opts.targetType ?? 'system';
  const targetId = opts.targetId ?? cfg.instanceId;

  const logEvent: Record<string, unknown> = {
    event_id: eventId,
    event_type: opts.eventType,
    level: opts.level,
    message: opts.message,
    timestamp: new Date().toISOString(),
    component: cfg.component,
    correlation_id: correlationId,
    payload: opts.payload,
    initiator_type: initiatorType,
    initiator_id: initiatorId,
    actor_type: actorType,
    actor_id: actorId,
    target_type: targetType,
    target_id: targetId,
  };
  if (opts.causationId != null && opts.causationId !== '') {
    logEvent.causation_id = opts.causationId;
  }

  await publishJsonMessage({
    cfg,
    exchange: cfg.logsExchange,
    exchangeType: 'topic',
    routingKey: `${cfg.component}.${opts.level}`,
    message: logEvent,
    correlationId,
  });

  return eventId;
}
