"""Mock connector runtime."""

import os

from core.bootstrap import bootstrap
from core.config import ConnectorConfig

if __name__ == '__main__':
    cfg = ConnectorConfig.from_env(
        component='mock-connector',
        db_path=os.environ.get('MOCK_CONNECTOR_DB'),
    )
    bootstrap(cfg=cfg)
