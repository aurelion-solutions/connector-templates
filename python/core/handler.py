"""Connector instance command handler."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol
from uuid import UUID

from .logger import emit_log

OperationResult = tuple[
    dict[str, Any] | list[dict[str, Any]] | None,
    dict[str, str] | None,
]


class OperationExecutor(Protocol):
    def execute(
        self,
        operation: str,
        payload: dict[str, Any],
        result_storage_requested: bool,
        *,
        correlation_id: str | None = None,
    ) -> OperationResult: ...


def _respond(
    publish_response: Callable[..., None] | None,
    *,
    command: dict[str, Any],
    response: dict[str, Any],
) -> None:
    if publish_response is not None:
        publish_response(command=command, response=response)


def _error_response(
    *,
    correlation_id: str | None,
    message: str,
) -> dict[str, Any]:
    return {
        'correlation_id': correlation_id,
        'status': 'error',
        'payload': None,
        'result_storage_ref': None,
        'error': {
            'message': message,
        },
    }


def _success_response(
    *,
    correlation_id: str | None,
    payload: dict[str, Any] | list[dict[str, Any]] | None,
    result_storage_ref: dict[str, str] | None,
) -> dict[str, Any]:
    return {
        'correlation_id': correlation_id,
        'status': 'ok',
        'payload': payload,
        'result_storage_ref': result_storage_ref,
        'error': None,
    }


def _parse_command_trace(command: dict[str, Any]) -> tuple[str, str, str, str, UUID] | None:
    """Return (initiator_type, initiator_id, target_type, target_id, parent_event_id) or None."""
    raw_parent = command.get('trace_parent_event_id')
    if not isinstance(raw_parent, str) or not raw_parent.strip():
        return None
    it = command.get('trace_initiator_type')
    ii = command.get('trace_initiator_id')
    tt = command.get('trace_target_type')
    ti = command.get('trace_target_id')
    if not all(isinstance(x, str) and x.strip() for x in (it, ii, tt, ti)):
        return None
    try:
        parent = UUID(raw_parent.strip())
    except ValueError:
        return None
    return it.strip().lower(), ii.strip(), tt.strip().lower(), ti.strip(), parent


def handle_command(
    command: dict[str, Any],
    *,
    instance_id: str,
    ops: OperationExecutor,
    publish_response: Callable[..., None] | None = None,
) -> None:
    correlation_id = command.get('correlation_id')
    operation = command.get('operation')
    result_storage_requested = bool(command.get('result_storage_requested'))
    payload = command.get('payload') or {}

    if not isinstance(correlation_id, str):
        response = _error_response(
            correlation_id=None,
            message='correlation_id not provided',
        )
        _respond(publish_response, command=command, response=response)
        return

    if not isinstance(operation, str) or not operation:
        response = _error_response(
            correlation_id=correlation_id,
            message='operation is required',
        )
        _respond(publish_response, command=command, response=response)
        return

    if not isinstance(payload, dict):
        response = _error_response(
            correlation_id=correlation_id,
            message='payload must be an object',
        )
        _respond(publish_response, command=command, response=response)
        return

    trace = _parse_command_trace(command)
    if trace:
        init_t, init_i, tgt_t, tgt_i, parent_event_id = trace
        received_id = emit_log(
            level='info',
            event_type='connector.command.received',
            message='Command received',
            payload={
                'instance_id': instance_id,
                'operation': operation,
            },
            correlation_id=correlation_id,
            causation_id=str(parent_event_id),
            initiator_type=init_t,
            initiator_id=init_i,
            actor_type='connector',
            actor_id=instance_id,
            target_type=tgt_t,
            target_id=tgt_i,
        )
    else:
        init_t, init_i = 'system', 'platform'
        tgt_t, tgt_i = 'system', operation
        received_id = emit_log(
            level='info',
            event_type='connector.command.received',
            message='Command received',
            payload={
                'instance_id': instance_id,
                'operation': operation,
            },
            correlation_id=correlation_id,
            initiator_type=init_t,
            initiator_id=init_i,
            actor_type='connector',
            actor_id=instance_id,
            target_type=tgt_t,
            target_id=tgt_i,
        )

    try:
        result_payload, storage_ref = ops.execute(
            operation, payload, result_storage_requested,
            correlation_id=correlation_id,
        )
        response = _success_response(
            correlation_id=correlation_id,
            payload=result_payload,
            result_storage_ref=storage_ref,
        )

    except Exception as exc:
        emit_log(
            level='error',
            event_type='connector.command.failed',
            message='Command failed',
            payload={
                'instance_id': instance_id,
                'operation': operation,
                'error': str(exc),
            },
            correlation_id=correlation_id,
            causation_id=received_id,
            initiator_type=init_t,
            initiator_id=init_i,
            actor_type='connector',
            actor_id=instance_id,
            target_type=tgt_t,
            target_id=tgt_i,
        )
        response = _error_response(
            correlation_id=correlation_id,
            message=str(exc),
        )
        _respond(publish_response, command=command, response=response)
        return

    emit_log(
        level='info',
        event_type='connector.command.completed',
        message='Command completed',
        payload={
            'instance_id': instance_id,
            'operation': operation,
            'stored': response.get('result_storage_ref') is not None,
        },
        correlation_id=correlation_id,
        causation_id=received_id,
        initiator_type=init_t,
        initiator_id=init_i,
        actor_type='connector',
        actor_id=instance_id,
        target_type=tgt_t,
        target_id=tgt_i,
    )
    _respond(publish_response, command=command, response=response)
