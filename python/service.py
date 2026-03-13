"""Connector instance operation implementations."""

from typing import Any

from backend import (
    delete_account,
    init_db,
    insert_account,
    list_accounts,
    list_employments,
    list_persons,
    list_privileges,
    list_roles,
)
from core.storage import write_records

OperationResult = tuple[
    dict[str, Any] | list[dict[str, Any]] | None,
    dict[str, str] | None,
]


class Service:
    def __init__(
        self,
        db_path: str | None = None,
        *,
        auto_seed_mock: bool = True,
    ) -> None:
        self._db_path = db_path
        init_db(db_path, auto_seed=auto_seed_mock)
        self._registry: dict[str, Any] = {
            'create_account': self._create_account,
            'delete_account': self._delete_account,
            'list_accounts': self._list_accounts,
            'list_roles': self._list_roles,
            'list_privileges': self._list_privileges,
            'list_persons': self._list_persons,
            'list_employments': self._list_employments,
        }

    def execute(
        self,
        operation: str,
        payload: dict[str, Any],
        result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult:
        handler = self._registry.get(operation)
        if handler is None:
            raise ValueError(f'unsupported operation: {operation!r}')
        return handler(payload, result_storage_requested, correlation_id=correlation_id)

    def _create_account(
        self,
        payload: dict[str, Any],
        _result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult:
        username = payload.get('username')
        email = payload.get('email')
        if not isinstance(username, str) or not username:
            raise ValueError('username is required')
        if not isinstance(email, str) or not email:
            raise ValueError('email is required')

        insert_account(username, email, path=self._db_path)
        return {'username': username, 'email': email}, None

    def _delete_account(
        self,
        payload: dict[str, Any],
        _result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult:
        username = payload.get('username')
        if not isinstance(username, str) or not username:
            raise ValueError('username is required')

        delete_account(username, path=self._db_path)
        return {'username': username}, None

    def _list_records(
        self,
        dataset_type: str,
        records: list[dict[str, Any]],
        result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult:
        if result_storage_requested:
            return None, write_records(dataset_type, records, correlation_id=correlation_id)
        return records, None

    def _list_accounts(
        self,
        _payload: dict[str, Any],
        result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult:
        return self._list_records(
            'accounts',
            list_accounts(path=self._db_path),
            result_storage_requested,
            correlation_id=correlation_id,
        )

    def _list_roles(
        self,
        _payload: dict[str, Any],
        result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult:
        return self._list_records(
            'roles',
            list_roles(path=self._db_path),
            result_storage_requested,
            correlation_id=correlation_id,
        )

    def _list_privileges(
        self,
        _payload: dict[str, Any],
        result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult:
        return self._list_records(
            'privileges',
            list_privileges(path=self._db_path),
            result_storage_requested,
            correlation_id=correlation_id,
        )

    def _list_persons(
        self,
        _payload: dict[str, Any],
        result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult:
        return self._list_records(
            'persons',
            list_persons(path=self._db_path),
            result_storage_requested,
            correlation_id=correlation_id,
        )

    def _list_employments(
        self,
        _payload: dict[str, Any],
        result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult:
        return self._list_records(
            'employments',
            list_employments(path=self._db_path),
            result_storage_requested,
            correlation_id=correlation_id,
        )
