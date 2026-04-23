# tests/test_interface.py
import io
import pytest

# This import will fail
from dbdb.interface import DBDB
from dbdb.physical import Storage
from dbdb.binary_tree import BinaryTree


class TestDBDB:
    def test_init(self):
        f = io.BytesIO()
        db = DBDB(f)
        assert hasattr(db, "_storage")
        assert isinstance(db._storage, Storage)
        assert hasattr(db, "_tree")
        assert isinstance(db._tree, BinaryTree)

    def test_set_get_del(self):
        f = io.BytesIO()
        db = DBDB(f)

        # Set and get
        db["a"] = "1"
        assert db["a"] == "1"

        # Delete
        del db["a"]
        with pytest.raises(KeyError):
            _ = db["a"]

    def test_closed_db_raises_error(self):
        f = io.BytesIO()
        db = DBDB(f)
        db._storage.close()  # Simulate closing

        with pytest.raises(ValueError):
            db["a"] = "1"

        with pytest.raises(ValueError):
            _ = db["a"]

        with pytest.raises(ValueError):
            del db["a"]
