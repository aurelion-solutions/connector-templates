"""Tests for deterministic mock connector seed data."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile

from backend import (
    init_db,
    list_accounts,
    list_employments,
    list_persons,
    list_privileges,
    list_roles,
)
from mock_dataset.generator import DATASET_SEED, build_sql, expected_counts


def _apply_seed(db_path: str) -> None:
    init_db(db_path, auto_seed=False)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(build_sql(seed=DATASET_SEED))
        conn.commit()
    finally:
        conn.close()


def test_expected_entity_counts() -> None:
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    try:
        _apply_seed(path)
        conn = sqlite3.connect(path)
        try:
            exp = expected_counts()
            assert conn.execute('SELECT COUNT(*) FROM persons').fetchone()[0] == exp.persons
            assert conn.execute('SELECT COUNT(*) FROM employments').fetchone()[0] == exp.employments
            assert conn.execute('SELECT COUNT(*) FROM accounts').fetchone()[0] == exp.accounts
            assert conn.execute('SELECT COUNT(*) FROM roles').fetchone()[0] == exp.roles
            assert conn.execute('SELECT COUNT(*) FROM privileges').fetchone()[0] == exp.privileges
            ar = conn.execute('SELECT COUNT(*) FROM account_roles').fetchone()[0]
            ap = conn.execute('SELECT COUNT(*) FROM account_privileges').fetchone()[0]
            assert ar > exp.accounts
            assert ap > exp.accounts
        finally:
            conn.close()
    finally:
        Path(path).unlink(missing_ok=True)


def test_deterministic_sql_output() -> None:
    a = build_sql(seed=DATASET_SEED)
    b = build_sql(seed=DATASET_SEED)
    assert a == b
    assert build_sql(seed=7) != a


def test_foreign_keys_and_references() -> None:
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    try:
        _apply_seed(path)
        conn = sqlite3.connect(path)
        try:
            conn.execute('PRAGMA foreign_keys = ON')
            assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
            bad_acc = conn.execute(
                """
                SELECT COUNT(*) FROM accounts a
                LEFT JOIN persons p ON p.id = a.person_id
                WHERE a.person_id IS NOT NULL AND p.id IS NULL
                """,
            ).fetchone()[0]
            assert bad_acc == 0
            bad_emp = conn.execute(
                """
                SELECT COUNT(*) FROM employments e
                LEFT JOIN persons p ON p.id = e.person_id
                WHERE p.id IS NULL
                """,
            ).fetchone()[0]
            assert bad_emp == 0
            bad_ar = conn.execute(
                """
                SELECT COUNT(*) FROM account_roles ar
                LEFT JOIN accounts a ON a.id = ar.account_id
                LEFT JOIN roles r ON r.id = ar.role_id
                WHERE a.id IS NULL OR r.id IS NULL
                """,
            ).fetchone()[0]
            assert bad_ar == 0
            bad_ap = conn.execute(
                """
                SELECT COUNT(*) FROM account_privileges ap
                LEFT JOIN accounts a ON a.id = ap.account_id
                LEFT JOIN privileges p ON p.id = ap.privilege_id
                WHERE a.id IS NULL OR p.id IS NULL
                """,
            ).fetchone()[0]
            assert bad_ap == 0
        finally:
            conn.close()
    finally:
        Path(path).unlink(missing_ok=True)


def test_employment_and_account_distribution() -> None:
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    try:
        _apply_seed(path)
        conn = sqlite3.connect(path)
        try:
            zero_emp = conn.execute(
                """
                SELECT COUNT(*) FROM persons p
                WHERE NOT EXISTS (SELECT 1 FROM employments e WHERE e.person_id = p.id)
                """,
            ).fetchone()[0]
            assert zero_emp == 5
            two_emp = conn.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT person_id FROM employments GROUP BY person_id HAVING COUNT(*) = 2
                )
                """,
            ).fetchone()[0]
            assert two_emp == 55
            no_acct = conn.execute(
                """
                SELECT COUNT(*) FROM persons p
                WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.person_id = p.id)
                """,
            ).fetchone()[0]
            assert no_acct == 20
            two_acct = conn.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT person_id FROM accounts WHERE person_id IS NOT NULL
                    GROUP BY person_id HAVING COUNT(*) = 2
                )
                """,
            ).fetchone()[0]
            assert two_acct == 20
        finally:
            conn.close()
    finally:
        Path(path).unlink(missing_ok=True)


def test_privileged_accounts_tend_more_roles() -> None:
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    try:
        _apply_seed(path)
        conn = sqlite3.connect(path)
        try:
            priv = conn.execute(
                """
                SELECT AVG(cnt) FROM (
                    SELECT a.id, COUNT(ar.role_id) AS cnt
                    FROM accounts a
                    JOIN account_roles ar ON ar.account_id = a.id
                    WHERE a.is_privileged = 1
                    GROUP BY a.id
                )
                """,
            ).fetchone()[0]
            norm = conn.execute(
                """
                SELECT AVG(cnt) FROM (
                    SELECT a.id, COUNT(ar.role_id) AS cnt
                    FROM accounts a
                    JOIN account_roles ar ON ar.account_id = a.id
                    WHERE a.is_privileged = 0
                    GROUP BY a.id
                )
                """,
            ).fetchone()[0]
            assert priv is not None and norm is not None
            assert float(priv) > float(norm)
        finally:
            conn.close()
    finally:
        Path(path).unlink(missing_ok=True)


def test_list_helpers_match_db() -> None:
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    try:
        _apply_seed(path)
        assert len(list_persons(path=path)) == 400
        assert len(list_employments(path=path)) == 450
        assert len(list_accounts(path=path)) == 400
        assert len(list_roles(path=path)) == 30
        assert len(list_privileges(path=path)) == 100
        sample = list_accounts(path=path)[0]
        assert 'identifier' in sample and 'meta' in sample
        assert 'role_identifiers' in sample['meta']
        assert 'privilege_identifiers' in sample['meta']
    finally:
        Path(path).unlink(missing_ok=True)


def test_auto_seed_loads_when_seed_file_present(tmp_path: Path) -> None:
    seed = tmp_path / 'seed.sql'
    seed.write_text(build_sql(seed=DATASET_SEED), encoding='utf-8')
    db = tmp_path / 'auto.db'
    import os

    old = os.environ.get('MOCK_CONNECTOR_SEED_SQL')
    try:
        os.environ['MOCK_CONNECTOR_SEED_SQL'] = str(seed)
        init_db(str(db), auto_seed=True)
        conn = sqlite3.connect(str(db))
        try:
            assert conn.execute('SELECT COUNT(*) FROM persons').fetchone()[0] == 400
        finally:
            conn.close()
    finally:
        if old is None:
            os.environ.pop('MOCK_CONNECTOR_SEED_SQL', None)
        else:
            os.environ['MOCK_CONNECTOR_SEED_SQL'] = old
