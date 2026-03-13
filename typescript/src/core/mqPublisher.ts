import amqplib from 'amqplib';
import { randomUUID } from 'node:crypto';
import type { ConnectorConfig } from './config.js';

export async function publishJsonMessage(opts: {
  cfg: ConnectorConfig;
  exchange: string;
  exchangeType: string;
  routingKey: string;
  message: Record<string, unknown>;
  correlationId?: string | null;
}): Promise<void> {
  const url = `amqp://${opts.cfg.rabbitmqUsername}:${opts.cfg.rabbitmqPassword}@${opts.cfg.rabbitmqHost}:${opts.cfg.rabbitmqPort}`;
  const conn = await amqplib.connect(url);
  const ch = await conn.createChannel();

  await ch.assertExchange(opts.exchange, opts.exchangeType, { durable: true });

  ch.publish(
    opts.exchange,
    opts.routingKey,
    Buffer.from(JSON.stringify(opts.message)),
    {
      contentType: 'application/json',
      deliveryMode: 2,
      correlationId: opts.correlationId ?? undefined,
      messageId: randomUUID(),
    },
  );

  await ch.close();
  await conn.close();
}
