using System.Globalization;
using Microsoft.Data.Sqlite;

namespace Aurelion.Connector;

public sealed class Backend
{
    private const string SeedName = "seed.sql";

    private readonly string _dbPath;
    private readonly string _connectionString;

    public Backend(string? dbPath)
    {
        _dbPath = dbPath ?? DefaultDbPath();
        _connectionString = $"Data Source={_dbPath}";
    }

    public void InitDb(bool autoSeed)
    {
        using (var conn = Open())
        {
            using var cmd = conn.CreateCommand();
            cmd.CommandText = SchemaSql;
            cmd.ExecuteNonQuery();
        }
        if (autoSeed) LoadSeedIfEmpty();
    }

    public string InsertAccount(string username, string email)
    {
        var id = Guid.NewGuid().ToString();
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO accounts (
                id, person_id, username, email, display_name, is_active,
                is_mfa_on, is_privileged, is_service, auth_local,
                password_updated_at, last_successful_login, namespace
            ) VALUES ($id, NULL, $user, $email, $user, 1, 0, 0, 0, 1, $now, NULL, 'local')
            """;
        cmd.Parameters.AddWithValue("$id", id);
        cmd.Parameters.AddWithValue("$user", username);
        cmd.Parameters.AddWithValue("$email", email);
        cmd.Parameters.AddWithValue("$now", IsoNow());
        cmd.ExecuteNonQuery();
        return id;
    }

    public void DeleteAccount(string username)
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "DELETE FROM accounts WHERE username = $user";
        cmd.Parameters.AddWithValue("$user", username);
        cmd.ExecuteNonQuery();
    }

    public List<Dictionary<string, object?>> ListAccounts()
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            SELECT id, person_id, username, email, display_name, is_active, is_mfa_on,
                   is_privileged, is_service, auth_local, password_updated_at,
                   last_successful_login, namespace
            FROM accounts
            ORDER BY username
            """;
        var result = new List<Dictionary<string, object?>>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var id = reader.GetString(0);
            var meta = new Dictionary<string, object?>
            {
                ["is_service"] = reader.GetInt64(8) != 0,
                ["auth_local"] = reader.GetInt64(9) != 0,
                ["password_updated_at"] = StringOrNull(reader, 10),
                ["last_successful_login"] = StringOrNull(reader, 11),
                ["namespace"] = reader.GetString(12),
                ["role_identifiers"] = RoleIdsForAccount(conn, id),
                ["privilege_identifiers"] = PrivIdsForAccount(conn, id),
            };
            var personId = StringOrNull(reader, 1);
            if (personId is not null) meta["person_identifier"] = personId;

            result.Add(new Dictionary<string, object?>
            {
                ["identifier"] = id,
                ["username"] = reader.GetString(2),
                ["display_name"] = StringOrNull(reader, 4),
                ["email"] = reader.GetString(3),
                ["is_active"] = reader.GetInt64(5) != 0,
                ["is_privileged"] = reader.GetInt64(7) != 0,
                ["mfa_enabled"] = reader.GetInt64(6) != 0,
                ["meta"] = meta,
            });
        }
        return result;
    }

    public List<Dictionary<string, object?>> ListRoles()
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, name, display_name, type, is_active FROM roles ORDER BY name";
        var result = new List<Dictionary<string, object?>>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            result.Add(new Dictionary<string, object?>
            {
                ["identifier"] = reader.GetString(0),
                ["name"] = reader.GetString(1),
                ["display_name"] = reader.GetString(2),
                ["type"] = reader.GetString(3),
                ["is_active"] = reader.GetInt64(4) != 0,
                ["meta"] = new Dictionary<string, object?>(),
            });
        }
        return result;
    }

    public List<Dictionary<string, object?>> ListPrivileges()
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            SELECT id, name, display_name, type, namespace, is_active
            FROM privileges ORDER BY namespace, name
            """;
        var result = new List<Dictionary<string, object?>>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var ns = StringOrNull(reader, 4);
            var meta = new Dictionary<string, object?>();
            if (ns is not null) meta["namespace"] = ns;

            result.Add(new Dictionary<string, object?>
            {
                ["identifier"] = reader.GetString(0),
                ["name"] = reader.GetString(1),
                ["display_name"] = reader.GetString(2),
                ["type"] = reader.GetString(3),
                ["is_active"] = reader.GetInt64(5) != 0,
                ["meta"] = meta,
            });
        }
        return result;
    }

    public List<Dictionary<string, object?>> ListPersons()
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            SELECT id, full_name, email, city, phone, timezone, synthetic_ssn, synthetic_dob,
                   primary_org_unit_id, primary_title_id
            FROM persons ORDER BY email
            """;
        var result = new List<Dictionary<string, object?>>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            result.Add(new Dictionary<string, object?>
            {
                ["identifier"] = reader.GetString(0),
                ["full_name"] = reader.GetString(1),
                ["email"] = reader.GetString(2),
                ["city"] = StringOrNull(reader, 3),
                ["phone"] = StringOrNull(reader, 4),
                ["timezone"] = StringOrNull(reader, 5),
                ["synthetic_ssn"] = StringOrNull(reader, 6),
                ["synthetic_dob"] = StringOrNull(reader, 7),
                ["org_unit_identifier"] = StringOrNull(reader, 8),
                ["title_identifier"] = StringOrNull(reader, 9),
            });
        }
        return result;
    }

    public List<Dictionary<string, object?>> ListEmployments()
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            SELECT id, person_id, employment_type, status, started_at, ended_at,
                   org_unit_id, job_title_id
            FROM employments ORDER BY started_at, id
            """;
        var result = new List<Dictionary<string, object?>>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            result.Add(new Dictionary<string, object?>
            {
                ["identifier"] = reader.GetString(0),
                ["person_identifier"] = reader.GetString(1),
                ["employment_type"] = reader.GetString(2),
                ["status"] = reader.GetString(3),
                ["started_at"] = reader.GetString(4),
                ["ended_at"] = StringOrNull(reader, 5),
                ["org_unit_identifier"] = StringOrNull(reader, 6),
                ["title_identifier"] = StringOrNull(reader, 7),
            });
        }
        return result;
    }

    private SqliteConnection Open()
    {
        var conn = new SqliteConnection(_connectionString);
        conn.Open();
        return conn;
    }

    private static string DefaultDbPath()
    {
        var envPath = Environment.GetEnvironmentVariable("MOCK_CONNECTOR_DB");
        if (!string.IsNullOrEmpty(envPath)) return envPath;
        return Path.Combine(MockDataDir(), "mock_connector.db");
    }

    private static string MockDataDir()
    {
        // bin/Debug/net8.0/ -> csharp -> connector-templates -> _mock-data
        return Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "_mock-data"));
    }

    private static string SeedPath()
    {
        var raw = Environment.GetEnvironmentVariable("MOCK_CONNECTOR_SEED_SQL");
        if (!string.IsNullOrEmpty(raw)) return raw;
        return Path.Combine(MockDataDir(), SeedName);
    }

    private void LoadSeedIfEmpty()
    {
        var seed = SeedPath();
        if (!File.Exists(seed)) return;

        using var conn = Open();

        using (var check = conn.CreateCommand())
        {
            check.CommandText = "SELECT name FROM sqlite_master WHERE type='table' AND name='persons'";
            if (check.ExecuteScalar() is null) return;
        }

        long count;
        using (var countCmd = conn.CreateCommand())
        {
            countCmd.CommandText = "SELECT COUNT(*) FROM persons";
            count = (long)(countCmd.ExecuteScalar() ?? 0L);
        }
        if (count > 0) return;

        var sql = File.ReadAllText(seed);
        using var seedCmd = conn.CreateCommand();
        seedCmd.CommandText = sql;
        seedCmd.ExecuteNonQuery();
    }

    private static List<string> RoleIdsForAccount(SqliteConnection conn, string accountId)
    {
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT role_id FROM account_roles WHERE account_id = $id ORDER BY role_id";
        cmd.Parameters.AddWithValue("$id", accountId);
        var result = new List<string>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read()) result.Add(reader.GetString(0));
        return result;
    }

    private static List<string> PrivIdsForAccount(SqliteConnection conn, string accountId)
    {
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT privilege_id FROM account_privileges WHERE account_id = $id ORDER BY privilege_id";
        cmd.Parameters.AddWithValue("$id", accountId);
        var result = new List<string>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read()) result.Add(reader.GetString(0));
        return result;
    }

    private static string? StringOrNull(SqliteDataReader reader, int ordinal)
        => reader.IsDBNull(ordinal) ? null : reader.GetString(ordinal);

    private static string IsoNow()
        => DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", CultureInfo.InvariantCulture);

    private const string SchemaSql = """
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS org_units (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL REFERENCES companies(id),
            parent_org_unit_id TEXT REFERENCES org_units(id),
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS job_titles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

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
        );

        CREATE TABLE IF NOT EXISTS employments (
            id TEXT PRIMARY KEY,
            person_id TEXT NOT NULL REFERENCES persons(id),
            employment_type TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            org_unit_id TEXT REFERENCES org_units(id),
            job_title_id TEXT REFERENCES job_titles(id)
        );

        CREATE TABLE IF NOT EXISTS roles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            type TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS privileges (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            type TEXT NOT NULL,
            namespace TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

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
        );

        CREATE TABLE IF NOT EXISTS account_roles (
            account_id TEXT NOT NULL REFERENCES accounts(id),
            role_id TEXT NOT NULL REFERENCES roles(id),
            PRIMARY KEY (account_id, role_id)
        );

        CREATE TABLE IF NOT EXISTS account_privileges (
            account_id TEXT NOT NULL REFERENCES accounts(id),
            privilege_id TEXT NOT NULL REFERENCES privileges(id),
            PRIMARY KEY (account_id, privilege_id)
        );
        """;
}
