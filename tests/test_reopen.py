# tests/test_reopen.py
import io
import os
import tempfile

import pytest

import dbdb
from dbdb.interface import DBDB
from dbdb.physical import Storage


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def simulate_replacement(original_path: str, data: dict) -> None:
    """Simulate another process running compaction: write a new db file and rename it over original."""
    tmp_path = original_path + ".replacement"
    new_db = dbdb.connect(tmp_path)
    try:
        for key, value in data.items():
            new_db[key] = value
        new_db.commit()
    finally:
        new_db.close()
    os.rename(tmp_path, original_path)


class TestIsFileReplaced:
    def test_returns_false_for_unchanged_file(self, db_path):
        db = dbdb.connect(db_path)
        assert db._storage.is_file_replaced() is False
        db.close()

    def test_returns_true_after_rename(self, db_path):
        db = dbdb.connect(db_path)
        simulate_replacement(db_path, {"x": "y"})
        assert db._storage.is_file_replaced() is True
        db._storage.close()

    def test_returns_false_for_bytesio(self):
        storage = Storage(io.BytesIO())
        assert storage.is_file_replaced() is False

    def test_returns_false_again_after_reopen(self, db_path):
        db = dbdb.connect(db_path)
        simulate_replacement(db_path, {"x": "y"})
        db._reopen_if_replaced()
        assert db._storage.is_file_replaced() is False
        db.close()


class TestReopenIfReplaced:
    def test_getitem_sees_new_data(self, db_path):
        db = dbdb.connect(db_path)
        db["key"] = "old"
        db.commit()

        simulate_replacement(db_path, {"key": "new"})

        assert db["key"] == "new"
        db.close()

    def test_setitem_writes_to_new_file(self, db_path):
        db = dbdb.connect(db_path)
        db["a"] = "1"
        db.commit()

        simulate_replacement(db_path, {"a": "1"})

        db["b"] = "2"
        db.commit()
        db.close()

        verify = dbdb.connect(db_path)
        assert verify["a"] == "1"
        assert verify["b"] == "2"
        verify.close()

    def test_delitem_works_on_new_file(self, db_path):
        db = dbdb.connect(db_path)
        db["a"] = "1"
        db.commit()

        simulate_replacement(db_path, {"a": "1", "b": "2"})

        del db["b"]
        db.commit()
        db.close()

        verify = dbdb.connect(db_path)
        assert verify["a"] == "1"
        with pytest.raises(KeyError):
            _ = verify["b"]
        verify.close()

    def test_contains_reflects_new_file(self, db_path):
        db = dbdb.connect(db_path)
        db["old_key"] = "x"
        db.commit()

        simulate_replacement(db_path, {"new_key": "y"})

        assert "new_key" in db
        assert "old_key" not in db
        db.close()

    def test_len_reflects_new_file(self, db_path):
        db = dbdb.connect(db_path)
        db["a"] = "1"
        db["b"] = "2"
        db["c"] = "3"
        db.commit()

        simulate_replacement(db_path, {"a": "1"})

        assert len(db) == 1
        db.close()

    def test_storage_and_tree_are_replaced(self, db_path):
        db = dbdb.connect(db_path)
        old_storage = db._storage
        old_tree = db._tree

        simulate_replacement(db_path, {"k": "v"})
        db._reopen_if_replaced()

        assert db._storage is not old_storage
        assert db._tree is not old_tree
        db.close()

    def test_no_spurious_reopen_without_replacement(self, db_path):
        db = dbdb.connect(db_path)
        db["k"] = "v"
        db.commit()
        storage_before = db._storage

        db._reopen_if_replaced()

        assert db._storage is storage_before
        db.close()

    def test_write_session_not_interrupted(self, db_path):
        # If a write session is in progress (lock held), is_file_replaced
        # must return False because compact cannot run while lock is held.
        db = dbdb.connect(db_path)
        db["a"] = "1"  # acquires lock

        assert db._storage.locked is True
        assert db._storage.is_file_replaced() is False

        db.commit()
        db.close()
