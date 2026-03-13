"""Connector instance bootstrap — reusable startup sequence."""

from datetime import UTC, datetime
import threading

from .config import ConnectorConfig, init_config
from .handler import OperationExecutor, handle_command
from .logger import emit_log
from .mq import ConnectorMQRuntime
from .registration import heartbeat_loop, publish_registration


def bootstrap(
    *,
    cfg: ConnectorConfig | None = None,
    ops: OperationExecutor | None = None,
) -> None:
    cfg = init_config(cfg)

    publish_registration(
        event_type='connector.registered',
        instance_id=cfg.instance_id,
        tags=cfg.tags,
    )

    heartbeat_thread = threading.Thread(
        name='HeartBeat',
        target=heartbeat_loop,
        kwargs={
            'instance_id': cfg.instance_id,
            'tags': cfg.tags,
            'interval_seconds': cfg.heartbeat_seconds,
        },
        daemon=True,
    )
    heartbeat_thread.start()

    emit_log(
        level='info',
        event_type='connector.instance.started',
        message='Connector instance runtime started',
        payload={
            'instance_id': cfg.instance_id,
            'tags': cfg.tags,
        },
    )

    print(
        datetime.now(UTC).isoformat(),
        'connector instance listening',
        f'instance_id={cfg.instance_id}',
        cfg.tags,
        f'{cfg.rabbitmq_host}:{cfg.rabbitmq_port}',
        cfg.commands_exchange,
    )

    runtime = ConnectorMQRuntime(
        host=cfg.rabbitmq_host,
        port=cfg.rabbitmq_port,
        username=cfg.rabbitmq_username,
        password=cfg.rabbitmq_password,
        commands_exchange=cfg.commands_exchange,
    )

    if ops is None:
        ops = _default_ops(cfg)

    runtime.consume_commands(
        instance_id=cfg.instance_id,
        on_command=lambda command: handle_command(
            command,
            instance_id=cfg.instance_id,
            ops=ops,
            publish_response=runtime.publish_command_response,
        ),
    )


def _default_ops(cfg: ConnectorConfig) -> OperationExecutor:
    from service import Service

    return Service(db_path=cfg.db_path, auto_seed_mock=cfg.auto_seed_mock_data)
