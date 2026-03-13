"""Local RabbitMQ helpers for the connector instance runtime."""

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel


def _default_params(
    host: str = 'localhost',
    port: int = 5672,
    username: str | None = None,
    password: str | None = None,
) -> pika.ConnectionParameters:
    user = username if username is not None else 'guest'
    passwd = password if password is not None else 'guest'
    credentials = pika.PlainCredentials(username=user, password=passwd)
    return pika.ConnectionParameters(host=host, port=port, credentials=credentials)


def publish_json_message(
    *,
    host: str,
    port: int,
    exchange: str,
    exchange_type: str,
    routing_key: str,
    message: dict[str, Any],
    username: str | None = None,
    password: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Publish one JSON message."""
    params = _default_params(host=host, port=port, username=username, password=password)
    connection = pika.BlockingConnection(params)
    channel: BlockingChannel = connection.channel()

    channel.exchange_declare(
        exchange=exchange,
        exchange_type=exchange_type,
        durable=True,
    )

    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=json.dumps(message, ensure_ascii=False).encode('utf-8'),
        properties=pika.BasicProperties(
            content_type='application/json',
            delivery_mode=2,
            correlation_id=correlation_id,
            message_id=str(uuid.uuid4()),
        ),
    )
    connection.close()


class ConnectorMQRuntime:
    """Long-lived command consumer for one connector instance."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        commands_exchange: str = 'aurelion.connectors.commands',
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._commands_exchange = commands_exchange

        params = _default_params(host=host, port=port, username=username, password=password)
        self._connection = pika.BlockingConnection(params)
        self._channel: BlockingChannel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=self._commands_exchange,
            exchange_type='direct',
            durable=True,
        )

    def command_queue_name(self, instance_id: str) -> str:
        return f'aurelion.connector.{instance_id}.commands'

    def consume_commands(
        self,
        *,
        instance_id: str,
        on_command: Callable[[dict[str, Any]], None],
    ) -> None:
        queue_name = self.command_queue_name(instance_id)

        self._channel.queue_declare(queue=queue_name, durable=True)
        self._channel.queue_bind(
            queue=queue_name,
            exchange=self._commands_exchange,
            routing_key=instance_id,
        )

        def _callback(_ch: BlockingChannel, method: Any, _props: Any, body: bytes) -> None:
            try:
                raw = json.loads(body.decode('utf-8'))
                if not isinstance(raw, dict):
                    raise ValueError('Payload is not a JSON object')
                correlation_id = getattr(_props, 'correlation_id', None) or raw.get(
                    'correlation_id'
                )
                cid_label = (
                    f'[correlation_id: {correlation_id}]'
                    if correlation_id
                    else '[correlation_id: n/a]'
                )
                print(
                    datetime.now(UTC).isoformat(),
                    cid_label,
                    'mq command received:',
                    raw.get('operation'),
                )
                on_command(raw)
            except Exception:
                _ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            _ch.basic_ack(delivery_tag=method.delivery_tag)

        self._channel.basic_consume(queue=queue_name, on_message_callback=_callback)

        try:
            self._channel.start_consuming()
        finally:
            self._connection.close()

    def publish_command_response(
        self,
        *,
        command: dict[str, Any],
        response: dict[str, Any],
    ) -> None:
        """Send a response back to the caller via reply_exchange/reply_routing_key."""
        reply_exchange = command.get('reply_exchange')
        reply_routing_key = command.get('reply_routing_key')
        correlation_id = command.get('correlation_id')

        if not isinstance(reply_exchange, str) or not reply_exchange:
            return
        if not isinstance(reply_routing_key, str) or not reply_routing_key:
            return

        cid_label = (
            f'[correlation_id: {correlation_id}]'
            if correlation_id
            else '[correlation_id: n/a]'
        )
        print(
            datetime.now(UTC).isoformat(),
            cid_label,
            'mq response publish:',
            f'routing_key:{reply_routing_key}',
            f'status:{response.get("status")}',
        )
        publish_json_message(
            host=self._host,
            port=self._port,
            exchange=reply_exchange,
            exchange_type='direct',
            routing_key=reply_routing_key,
            message=response,
            username=self._username,
            password=self._password,
            correlation_id=correlation_id,
        )
