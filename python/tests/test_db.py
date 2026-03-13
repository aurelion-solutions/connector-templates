"""Tests for mock connector SQLite storage."""

from pathlib import Path
import sqlite3
import tempfile

import pytest
from backend import (
    delete_account,
    get_account_by_username,
    init_db,
    insert_account,
)


def test_insert_account_returns_id():
    """insert_account returns a non-empty id."""
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / 'test.db')
        init_db(path, auto_seed=False)
        id_ = insert_account('alice', 'alice@example.com', path=path)
        assert id_
        assert len(id_) == 36


def test_get_account_by_username_returns_row():
    """get_account_by_username returns row when found."""
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / 'test.db')
        init_db(path, auto_seed=False)
        id_ = insert_account('bob', 'bob@test.org', path=path)

        row = get_account_by_username('bob', path=path)
        assert row is not None
        assert row['id'] == id_
        assert row['username'] == 'bob'
        assert row['email'] == 'bob@test.org'


def test_get_account_by_username_returns_none_when_missing():
    """get_account_by_username returns None when not found."""
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / 'test.db')
        init_db(path, auto_seed=False)

        row = get_account_by_username('missing', path=path)
        assert row is None


def test_delete_account_removes_row():
    """delete_account removes the row."""
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / 'test.db')
        init_db(path, auto_seed=False)
        insert_account('charlie', 'charlie@co.org', path=path)
        assert get_account_by_username('charlie', path=path) is not None

        delete_account('charlie', path=path)
        assert get_account_by_username('charlie', path=path) is None


def test_insert_then_query():
    """Can insert and query by username."""
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / 'test.db')
        init_db(path, auto_seed=False)
        id_ = insert_account('dave', 'dave@example.com', path=path)

        row = get_account_by_username('dave', path=path)
        assert row is not None
        assert row['id'] == id_
        assert row['username'] == 'dave'
        assert row['email'] == 'dave@example.com'


def test_username_unique_constraint():
    """Duplicate username raises IntegrityError."""
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / 'test.db')
        init_db(path, auto_seed=False)
        insert_account('unique', 'first@test.org', path=path)

        with pytest.raises(sqlite3.IntegrityError):
            insert_account('unique', 'second@test.org', path=path)
