"""Singleton configuration for the connector instance runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class ConnectorConfig:
    rabbitmq_host: str = 'localhost'
    rabbitmq_port: int = 5672
    rabbitmq_username: str | None = None
    rabbitmq_password: str | None = None

    instance_id: str = ''
    tags: list[str] = field(default_factory=list)
    db_path: str | None = None

    commands_exchange: str = 'aurelion.connectors.commands'
    registry_exchange: str = 'aurelion.connectors.registry'
    logs_exchange: str = 'aurelion.logs'

    component: str = 'mock-connector'
    heartbeat_seconds: int = 60
    auto_seed_mock_data: bool = False

    @classmethod
    def from_env(cls, **overrides: object) -> ConnectorConfig:
        from dotenv import load_dotenv

        load_dotenv()

        component = os.environ.get('AURELION_CONNECTOR_COMPONENT', '')

        values = dict(
            rabbitmq_host=os.environ.get('AURELION_RABBITMQ_HOST', 'localhost'),
            rabbitmq_port=int(os.environ.get('AURELION_RABBITMQ_PORT', '5672')),
            rabbitmq_username=os.environ.get('AURELION_RABBITMQ_USERNAME'),
            rabbitmq_password=os.environ.get('AURELION_RABBITMQ_PASSWORD'),
            instance_id=os.environ.get('AURELION_CONNECTOR_INSTANCE_ID', ''),
            tags=_parse_tags(os.environ.get('AURELION_CONNECTOR_TAGS')),
            commands_exchange=os.environ.get(
                'AURELION_CONNECTOR_COMMANDS_EXCHANGE',
                'aurelion.connectors.commands',
            ),
            registry_exchange=os.environ.get(
                'AURELION_CONNECTOR_REGISTRY_EXCHANGE',
                'aurelion.connectors.registry',
            ),
            logs_exchange=os.environ.get('AURELION_LOGS_EXCHANGE', 'aurelion.logs'),
            component=component,
            heartbeat_seconds=int(
                os.environ.get('AURELION_CONNECTOR_HEARTBEAT_SECONDS', '60'),
            ),
            auto_seed_mock_data=False,
        )
        values.update({k: v for k, v in overrides.items() if v is not None})
        auto_raw = os.environ.get('AURELION_MOCK_AUTO_SEED')
        if auto_raw is not None:
            values['auto_seed_mock_data'] = auto_raw.strip().lower() in ('1', 'true', 'yes')
        elif 'auto_seed_mock_data' not in overrides:
            comp = str(values.get('component') or '')
            values['auto_seed_mock_data'] = comp.strip().lower() in (
                'mock-connector',
                'mock_connector',
            )
        return cls(**values)


def _parse_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


_cfg: ConnectorConfig | None = None


def init_config(cfg: ConnectorConfig | None = None) -> ConnectorConfig:
    global _cfg  # noqa: PLW0603
    _cfg = cfg if cfg is not None else ConnectorConfig.from_env()
    return _cfg


def get_config() -> ConnectorConfig:
    if _cfg is None:
        raise RuntimeError('ConnectorConfig not initialised — call init_config() first')
    return _cfg
