"""SQLite storage for mock connector."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import uuid
from typing import Any

_SEED_NAME = 'seed.sql'


def _mock_data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / '_mock-data'


def _get_db_path() -> str:
    """Return SQLite DB path from env or default."""
    default = str(_mock_data_dir() / 'mock_connector.db')
    return os.environ.get('MOCK_CONNECTOR_DB', default)


def _seed_path() -> Path:
    raw = os.environ.get('MOCK_CONNECTOR_SEED_SQL')
    if raw:
        return Path(raw)
    return _mock_data_dir() / _SEED_NAME


def _connect(path: str | None = None) -> sqlite3.Connection:
    """Open connection."""
    conn = sqlite3.connect(path or _get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
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
        """
    )


def _load_seed_if_empty(path: str | None) -> None:
    sp = _seed_path()
    if not sp.is_file():
        return
    conn = _connect(path)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='persons'",
        )
        if cur.fetchone() is None:
            return
        n = conn.execute('SELECT COUNT(*) AS c FROM persons').fetchone()['c']
        if n > 0:
            return
        sql = sp.read_text(encoding='utf-8')
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def init_db(path: str | None = None, *, auto_seed: bool = False) -> None:
    """Create tables; optionally load seed.sql when persons table is empty."""
    conn = _connect(path)
    try:
        _create_schema(conn)
        conn.commit()
    finally:
        conn.close()
    if auto_seed:
        _load_seed_if_empty(path)


def insert_account(username: str, email: str, path: str | None = None) -> str:
    """Insert account, return id."""
    conn = _connect(path)
    try:
        id_ = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO accounts (
                id, person_id, username, email, display_name, is_active,
                is_mfa_on, is_privileged, is_service, auth_local,
                password_updated_at, last_successful_login, namespace
            ) VALUES (?, NULL, ?, ?, ?, 1, 0, 0, 0, 1, ?, NULL, ?)
            """,
            (id_, username, email, username, _iso_now(), 'local'),
        )
        conn.commit()
        return id_
    finally:
        conn.close()


def _iso_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def delete_account(username: str, path: str | None = None) -> None:
    """Delete account by username."""
    conn = _connect(path)
    try:
        conn.execute('DELETE FROM accounts WHERE username = ?', (username,))
        conn.commit()
    finally:
        conn.close()


def get_account_by_username(username: str, path: str | None = None) -> sqlite3.Row | None:
    """Return row or None."""
    conn = _connect(path)
    try:
        cur = conn.execute(
            'SELECT id, username, email FROM accounts WHERE username = ?',
            (username,),
        )
        return cur.fetchone()
    finally:
        conn.close()


def _role_ids_for_account(conn: sqlite3.Connection, account_id: str) -> list[str]:
    cur = conn.execute(
        'SELECT role_id FROM account_roles WHERE account_id = ? ORDER BY role_id',
        (account_id,),
    )
    return [r['role_id'] for r in cur.fetchall()]


def _priv_ids_for_account(conn: sqlite3.Connection, account_id: str) -> list[str]:
    cur = conn.execute(
        'SELECT privilege_id FROM account_privileges WHERE account_id = ? ORDER BY privilege_id',
        (account_id,),
    )
    return [r['privilege_id'] for r in cur.fetchall()]


def list_accounts(path: str | None = None) -> list[dict[str, Any]]:
    """Return all accounts as connector payload records (AccountDTO-friendly)."""
    conn = _connect(path)
    try:
        cur = conn.execute(
            """
            SELECT id, person_id, username, email, display_name, is_active, is_mfa_on,
                   is_privileged, is_service, auth_local, password_updated_at,
                   last_successful_login, namespace
            FROM accounts
            ORDER BY username
            """,
        )
        rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            aid = row['id']
            meta: dict[str, Any] = {
                'is_service': bool(row['is_service']),
                'auth_local': bool(row['auth_local']),
                'password_updated_at': row['password_updated_at'],
                'last_successful_login': row['last_successful_login'],
                'namespace': row['namespace'],
                'role_identifiers': _role_ids_for_account(conn, aid),
                'privilege_identifiers': _priv_ids_for_account(conn, aid),
            }
            if row['person_id']:
                meta['person_identifier'] = row['person_id']
            out.append(
                {
                    'identifier': aid,
                    'username': row['username'],
                    'display_name': row['display_name'],
                    'email': row['email'],
                    'is_active': bool(row['is_active']),
                    'is_privileged': bool(row['is_privileged']),
                    'mfa_enabled': bool(row['is_mfa_on']),
                    'meta': meta,
                },
            )
        return out
    finally:
        conn.close()


def list_roles(path: str | None = None) -> list[dict[str, Any]]:
    conn = _connect(path)
    try:
        cur = conn.execute(
            """
            SELECT id, name, display_name, type, is_active
            FROM roles
            ORDER BY name
            """,
        )
        return [
            {
                'identifier': r['id'],
                'name': r['name'],
                'display_name': r['display_name'],
                'type': r['type'],
                'is_active': bool(r['is_active']),
                'meta': {},
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def list_privileges(path: str | None = None) -> list[dict[str, Any]]:
    conn = _connect(path)
    try:
        cur = conn.execute(
            """
            SELECT id, name, display_name, type, namespace, is_active
            FROM privileges
            ORDER BY namespace, name
            """,
        )
        return [
            {
                'identifier': r['id'],
                'name': r['name'],
                'display_name': r['display_name'],
                'type': r['type'],
                'is_active': bool(r['is_active']),
                'meta': {'namespace': r['namespace']} if r['namespace'] else {},
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def list_persons(path: str | None = None) -> list[dict[str, Any]]:
    conn = _connect(path)
    try:
        cur = conn.execute(
            """
            SELECT id, full_name, email, city, phone, timezone, synthetic_ssn, synthetic_dob,
                   primary_org_unit_id, primary_title_id
            FROM persons
            ORDER BY email
            """,
        )
        return [
            {
                'identifier': r['id'],
                'full_name': r['full_name'],
                'email': r['email'],
                'city': r['city'],
                'phone': r['phone'],
                'timezone': r['timezone'],
                'synthetic_ssn': r['synthetic_ssn'],
                'synthetic_dob': r['synthetic_dob'],
                'org_unit_identifier': r['primary_org_unit_id'],
                'title_identifier': r['primary_title_id'],
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def list_employments(path: str | None = None) -> list[dict[str, Any]]:
    conn = _connect(path)
    try:
        cur = conn.execute(
            """
            SELECT id, person_id, employment_type, status, started_at, ended_at,
                   org_unit_id, job_title_id
            FROM employments
            ORDER BY started_at, id
            """,
        )
        return [
            {
                'identifier': r['id'],
                'person_identifier': r['person_id'],
                'employment_type': r['employment_type'],
                'status': r['status'],
                'started_at': r['started_at'],
                'ended_at': r['ended_at'],
                'org_unit_identifier': r['org_unit_id'],
                'title_identifier': r['job_title_id'],
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()
