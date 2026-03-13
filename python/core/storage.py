"""Local file storage helpers for the connector instance runtime."""

from collections.abc import Iterable
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any
import uuid

_DEFAULT_BASE = Path('.lake')


def _resolve_base_path() -> Path:
    raw = os.environ.get('AURELION_LAKE_PATH', '')
    if raw:
        return Path(raw)
    return Path.cwd() / _DEFAULT_BASE


def _sanitize_dataset_type(dataset_type: str) -> str:
    if '..' in dataset_type or '/' in dataset_type or '\\' in dataset_type:
        raise ValueError(f'Invalid dataset_type: {dataset_type!r}')
    return dataset_type


def write_records(
    dataset_type: str,
    records: Iterable[dict[str, Any]],
    *,
    correlation_id: str | None = None,
) -> dict[str, str]:
    """Write JSONL records and return a storage reference."""
    base_path = _resolve_base_path()
    key = str(uuid.uuid4())
    safe_dataset_type = _sanitize_dataset_type(dataset_type)
    file_path = base_path / safe_dataset_type / f'{key}.jsonl'
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as file_obj:
        for record in records:
            file_obj.write(json.dumps(record, ensure_ascii=False) + '\n')

    ref = {
        'provider': 'file',
        'storage_key': f'{safe_dataset_type}/{key}',
    }
    cid_label = (
        f'[correlation_id: {correlation_id}]'
        if correlation_id
        else '[correlation_id: n/a]'
    )
    print(
        datetime.now(UTC).isoformat(),
        cid_label,
        'datalake write',
        ref['storage_key'],
    )
    return ref
