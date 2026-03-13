package com.aurelion.connector;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.*;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;

public final class Backend {

    private static final String SEED_NAME = "seed.sql";

    private final String dbPath;

    public Backend(String dbPath) {
        this.dbPath = dbPath != null ? dbPath : defaultDbPath();
    }

    public void initDb(boolean autoSeed) {
        try (Connection conn = connect(); Statement stmt = conn.createStatement()) {
            for (String ddl : SCHEMA_STATEMENTS) {
                stmt.execute(ddl);
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to init DB", e);
        }
        if (autoSeed) loadSeedIfEmpty();
    }

    public String insertAccount(String username, String email) {
        String id = UUID.randomUUID().toString();
        try (Connection conn = connect();
             PreparedStatement ps = conn.prepareStatement("""
                     INSERT INTO accounts (
                         id, person_id, username, email, display_name, is_active,
                         is_mfa_on, is_privileged, is_service, auth_local,
                         password_updated_at, last_successful_login, namespace
                     ) VALUES (?, NULL, ?, ?, ?, 1, 0, 0, 0, 1, ?, NULL, 'local')
                     """)) {
            ps.setString(1, id);
            ps.setString(2, username);
            ps.setString(3, email);
            ps.setString(4, username);
            ps.setString(5, isoNow());
            ps.executeUpdate();
        } catch (SQLException e) {
            throw new RuntimeException("Failed to insert account", e);
        }
        return id;
    }

    public void deleteAccount(String username) {
        try (Connection conn = connect();
             PreparedStatement ps = conn.prepareStatement("DELETE FROM accounts WHERE username = ?")) {
            ps.setString(1, username);
            ps.executeUpdate();
        } catch (SQLException e) {
            throw new RuntimeException("Failed to delete account", e);
        }
    }

    public List<Map<String, Object>> listAccounts() {
        List<Map<String, Object>> result = new ArrayList<>();
        try (Connection conn = connect();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("""
                     SELECT id, person_id, username, email, display_name, is_active, is_mfa_on,
                            is_privileged, is_service, auth_local, password_updated_at,
                            last_successful_login, namespace
                     FROM accounts
                     ORDER BY username
                     """)) {
            while (rs.next()) {
                String id = rs.getString("id");
                Map<String, Object> meta = new LinkedHashMap<>();
                meta.put("is_service", rs.getInt("is_service") != 0);
                meta.put("auth_local", rs.getInt("auth_local") != 0);
                meta.put("password_updated_at", rs.getString("password_updated_at"));
                meta.put("last_successful_login", rs.getString("last_successful_login"));
                meta.put("namespace", rs.getString("namespace"));
                meta.put("role_identifiers", roleIdsForAccount(conn, id));
                meta.put("privilege_identifiers", privIdsForAccount(conn, id));
                String personId = rs.getString("person_id");
                if (personId != null) meta.put("person_identifier", personId);

                Map<String, Object> record = new LinkedHashMap<>();
                record.put("identifier", id);
                record.put("username", rs.getString("username"));
                record.put("display_name", rs.getString("display_name"));
                record.put("email", rs.getString("email"));
                record.put("is_active", rs.getInt("is_active") != 0);
                record.put("is_privileged", rs.getInt("is_privileged") != 0);
                record.put("mfa_enabled", rs.getInt("is_mfa_on") != 0);
                record.put("meta", meta);
                result.add(record);
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to list accounts", e);
        }
        return result;
    }

    public List<Map<String, Object>> listRoles() {
        List<Map<String, Object>> result = new ArrayList<>();
        try (Connection conn = connect();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                     "SELECT id, name, display_name, type, is_active FROM roles ORDER BY name")) {
            while (rs.next()) {
                Map<String, Object> record = new LinkedHashMap<>();
                record.put("identifier", rs.getString("id"));
                record.put("name", rs.getString("name"));
                record.put("display_name", rs.getString("display_name"));
                record.put("type", rs.getString("type"));
                record.put("is_active", rs.getInt("is_active") != 0);
                record.put("meta", Map.of());
                result.add(record);
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to list roles", e);
        }
        return result;
    }

    public List<Map<String, Object>> listPrivileges() {
        List<Map<String, Object>> result = new ArrayList<>();
        try (Connection conn = connect();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("""
                     SELECT id, name, display_name, type, namespace, is_active
                     FROM privileges ORDER BY namespace, name
                     """)) {
            while (rs.next()) {
                String ns = rs.getString("namespace");
                Map<String, Object> meta = new LinkedHashMap<>();
                if (ns != null) meta.put("namespace", ns);

                Map<String, Object> record = new LinkedHashMap<>();
                record.put("identifier", rs.getString("id"));
                record.put("name", rs.getString("name"));
                record.put("display_name", rs.getString("display_name"));
                record.put("type", rs.getString("type"));
                record.put("is_active", rs.getInt("is_active") != 0);
                record.put("meta", meta);
                result.add(record);
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to list privileges", e);
        }
        return result;
    }

    public List<Map<String, Object>> listPersons() {
        List<Map<String, Object>> result = new ArrayList<>();
        try (Connection conn = connect();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("""
                     SELECT id, full_name, email, city, phone, timezone, synthetic_ssn, synthetic_dob,
                            primary_org_unit_id, primary_title_id
                     FROM persons ORDER BY email
                     """)) {
            while (rs.next()) {
                Map<String, Object> record = new LinkedHashMap<>();
                record.put("identifier", rs.getString("id"));
                record.put("full_name", rs.getString("full_name"));
                record.put("email", rs.getString("email"));
                record.put("city", rs.getString("city"));
                record.put("phone", rs.getString("phone"));
                record.put("timezone", rs.getString("timezone"));
                record.put("synthetic_ssn", rs.getString("synthetic_ssn"));
                record.put("synthetic_dob", rs.getString("synthetic_dob"));
                record.put("org_unit_identifier", rs.getString("primary_org_unit_id"));
                record.put("title_identifier", rs.getString("primary_title_id"));
                result.add(record);
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to list persons", e);
        }
        return result;
    }

    public List<Map<String, Object>> listEmployments() {
        List<Map<String, Object>> result = new ArrayList<>();
        try (Connection conn = connect();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("""
                     SELECT id, person_id, employment_type, status, started_at, ended_at,
                            org_unit_id, job_title_id
                     FROM employments ORDER BY started_at, id
                     """)) {
            while (rs.next()) {
                Map<String, Object> record = new LinkedHashMap<>();
                record.put("identifier", rs.getString("id"));
                record.put("person_identifier", rs.getString("person_id"));
                record.put("employment_type", rs.getString("employment_type"));
                record.put("status", rs.getString("status"));
                record.put("started_at", rs.getString("started_at"));
                record.put("ended_at", rs.getString("ended_at"));
                record.put("org_unit_identifier", rs.getString("org_unit_id"));
                record.put("title_identifier", rs.getString("job_title_id"));
                result.add(record);
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to list employments", e);
        }
        return result;
    }

    private Connection connect() throws SQLException {
        return DriverManager.getConnection("jdbc:sqlite:" + dbPath);
    }

    private static String defaultDbPath() {
        String env = System.getenv("MOCK_CONNECTOR_DB");
        if (env != null && !env.isBlank()) return env;
        return mockDataDir().resolve("mock_connector.db").toString();
    }

    private static Path mockDataDir() {
        Path cwd = Paths.get(System.getProperty("user.dir")).toAbsolutePath();
        Path candidate = cwd.resolve("_mock-data");
        if (Files.isDirectory(candidate)) return candidate;
        Path parent = cwd.getParent();
        if (parent != null) {
            candidate = parent.resolve("_mock-data");
            if (Files.isDirectory(candidate)) return candidate;
        }
        return cwd.resolve("_mock-data");
    }

    private static Path seedPath() {
        String env = System.getenv("MOCK_CONNECTOR_SEED_SQL");
        if (env != null && !env.isBlank()) return Paths.get(env);
        return mockDataDir().resolve(SEED_NAME);
    }

    private void loadSeedIfEmpty() {
        Path seed = seedPath();
        if (!Files.isRegularFile(seed)) return;

        try (Connection conn = connect()) {
            try (Statement s = conn.createStatement();
                 ResultSet rs = s.executeQuery(
                         "SELECT name FROM sqlite_master WHERE type='table' AND name='persons'")) {
                if (!rs.next()) return;
            }
            try (Statement s = conn.createStatement();
                 ResultSet rs = s.executeQuery("SELECT COUNT(*) FROM persons")) {
                if (rs.next() && rs.getInt(1) > 0) return;
            }
            String sql = Files.readString(seed);
            try (Statement s = conn.createStatement()) {
                s.executeUpdate(sql);
            }
        } catch (IOException | SQLException e) {
            throw new RuntimeException("Failed to load seed", e);
        }
    }

    private static List<String> roleIdsForAccount(Connection conn, String accountId) throws SQLException {
        List<String> out = new ArrayList<>();
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT role_id FROM account_roles WHERE account_id = ? ORDER BY role_id")) {
            ps.setString(1, accountId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) out.add(rs.getString(1));
            }
        }
        return out;
    }

    private static List<String> privIdsForAccount(Connection conn, String accountId) throws SQLException {
        List<String> out = new ArrayList<>();
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT privilege_id FROM account_privileges WHERE account_id = ? ORDER BY privilege_id")) {
            ps.setString(1, accountId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) out.add(rs.getString(1));
            }
        }
        return out;
    }

    private static String isoNow() {
        return DateTimeFormatter.ISO_INSTANT
                .withZone(ZoneOffset.UTC)
                .format(Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS));
    }

