import Database from 'better-sqlite3';
import { existsSync, readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SEED_NAME = 'seed.sql';

function mockDataDir(): string {
  // dist/backend.js -> typescript/dist -> typescript -> connector-templates -> _mock-data
  return resolve(__dirname, '..', '..', '_mock-data');
}

function defaultDbPath(): string {
  return process.env['MOCK_CONNECTOR_DB'] ?? join(mockDataDir(), 'mock_connector.db');
}

function seedPath(): string {
  const raw = process.env['MOCK_CONNECTOR_SEED_SQL'];
  if (raw) return raw;
  return join(mockDataDir(), SEED_NAME);
}

let _db: Database.Database | null = null;

function getDb(path?: string): Database.Database {
  if (!_db) {
    _db = new Database(path ?? defaultDbPath());
  }
  return _db;
}

function isoNow(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

const SCHEMA_SQL = `
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
`;

function loadSeedIfEmpty(db: Database.Database): void {
  const sp = seedPath();
  if (!existsSync(sp)) return;

  const row = db
    .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='persons'")
    .get() as { name: string } | undefined;
  if (!row) return;

  const count = (db.prepare('SELECT COUNT(*) AS c FROM persons').get() as { c: number }).c;
  if (count > 0) return;

  const sql = readFileSync(sp, 'utf-8');
  db.exec(sql);
}

export function initDb(path?: string, autoSeed = false): void {
  const db = getDb(path);
  db.exec(SCHEMA_SQL);
  if (autoSeed) loadSeedIfEmpty(db);
}

export function insertAccount(username: string, email: string, path?: string): string {
  const id = randomUUID();
  getDb(path)
    .prepare(
      `INSERT INTO accounts (
        id, person_id, username, email, display_name, is_active,
        is_mfa_on, is_privileged, is_service, auth_local,
        password_updated_at, last_successful_login, namespace
      ) VALUES (?, NULL, ?, ?, ?, 1, 0, 0, 0, 1, ?, NULL, 'local')`,
    )
    .run(id, username, email, username, isoNow());
  return id;
}

export function deleteAccount(username: string, path?: string): void {
  getDb(path).prepare('DELETE FROM accounts WHERE username = ?').run(username);
}

type AccountRow = {
  id: string;
  person_id: string | null;
  username: string;
  email: string;
  display_name: string | null;
  is_active: number;
  is_mfa_on: number;
  is_privileged: number;
  is_service: number;
  auth_local: number;
  password_updated_at: string | null;
  last_successful_login: string | null;
  namespace: string;
};

export function listAccounts(path?: string): Record<string, unknown>[] {
  const db = getDb(path);
  const rows = db
    .prepare(
      `SELECT id, person_id, username, email, display_name, is_active, is_mfa_on,
              is_privileged, is_service, auth_local, password_updated_at,
              last_successful_login, namespace
       FROM accounts ORDER BY username`,
    )
    .all() as AccountRow[];

  const rolesStmt = db.prepare(
    'SELECT role_id FROM account_roles WHERE account_id = ? ORDER BY role_id',
  );
  const privsStmt = db.prepare(
    'SELECT privilege_id FROM account_privileges WHERE account_id = ? ORDER BY privilege_id',
  );

  return rows.map((r) => {
    const meta: Record<string, unknown> = {
      is_service: Boolean(r.is_service),
      auth_local: Boolean(r.auth_local),
      password_updated_at: r.password_updated_at,
      last_successful_login: r.last_successful_login,
      namespace: r.namespace,
      role_identifiers: (rolesStmt.all(r.id) as { role_id: string }[]).map((x) => x.role_id),
      privilege_identifiers: (privsStmt.all(r.id) as { privilege_id: string }[]).map(
        (x) => x.privilege_id,
      ),
    };
    if (r.person_id) meta['person_identifier'] = r.person_id;

    return {
      identifier: r.id,
      username: r.username,
      display_name: r.display_name,
      email: r.email,
      is_active: Boolean(r.is_active),
      is_privileged: Boolean(r.is_privileged),
      mfa_enabled: Boolean(r.is_mfa_on),
      meta,
    };
  });
}

export function listRoles(path?: string): Record<string, unknown>[] {
  const rows = getDb(path)
    .prepare(
      'SELECT id, name, display_name, type, is_active FROM roles ORDER BY name',
    )
    .all() as {
    id: string;
    name: string;
    display_name: string;
    type: string;
    is_active: number;
  }[];

  return rows.map((r) => ({
    identifier: r.id,
    name: r.name,
    display_name: r.display_name,
    type: r.type,
    is_active: Boolean(r.is_active),
    meta: {},
  }));
}

export function listPrivileges(path?: string): Record<string, unknown>[] {
  const rows = getDb(path)
    .prepare(
      `SELECT id, name, display_name, type, namespace, is_active
       FROM privileges ORDER BY namespace, name`,
    )
    .all() as {
    id: string;
    name: string;
    display_name: string;
    type: string;
    namespace: string | null;
    is_active: number;
  }[];

  return rows.map((r) => ({
    identifier: r.id,
    name: r.name,
    display_name: r.display_name,
    type: r.type,
    is_active: Boolean(r.is_active),
    meta: r.namespace ? { namespace: r.namespace } : {},
  }));
}

export function listPersons(path?: string): Record<string, unknown>[] {
  const rows = getDb(path)
    .prepare(
      `SELECT id, full_name, email, city, phone, timezone, synthetic_ssn, synthetic_dob,
              primary_org_unit_id, primary_title_id
       FROM persons ORDER BY email`,
    )
    .all() as {
    id: string;
    full_name: string;
    email: string;
    city: string | null;
    phone: string | null;
    timezone: string | null;
    synthetic_ssn: string | null;
    synthetic_dob: string | null;
    primary_org_unit_id: string | null;
    primary_title_id: string | null;
  }[];

  return rows.map((r) => ({
    identifier: r.id,
    full_name: r.full_name,
    email: r.email,
    city: r.city,
    phone: r.phone,
    timezone: r.timezone,
    synthetic_ssn: r.synthetic_ssn,
    synthetic_dob: r.synthetic_dob,
    org_unit_identifier: r.primary_org_unit_id,
    title_identifier: r.primary_title_id,
  }));
}

export function listEmployments(path?: string): Record<string, unknown>[] {
  const rows = getDb(path)
    .prepare(
      `SELECT id, person_id, employment_type, status, started_at, ended_at,
              org_unit_id, job_title_id
       FROM employments ORDER BY started_at, id`,
    )
    .all() as {
    id: string;
    person_id: string;
    employment_type: string;
    status: string;
    started_at: string;
    ended_at: string | null;
    org_unit_id: string | null;
    job_title_id: string | null;
  }[];

  return rows.map((r) => ({
    identifier: r.id,
    person_identifier: r.person_id,
    employment_type: r.employment_type,
    status: r.status,
    started_at: r.started_at,
    ended_at: r.ended_at,
    org_unit_identifier: r.org_unit_id,
    title_identifier: r.job_title_id,
  }));
}
