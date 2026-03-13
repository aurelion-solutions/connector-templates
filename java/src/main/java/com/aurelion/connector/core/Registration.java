package com.aurelion.connector.core;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class Registration {

    private final Config cfg;

    public Registration(Config cfg) {
        this.cfg = cfg;
    }

    public void publish(String eventType, String instanceId, List<String> tags) {
        Map<String, Object> message = new LinkedHashMap<>();
        message.put("event_type", eventType);
        message.put("instance_id", instanceId);
        message.put("tags", tags);

        MqPublisher.publishJson(cfg, cfg.registryExchange(), "topic",
                eventType, message, null);
    }

    public void heartbeatLoop(String instanceId, List<String> tags, int intervalSeconds) {
        while (true) {
            publish("connector.heartbeat", instanceId, tags);
            try {
                Thread.sleep(intervalSeconds * 1000L);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }
}
