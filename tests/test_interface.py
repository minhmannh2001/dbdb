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
