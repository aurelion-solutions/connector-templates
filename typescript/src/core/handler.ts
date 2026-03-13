import { emitLog } from './logger.js';
import type { OperationExecutor } from './types.js';

export type ResponseSender = (
  command: Record<string, unknown>,
  response: Record<string, unknown>,
) => void;

function errorResponse(
  correlationId: string | null,
  message: string,
): Record<string, unknown> {
  return {
    correlation_id: correlationId,
    status: 'error',
    payload: null,
    result_storage_ref: null,
    error: { message },
  };
}

function successResponse(
  correlationId: string,
  payload: unknown,
  storageRef: Record<string, string> | null,
): Record<string, unknown> {
  return {
    correlation_id: correlationId,
    status: 'ok',
    payload,
    result_storage_ref: storageRef,
    error: null,
  };
}

function asString(obj: Record<string, unknown>, key: string): string | null {
  const val = obj[key];
  return typeof val === 'string' ? val : null;
}

function parseCommandTrace(command: Record<string, unknown>): {
  parentEventId: string;
  initiatorType: string;
  initiatorId: string;
  targetType: string;
  targetId: string;
} | null {
  const rawParent = asString(command, 'trace_parent_event_id');
  if (!rawParent?.trim()) return null;
  const it = asString(command, 'trace_initiator_type');
  const ii = asString(command, 'trace_initiator_id');
  const tt = asString(command, 'trace_target_type');
  const ti = asString(command, 'trace_target_id');
  if (!it?.trim() || !ii?.trim() || !tt?.trim() || !ti?.trim()) return null;
  return {
    parentEventId: rawParent.trim(),
    initiatorType: it.trim().toLowerCase(),
    initiatorId: ii.trim(),
    targetType: tt.trim().toLowerCase(),
    targetId: ti.trim(),
  };
}

export async function handleCommand(
  command: Record<string, unknown>,
  opts: {
    instanceId: string;
    ops: OperationExecutor;
    sendResponse: ResponseSender;
  },
): Promise<void> {
  const correlationId = asString(command, 'correlation_id');
  const operation = asString(command, 'operation');
  const resultStorageRequested = command['result_storage_requested'] === true;
  const rawPayload = command['payload'];
  const payload: Record<string, unknown> =
    rawPayload && typeof rawPayload === 'object' && !Array.isArray(rawPayload)
      ? (rawPayload as Record<string, unknown>)
      : {};

  if (!correlationId) {
    opts.sendResponse(command, errorResponse(null, 'correlation_id not provided'));
    return;
  }

  if (!operation) {
    opts.sendResponse(command, errorResponse(correlationId, 'operation is required'));
    return;
  }

  const trace = parseCommandTrace(command);
  let initT: string;
  let initI: string;
  let tgtT: string;
  let tgtI: string;
  let receivedId: string;

  if (trace) {
    initT = trace.initiatorType;
    initI = trace.initiatorId;
    tgtT = trace.targetType;
    tgtI = trace.targetId;
    receivedId = await emitLog({
      level: 'info',
      eventType: 'connector.command.received',
      message: 'Command received',
      payload: { instance_id: opts.instanceId, operation },
      correlationId,
      causationId: trace.parentEventId,
      initiatorType: initT,
      initiatorId: initI,
      actorType: 'connector',
      actorId: opts.instanceId,
      targetType: tgtT,
      targetId: tgtI,
    });
  } else {
    initT = 'system';
    initI = 'platform';
    tgtT = 'system';
    tgtI = operation;
    receivedId = await emitLog({
      level: 'info',
      eventType: 'connector.command.received',
      message: 'Command received',
      payload: { instance_id: opts.instanceId, operation },
      correlationId,
      initiatorType: initT,
      initiatorId: initI,
      actorType: 'connector',
      actorId: opts.instanceId,
      targetType: tgtT,
      targetId: tgtI,
    });
  }

  try {
    const result = opts.ops.execute(operation, payload, resultStorageRequested, correlationId);
    const response = successResponse(correlationId, result.payload, result.storageRef);

    await emitLog({
      level: 'info',
      eventType: 'connector.command.completed',
      message: 'Command completed',
      payload: {
        instance_id: opts.instanceId,
        operation,
        stored: result.storageRef !== null,
      },
      correlationId,
      causationId: receivedId,
      initiatorType: initT,
      initiatorId: initI,
      actorType: 'connector',
      actorId: opts.instanceId,
      targetType: tgtT,
      targetId: tgtI,
    });

    opts.sendResponse(command, response);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);

    await emitLog({
      level: 'error',
      eventType: 'connector.command.failed',
      message: 'Command failed',
      payload: { instance_id: opts.instanceId, operation, error: message },
      correlationId,
      causationId: receivedId,
      initiatorType: initT,
      initiatorId: initI,
      actorType: 'connector',
      actorId: opts.instanceId,
      targetType: tgtT,
      targetId: tgtI,
    });

    opts.sendResponse(command, errorResponse(correlationId, message));
  }
}
