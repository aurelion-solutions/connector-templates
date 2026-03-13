package com.aurelion.connector.core;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

public final class ConnectorLogger {

    private final Config cfg;

    public ConnectorLogger(Config cfg) {
        this.cfg = cfg;
    }

    public String emit(String level, String eventType, String message,
                        Map<String, Object> payload, String correlationId) {
        return emit(level, eventType, message, payload, correlationId,
                null, null, null, null, null, null, null);
    }

    public String emit(String level, String eventType, String message,
                        Map<String, Object> payload,
                        String correlationId,
                        String causationId,
                        String initiatorType, String initiatorId,
                        String actorType, String actorId,
                        String targetType, String targetId) {
        String eventId = UUID.randomUUID().toString();
        String cid = correlationId != null ? correlationId : UUID.randomUUID().toString();

        Map<String, Object> event = new LinkedHashMap<>();
        event.put("event_id", eventId);
        event.put("event_type", eventType);
        event.put("level", level);
        event.put("message", message);
        event.put("timestamp", Instant.now().toString());
        event.put("component", cfg.component());
        event.put("correlation_id", cid);
        event.put("payload", payload);
        event.put("initiator_type", initiatorType != null ? initiatorType : "system");
        event.put("initiator_id", initiatorId != null ? initiatorId : "platform");
        event.put("actor_type", actorType != null ? actorType : "connector");
        event.put("actor_id", actorId != null ? actorId : cfg.instanceId());
        event.put("target_type", targetType != null ? targetType : "system");
        event.put("target_id", targetId != null ? targetId : cfg.instanceId());
        if (causationId != null) event.put("causation_id", causationId);

        MqPublisher.publishJson(cfg, cfg.logsExchange(), "topic",
                cfg.component() + "." + level, event, cid);

        return eventId;
    }
}
