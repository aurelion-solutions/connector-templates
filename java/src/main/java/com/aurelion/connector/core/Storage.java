package com.aurelion.connector.core;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

public final class Storage {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String DEFAULT_BASE = ".lake";

    private Storage() {}

    public static Map<String, String> writeRecords(String datasetType,
                                                     Iterable<Map<String, Object>> records,
                                                     String correlationId) {
        String safe = sanitizeDatasetType(datasetType);
        Path base = resolveBasePath();
        String key = UUID.randomUUID().toString();
        Path dir = base.resolve(safe);

        try {
            Files.createDirectories(dir);
            Path filePath = dir.resolve(key + ".jsonl");
            try (BufferedWriter writer = Files.newBufferedWriter(filePath, StandardCharsets.UTF_8)) {
                for (Map<String, Object> record : records) {
                    writer.write(MAPPER.writeValueAsString(record));
                    writer.write('\n');
                }
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to write records", e);
        }

        String cidLabel = (correlationId == null || correlationId.isEmpty())
                ? "[correlation_id: n/a]"
                : "[correlation_id: " + correlationId + "]";
        System.out.println(Instant.now() + " " + cidLabel + " datalake write " + safe + "/" + key);

        return Map.of("provider", "file", "storage_key", safe + "/" + key);
    }

    private static Path resolveBasePath() {
        String env = System.getenv("AURELION_LAKE_PATH");
        if (env != null && !env.isBlank()) return Paths.get(env);
        return Paths.get(System.getProperty("user.dir"), DEFAULT_BASE);
    }

    private static String sanitizeDatasetType(String datasetType) {
        if (datasetType.contains("..") || datasetType.contains("/") || datasetType.contains("\\")) {
            throw new IllegalArgumentException("Invalid dataset_type: '" + datasetType + "'");
        }
        return datasetType;
    }
}
