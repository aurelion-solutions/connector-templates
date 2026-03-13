package com.aurelion.connector.core;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public record Config(
        String rabbitmqHost,
        int rabbitmqPort,
        String rabbitmqUsername,
        String rabbitmqPassword,
        String instanceId,
        List<String> tags,
        String dbPath,
        String commandsExchange,
        String registryExchange,
        String logsExchange,
        String component,
        int heartbeatSeconds,
        boolean autoSeedMockData
) {
    public static Config fromEnv() {
        return fromEnv(null);
    }

    public static Config fromEnv(String componentOverride) {
        String component = componentOverride != null
                ? componentOverride
                : envOrNull("AURELION_CONNECTOR_COMPONENT");
        if (component == null || component.isBlank()) component = "mock-connector-java";

        return new Config(
                env("AURELION_RABBITMQ_HOST", "localhost"),
                Integer.parseInt(env("AURELION_RABBITMQ_PORT", "5672")),
                env("AURELION_RABBITMQ_USERNAME", "guest"),
                env("AURELION_RABBITMQ_PASSWORD", "guest"),
                env("AURELION_CONNECTOR_INSTANCE_ID", ""),
                parseTags(System.getenv("AURELION_CONNECTOR_TAGS")),
                System.getenv("MOCK_CONNECTOR_DB"),
                env("AURELION_CONNECTOR_COMMANDS_EXCHANGE", "aurelion.connectors.commands"),
                env("AURELION_CONNECTOR_REGISTRY_EXCHANGE", "aurelion.connectors.registry"),
                env("AURELION_LOGS_EXCHANGE", "aurelion.logs"),
                component,
                Integer.parseInt(env("AURELION_CONNECTOR_HEARTBEAT_SECONDS", "60")),
                resolveAutoSeed(component)
        );
    }

    private static boolean resolveAutoSeed(String component) {
        String raw = System.getenv("AURELION_MOCK_AUTO_SEED");
        if (raw != null) {
            String lower = raw.trim().toLowerCase();
            return lower.equals("1") || lower.equals("true") || lower.equals("yes");
        }
        String normalized = component == null ? "" : component.trim().toLowerCase();
        return normalized.equals("mock-connector") || normalized.equals("mock_connector");
    }

    private static String env(String key, String defaultValue) {
        String val = System.getenv(key);
        return val != null ? val : defaultValue;
    }

    private static String envOrNull(String key) {
        String val = System.getenv(key);
        return (val == null || val.isBlank()) ? null : val;
    }

    private static List<String> parseTags(String value) {
        if (value == null || value.isBlank()) return Collections.emptyList();
        return Arrays.stream(value.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();
    }
}
