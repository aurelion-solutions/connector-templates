import time

from .config import get_config
from .mq import publish_json_message


def publish_registration(
    *,
    event_type: str,
    instance_id: str,
    tags: list[str] | None = None,
) -> None:
    cfg = get_config()

    publish_json_message(
        host=cfg.rabbitmq_host,
        port=cfg.rabbitmq_port,
        exchange=cfg.registry_exchange,
        exchange_type='topic',
        routing_key=event_type,
        message={
            'event_type': event_type,
            'instance_id': instance_id,
            'tags': tags or [],
        },
        username=cfg.rabbitmq_username,
        password=cfg.rabbitmq_password,
    )


def heartbeat_loop(
    *,
    instance_id: str,
    tags: list[str] | None = None,
    interval_seconds: int = 60,
) -> None:
    while True:
        publish_registration(
            event_type='connector.heartbeat',
            instance_id=instance_id,
            tags=tags,
        )
        time.sleep(interval_seconds)
