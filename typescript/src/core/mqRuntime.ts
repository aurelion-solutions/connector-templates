import amqplib from 'amqplib';
import type { ConnectorConfig } from './config.js';
import { publishJsonMessage } from './mqPublisher.js';

export class ConnectorMqRuntime {
  private readonly cfg: ConnectorConfig;

  constructor(cfg: ConnectorConfig) {
    this.cfg = cfg;
  }

  async consumeCommands(
    instanceId: string,
    onCommand: (command: Record<string, unknown>) => void | Promise<void>,
  ): Promise<void> {
    const url = `amqp://${this.cfg.rabbitmqUsername}:${this.cfg.rabbitmqPassword}@${this.cfg.rabbitmqHost}:${this.cfg.rabbitmqPort}`;
    const conn = await amqplib.connect(url);
    const ch = await conn.createChannel();

    const exchange = this.cfg.commandsExchange;
    await ch.assertExchange(exchange, 'direct', { durable: true });

    const queueName = `aurelion.connector.${instanceId}.commands`;
    await ch.assertQueue(queueName, { durable: true });
    await ch.bindQueue(queueName, exchange, instanceId);

    await ch.consume(queueName, async (msg) => {
      if (!msg) return;
      try {
        const raw = JSON.parse(msg.content.toString('utf-8'));
        if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) {
          throw new Error('Payload is not a JSON object');
        }
        await onCommand(raw as Record<string, unknown>);
        ch.ack(msg);
      } catch {
        ch.nack(msg, false, false);
      }
    });

    console.log(`Consuming commands on queue: ${queueName}`);

    await new Promise<void>((resolve) => {
      conn.on('close', resolve);
    });
  }

  publishCommandResponse = (
    command: Record<string, unknown>,
    response: Record<string, unknown>,
  ): void => {
    const replyExchange = command['reply_exchange'];
    const replyRoutingKey = command['reply_routing_key'];
    const correlationId = command['correlation_id'];

    if (typeof replyExchange !== 'string' || !replyExchange) return;
    if (typeof replyRoutingKey !== 'string' || !replyRoutingKey) return;

    publishJsonMessage({
      cfg: this.cfg,
      exchange: replyExchange,
      exchangeType: 'direct',
      routingKey: replyRoutingKey,
      message: response,
      correlationId: typeof correlationId === 'string' ? correlationId : undefined,
    }).catch(() => {
      /* response publish failures are logged elsewhere */
    });
  };
}
