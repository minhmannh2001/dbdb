# tests/test_reopen.py
import io
import os
import tempfile
from unittest.mock import patch

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


class TestPrepareWrite:
    def test_no_reopen_when_file_not_replaced(self, db_path):
        db = dbdb.connect(db_path)
        db["a"] = "1"
        db.commit()
        storage_before = db._storage

        db._prepare_write()

        assert db._storage is storage_before
        db.commit()
        db.close()

    def test_tree_ref_refreshed_on_first_lock(self, db_path):
        # After _prepare_write(), self._tree.set() must NOT call _refresh_tree_ref
        # again (lock is already held). Verify by checking the lock state.
        db = dbdb.connect(db_path)
        db["a"] = "1"
        db.commit()

        db._prepare_write()

        assert db._storage.locked is True
        db.commit()
        db.close()

    def test_mid_session_write_skips_reopen_check(self, db_path):
        # Second set() in the same session: _prepare_write finds lock already held,
        # skips both reopen check and refresh. Storage object must not change.
        db = dbdb.connect(db_path)
        db["a"] = "1"             # acquires lock via _prepare_write
        storage_after_first = db._storage

        db["b"] = "2"             # second write — _prepare_write must be a no-op

        assert db._storage is storage_after_first
        db.commit()
        db.close()

    def test_toctou_setitem_writes_to_new_file(self, db_path):
        # Simulate the TOCTOU race: pre-lock check passes (patched to no-op),
        # compact replaces the file, post-lock check inside _prepare_write catches it.
        db = dbdb.connect(db_path)
        db["a"] = "original"
        db.commit()

        # Suppress _reopen_if_replaced so the pre-lock check is bypassed,
        # then replace the file before __setitem__ acquires the lock.
        with patch.object(db, "_reopen_if_replaced", return_value=None):
            simulate_replacement(db_path, {"a": "compacted"})
            db["b"] = "new_write"
            db.commit()

        db.close()

        verify = dbdb.connect(db_path)
        assert verify["a"] == "compacted"
        assert verify["b"] == "new_write"
        verify.close()

    def test_toctou_delitem_writes_to_new_file(self, db_path):
        db = dbdb.connect(db_path)
        db["a"] = "1"
        db["b"] = "to_delete"
        db.commit()

        with patch.object(db, "_reopen_if_replaced", return_value=None):
            simulate_replacement(db_path, {"a": "1", "b": "to_delete"})
            del db["b"]
            db.commit()

        db.close()

        verify = dbdb.connect(db_path)
        assert verify["a"] == "1"
        with pytest.raises(KeyError):
            _ = verify["b"]
        verify.close()

    def test_toctou_triggers_storage_replacement(self, db_path):
        # Verify that _prepare_write replaces storage/tree when TOCTOU is detected.
        db = dbdb.connect(db_path)
        db["a"] = "1"
        db.commit()
        old_storage = db._storage

        with patch.object(db, "_reopen_if_replaced", return_value=None):
            simulate_replacement(db_path, {"a": "1"})
            db._prepare_write()

        assert db._storage is not old_storage
        db.commit()
        db.close()
