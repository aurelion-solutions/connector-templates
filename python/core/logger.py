"""MQ log publisher for the connector instance runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from .config import get_config
from .mq import publish_json_message


def emit_log(
    *,
    level: str,
    event_type: str,
    message: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
    causation_id: str | None = None,
    initiator_type: str | None = None,
    initiator_id: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> str:
    """Publish a LogEvent v2-shaped message. Returns ``event_id`` (for causation chaining)."""
    cfg = get_config()
    eid = uuid.uuid4()
    cid = correlation_id if correlation_id is not None else str(uuid.uuid4())

    itype = initiator_type or 'system'
    iid = initiator_id or 'platform'
    atype = actor_type or 'connector'
    aid = actor_id or cfg.instance_id
    ttype = target_type or 'system'
    tid = target_id or cfg.instance_id

    log_event: dict[str, Any] = {
        'event_id': str(eid),
        'event_type': event_type,
        'level': level,
        'message': message,
        'timestamp': datetime.now(UTC).isoformat(),
        'component': cfg.component,
        'correlation_id': cid,
        'payload': payload,
        'initiator_type': itype,
        'initiator_id': iid,
        'actor_type': atype,
        'actor_id': aid,
        'target_type': ttype,
        'target_id': tid,
    }
    if causation_id is not None:
        log_event['causation_id'] = causation_id

    publish_json_message(
        host=cfg.rabbitmq_host,
        port=cfg.rabbitmq_port,
        exchange=cfg.logs_exchange,
        exchange_type='topic',
        routing_key=f'{cfg.component}.{level}',
        message=log_event,
        username=cfg.rabbitmq_username,
        password=cfg.rabbitmq_password,
        correlation_id=cid,
    )
    return str(eid)
