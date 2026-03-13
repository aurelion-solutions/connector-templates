$script:SeedName = 'seed.sql'

function Get-MockDataDir {
    return (Resolve-Path (Join-Path $PSScriptRoot '..' '_mock-data')).Path
}

function Get-DefaultDbPath {
    if ($env:MOCK_CONNECTOR_DB) { return $env:MOCK_CONNECTOR_DB }
    return Join-Path (Get-MockDataDir) 'mock_connector.db'
}

function Get-SeedPath {
    if ($env:MOCK_CONNECTOR_SEED_SQL) { return $env:MOCK_CONNECTOR_SEED_SQL }
    return Join-Path (Get-MockDataDir) $script:SeedName
}

function Get-IsoNow {
    return [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
}

$script:SchemaSql = @"
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
"@

function Open-DbConnection {
    param([string]$Path)
    if (-not $Path) { $Path = Get-DefaultDbPath }
    $conn = [Microsoft.Data.Sqlite.SqliteConnection]::new("Data Source=$Path")
    $conn.Open()
    return $conn
}

function Invoke-NonQuery {
    param(
        [Microsoft.Data.Sqlite.SqliteConnection]$Conn,
        [string]$Sql,
        [hashtable]$Params = @{}
    )
    $cmd = $Conn.CreateCommand()
    $cmd.CommandText = $Sql
    foreach ($k in $Params.Keys) {
        [void]$cmd.Parameters.AddWithValue($k, $Params[$k])
    }
    [void]$cmd.ExecuteNonQuery()
}

function Read-Rows {
    param(
        [Microsoft.Data.Sqlite.SqliteConnection]$Conn,
        [string]$Sql,
        [hashtable]$Params = @{}
    )
    $cmd = $Conn.CreateCommand()
    $cmd.CommandText = $Sql
    foreach ($k in $Params.Keys) {
        [void]$cmd.Parameters.AddWithValue($k, $Params[$k])
    }
    $reader = $cmd.ExecuteReader()
    $rows = [System.Collections.Generic.List[hashtable]]::new()
    try {
        while ($reader.Read()) {
            $row = @{}
            for ($i = 0; $i -lt $reader.FieldCount; $i++) {
                $name = $reader.GetName($i)
                $row[$name] = if ($reader.IsDBNull($i)) { $null } else { $reader.GetValue($i) }
            }
            $rows.Add($row)
        }
    }
    finally { $reader.Close() }
    return $rows
}

function Initialize-Database {
    param([string]$Path, [bool]$AutoSeed = $false)

    $conn = Open-DbConnection -Path $Path
    try {
        Invoke-NonQuery -Conn $conn -Sql $script:SchemaSql
    }
    finally { $conn.Close() }

    if ($AutoSeed) { Import-SeedIfEmpty -Path $Path }
}

function Import-SeedIfEmpty {
    param([string]$Path)

    $seed = Get-SeedPath
    if (-not (Test-Path $seed)) { return }

    $conn = Open-DbConnection -Path $Path
    try {
        $check = Read-Rows -Conn $conn -Sql "SELECT name FROM sqlite_master WHERE type='table' AND name='persons'"
        if ($check.Count -eq 0) { return }

        $countRows = Read-Rows -Conn $conn -Sql 'SELECT COUNT(*) AS c FROM persons'
        if ($countRows[0]['c'] -gt 0) { return }

        $sql = Get-Content -Raw -Path $seed
        Invoke-NonQuery -Conn $conn -Sql $sql
    }
    finally { $conn.Close() }
}

function Add-Account {
    param(
        [string]$Username,
        [string]$Email,
        [string]$Path
    )
    $id   = [guid]::NewGuid().ToString()
    $conn = Open-DbConnection -Path $Path
    try {
        Invoke-NonQuery -Conn $conn -Sql @"
INSERT INTO accounts (
    id, person_id, username, email, display_name, is_active,
    is_mfa_on, is_privileged, is_service, auth_local,
    password_updated_at, last_successful_login, namespace
) VALUES (`$id, NULL, `$user, `$email, `$user, 1, 0, 0, 0, 1, `$now, NULL, 'local')
"@ -Params @{
            '$id'    = $id
            '$user'  = $Username
            '$email' = $Email
            '$now'   = Get-IsoNow
        }
    }
    finally { $conn.Close() }
    return $id
}

function Remove-Account {
    param([string]$Username, [string]$Path)
    $conn = Open-DbConnection -Path $Path
    try {
        Invoke-NonQuery -Conn $conn -Sql 'DELETE FROM accounts WHERE username = $user' `
            -Params @{ '$user' = $Username }
    }
    finally { $conn.Close() }
}

function Get-AccountList {
    param([string]$Path)
    $conn = Open-DbConnection -Path $Path
    try {
        $rows = Read-Rows -Conn $conn -Sql @"
SELECT id, person_id, username, email, display_name, is_active, is_mfa_on,
       is_privileged, is_service, auth_local, password_updated_at,
       last_successful_login, namespace
FROM accounts
ORDER BY username
"@
        $result = [System.Collections.Generic.List[hashtable]]::new()
        foreach ($r in $rows) {
            $aid = $r['id']
            $roles = (Read-Rows -Conn $conn `
                -Sql 'SELECT role_id FROM account_roles WHERE account_id = $id ORDER BY role_id' `
                -Params @{ '$id' = $aid }) | ForEach-Object { $_['role_id'] }
            $privs = (Read-Rows -Conn $conn `
                -Sql 'SELECT privilege_id FROM account_privileges WHERE account_id = $id ORDER BY privilege_id' `
                -Params @{ '$id' = $aid }) | ForEach-Object { $_['privilege_id'] }

            $meta = @{
                is_service             = [bool][int]$r['is_service']
                auth_local             = [bool][int]$r['auth_local']
                password_updated_at    = $r['password_updated_at']
                last_successful_login  = $r['last_successful_login']
                namespace              = $r['namespace']
                role_identifiers       = @($roles)
                privilege_identifiers  = @($privs)
            }
            if ($r['person_id']) { $meta['person_identifier'] = $r['person_id'] }

            $result.Add(@{
                identifier    = $aid
                username      = $r['username']
                display_name  = $r['display_name']
                email         = $r['email']
                is_active     = [bool][int]$r['is_active']
                is_privileged = [bool][int]$r['is_privileged']
                mfa_enabled   = [bool][int]$r['is_mfa_on']
                meta          = $meta
            })
        }
        return $result.ToArray()
    }
    finally { $conn.Close() }
}

function Get-RoleList {
    param([string]$Path)
    $conn = Open-DbConnection -Path $Path
    try {
        $rows = Read-Rows -Conn $conn `
            -Sql 'SELECT id, name, display_name, type, is_active FROM roles ORDER BY name'
        return @($rows | ForEach-Object {
            @{
                identifier   = $_['id']
                name         = $_['name']
                display_name = $_['display_name']
                type         = $_['type']
                is_active    = [bool][int]$_['is_active']
                meta         = @{}
            }
        })
    }
    finally { $conn.Close() }
}

function Get-PrivilegeList {
    param([string]$Path)
    $conn = Open-DbConnection -Path $Path
    try {
        $rows = Read-Rows -Conn $conn -Sql @"
SELECT id, name, display_name, type, namespace, is_active
FROM privileges
ORDER BY namespace, name
"@
        return @($rows | ForEach-Object {
            $meta = @{}
            if ($_['namespace']) { $meta['namespace'] = $_['namespace'] }
            @{
                identifier   = $_['id']
                name         = $_['name']
                display_name = $_['display_name']
                type         = $_['type']
                is_active    = [bool][int]$_['is_active']
                meta         = $meta
            }
        })
    }
    finally { $conn.Close() }
}

function Get-PersonList {
    param([string]$Path)
    $conn = Open-DbConnection -Path $Path
    try {
        $rows = Read-Rows -Conn $conn -Sql @"
SELECT id, full_name, email, city, phone, timezone, synthetic_ssn, synthetic_dob,
       primary_org_unit_id, primary_title_id
FROM persons
ORDER BY email
"@
        return @($rows | ForEach-Object {
            @{
                identifier          = $_['id']
                full_name           = $_['full_name']
                email               = $_['email']
                city                = $_['city']
                phone               = $_['phone']
                timezone            = $_['timezone']
                synthetic_ssn       = $_['synthetic_ssn']
                synthetic_dob       = $_['synthetic_dob']
                org_unit_identifier = $_['primary_org_unit_id']
                title_identifier    = $_['primary_title_id']
            }
        })
    }
    finally { $conn.Close() }
}

function Get-EmploymentList {
    param([string]$Path)
    $conn = Open-DbConnection -Path $Path
    try {
        $rows = Read-Rows -Conn $conn -Sql @"
SELECT id, person_id, employment_type, status, started_at, ended_at,
       org_unit_id, job_title_id
FROM employments
ORDER BY started_at, id
"@
        return @($rows | ForEach-Object {
            @{
                identifier          = $_['id']
                person_identifier   = $_['person_id']
                employment_type     = $_['employment_type']
                status              = $_['status']
                started_at          = $_['started_at']
                ended_at            = $_['ended_at']
                org_unit_identifier = $_['org_unit_id']
                title_identifier    = $_['job_title_id']
            }
        })
    }
    finally { $conn.Close() }
}
