package com.aurelion.connector;

import com.aurelion.connector.core.OperationExecutor;
import com.aurelion.connector.core.Storage;

import java.util.*;

public final class Service implements OperationExecutor {

    private final Backend backend;
    private final Map<String, Op> registry;

    @FunctionalInterface
    private interface Op {
        OperationResult apply(Map<String, Object> payload, boolean resultStorageRequested,
                               String correlationId);
    }

    public Service(String dbPath) {
        this(dbPath, true);
    }

    public Service(String dbPath, boolean autoSeedMock) {
        this.backend = new Backend(dbPath);
        this.backend.initDb(autoSeedMock);
        Map<String, Op> r = new LinkedHashMap<>();
        r.put("create_account", (p, rsr, cid) -> createAccount(p));
        r.put("delete_account", (p, rsr, cid) -> deleteAccount(p));
        r.put("list_accounts",  (p, rsr, cid) -> listRecords("accounts",   backend.listAccounts(), rsr, cid));
        r.put("list_roles",     (p, rsr, cid) -> listRecords("roles",      backend.listRoles(), rsr, cid));
        r.put("list_privileges",(p, rsr, cid) -> listRecords("privileges", backend.listPrivileges(), rsr, cid));
        r.put("list_persons",   (p, rsr, cid) -> listRecords("persons",    backend.listPersons(), rsr, cid));
        r.put("list_employments",(p, rsr, cid) -> listRecords("employments", backend.listEmployments(), rsr, cid));
        this.registry = Collections.unmodifiableMap(r);
    }

    @Override
    public OperationResult execute(String operation, Map<String, Object> payload,
                                   boolean resultStorageRequested, String correlationId) {
        Op op = registry.get(operation);
        if (op == null) {
            throw new IllegalArgumentException("unsupported operation: '" + operation + "'");
        }
        return op.apply(payload, resultStorageRequested, correlationId);
    }

    private OperationResult createAccount(Map<String, Object> payload) {
        String username = asString(payload, "username");
        String email = asString(payload, "email");
        if (username == null || username.isBlank()) throw new IllegalArgumentException("username is required");
        if (email == null || email.isBlank()) throw new IllegalArgumentException("email is required");

        backend.insertAccount(username, email);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("username", username);
        out.put("email", email);
        return new OperationResult(out, null);
    }

    private OperationResult deleteAccount(Map<String, Object> payload) {
        String username = asString(payload, "username");
        if (username == null || username.isBlank()) throw new IllegalArgumentException("username is required");

        backend.deleteAccount(username);
        return new OperationResult(Map.of("username", username), null);
    }

    private OperationResult listRecords(String datasetType,
                                         List<Map<String, Object>> records,
                                         boolean resultStorageRequested,
                                         String correlationId) {
        if (resultStorageRequested) {
            Map<String, String> ref = Storage.writeRecords(datasetType, records, correlationId);
            return new OperationResult(null, ref);
        }
        return new OperationResult(records, null);
    }

    private static String asString(Map<String, Object> map, String key) {
        Object val = map.get(key);
        return val instanceof String s ? s : null;
    }
}
