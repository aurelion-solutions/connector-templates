package com.aurelion.connector.core;

import com.aurelion.connector.core.OperationExecutor.OperationResult;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

public final class CommandHandler {

    private final String instanceId;
    private final OperationExecutor ops;
    private final ConnectorLogger logger;
    private final MqResponseSender responseSender;

    @FunctionalInterface
    public interface MqResponseSender {
        void send(Map<String, Object> command, Map<String, Object> response);
    }

    public CommandHandler(String instanceId, OperationExecutor ops,
                          ConnectorLogger logger, MqResponseSender responseSender) {
        this.instanceId = instanceId;
        this.ops = ops;
        this.logger = logger;
        this.responseSender = responseSender;
    }

    @SuppressWarnings("unchecked")
    public void handle(Map<String, Object> command) {
        String correlationId = asString(command, "correlation_id");
        String operation = asString(command, "operation");
        boolean resultStorageRequested = Boolean.TRUE.equals(command.get("result_storage_requested"));
        Object rawPayload = command.getOrDefault("payload", Map.of());
        Map<String, Object> payload = rawPayload instanceof Map<?, ?>
                ? (Map<String, Object>) rawPayload : Map.of();

        if (correlationId == null) {
            responseSender.send(command, errorResponse(null, "correlation_id not provided"));
            return;
        }
        if (operation == null || operation.isBlank()) {
            responseSender.send(command, errorResponse(correlationId, "operation is required"));
            return;
        }

        TraceContext trace = parseCommandTrace(command);
        String initT, initI, tgtT, tgtI;
        String causationParent = null;
        if (trace != null) {
            initT = trace.initiatorType;
            initI = trace.initiatorId;
            tgtT = trace.targetType;
            tgtI = trace.targetId;
            causationParent = trace.parentEventId;
        } else {
            initT = "system";
            initI = "platform";
            tgtT = "system";
            tgtI = operation;
        }

        String receivedId = logger.emit("info", "connector.command.received", "Command received",
                Map.of("instance_id", instanceId, "operation", operation),
                correlationId, causationParent,
                initT, initI, "connector", instanceId, tgtT, tgtI);

        try {
            OperationResult result = ops.execute(operation, payload, resultStorageRequested, correlationId);
            Map<String, Object> response = successResponse(correlationId, result.payload(), result.storageRef());

            logger.emit("info", "connector.command.completed", "Command completed",
                    Map.of("instance_id", instanceId, "operation", operation,
                            "stored", result.storageRef() != null),
                    correlationId, receivedId,
                    initT, initI, "connector", instanceId, tgtT, tgtI);

            responseSender.send(command, response);
        } catch (Exception e) {
            logger.emit("error", "connector.command.failed", "Command failed",
                    Map.of("instance_id", instanceId, "operation", operation,
                            "error", e.getMessage() == null ? "" : e.getMessage()),
                    correlationId, receivedId,
                    initT, initI, "connector", instanceId, tgtT, tgtI);
            responseSender.send(command, errorResponse(correlationId, e.getMessage()));
        }
    }

    private record TraceContext(String initiatorType, String initiatorId,
                                 String targetType, String targetId,
                                 String parentEventId) {}

    private static TraceContext parseCommandTrace(Map<String, Object> command) {
        String raw = asString(command, "trace_parent_event_id");
        if (raw == null || raw.isBlank()) return null;
        try {
            UUID.fromString(raw.trim());
        } catch (IllegalArgumentException e) {
            return null;
        }
        String it = asString(command, "trace_initiator_type");
        String ii = asString(command, "trace_initiator_id");
        String tt = asString(command, "trace_target_type");
        String ti = asString(command, "trace_target_id");
        if (it == null || it.isBlank() || ii == null || ii.isBlank()
                || tt == null || tt.isBlank() || ti == null || ti.isBlank()) return null;

        return new TraceContext(
                it.trim().toLowerCase(),
                ii.trim(),
                tt.trim().toLowerCase(),
                ti.trim(),
                raw.trim()
        );
    }

    private static Map<String, Object> errorResponse(String correlationId, String message) {
        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("correlation_id", correlationId);
        resp.put("status", "error");
        resp.put("payload", null);
        resp.put("result_storage_ref", null);
        resp.put("error", Map.of("message", message == null ? "" : message));
        return resp;
    }

    private static Map<String, Object> successResponse(String correlationId,
                                                        Object payload,
                                                        Map<String, String> storageRef) {
        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("correlation_id", correlationId);
        resp.put("status", "ok");
        resp.put("payload", payload);
        resp.put("result_storage_ref", storageRef);
        resp.put("error", null);
        return resp;
    }

    private static String asString(Map<String, Object> map, String key) {
        Object val = map.get(key);
        return val instanceof String s ? s : null;
    }
}
