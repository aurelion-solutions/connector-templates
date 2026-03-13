package com.aurelion.connector.core;

import java.util.Map;

public interface OperationExecutor {

    record OperationResult(Object payload, Map<String, String> storageRef) {}

    OperationResult execute(String operation, Map<String, Object> payload,
                            boolean resultStorageRequested, String correlationId);
}