    private static final String[] SCHEMA_STATEMENTS = new String[]{
            """
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS org_units (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL REFERENCES companies(id),
                parent_org_unit_id TEXT REFERENCES org_units(id),
                name TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS job_titles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS persons (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                city TEXT,
                phone TEXT,
                timezone TEXT,
                synthetic_ssn TEXT,
                synthetic_dob TEXT,
                primary_org_unit_id TEXT REFERENCES org_units(id),
                primary_title_id TEXT REFERENCES job_titles(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS employments (
                id TEXT PRIMARY KEY,
                person_id TEXT NOT NULL REFERENCES persons(id),
                employment_type TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                org_unit_id TEXT REFERENCES org_units(id),
                job_title_id TEXT REFERENCES job_titles(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                type TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS privileges (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                type TEXT NOT NULL,
                namespace TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                person_id TEXT REFERENCES persons(id),
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                display_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_mfa_on INTEGER NOT NULL DEFAULT 0,
                is_privileged INTEGER NOT NULL DEFAULT 0,
                is_service INTEGER NOT NULL DEFAULT 0,
                auth_local INTEGER NOT NULL DEFAULT 1,
                password_updated_at TEXT,
                last_successful_login TEXT,
                namespace TEXT NOT NULL DEFAULT 'corp'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS account_roles (
                account_id TEXT NOT NULL REFERENCES accounts(id),
                role_id TEXT NOT NULL REFERENCES roles(id),
                PRIMARY KEY (account_id, role_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS account_privileges (
                account_id TEXT NOT NULL REFERENCES accounts(id),
                privilege_id TEXT NOT NULL REFERENCES privileges(id),
                PRIMARY KEY (account_id, privilege_id)
            )
            """
    };
}
