# tests/test_interface.py
import io
import pytest

from dbdb.interface import DBDB
from dbdb.physical import Storage
from dbdb.avl_tree import AVLTree
from dbdb.binary_tree import BinaryTree
from dbdb.btree import BTree


class TestDBDB:
    @pytest.mark.parametrize("tree_type", ["bst", "avl", "btree"])
    def test_init(self, tree_type):
        f = io.BytesIO()
        db = DBDB(f, tree_type=tree_type)
        assert hasattr(db, "_storage")
        assert isinstance(db._storage, Storage)
        assert hasattr(db, "_tree")
        if tree_type == "btree":
            assert isinstance(db._tree, BTree)
        elif tree_type == "avl":
            assert isinstance(db._tree, AVLTree)
        else:
            assert isinstance(db._tree, BinaryTree)

    @pytest.mark.parametrize("tree_type", ["bst", "avl", "btree"])
    def test_set_get_del(self, tree_type):
        f = io.BytesIO()
        db = DBDB(f, tree_type=tree_type)

        # Set and get
        db["a"] = "1"
        assert db["a"] == "1"

        # Delete
        del db["a"]
        with pytest.raises(KeyError):
            _ = db["a"]

    @pytest.mark.parametrize("tree_type", ["bst", "avl", "btree"])
    def test_closed_db_raises_error(self, tree_type):
        f = io.BytesIO()
        db = DBDB(f, tree_type=tree_type)
        db.close()

        with pytest.raises(ValueError):
            db["a"] = "1"

        with pytest.raises(ValueError):
            _ = db["a"]

        with pytest.raises(ValueError):
            del db["a"]

    @pytest.mark.parametrize("tree_type", ["bst", "avl", "btree"])
    def test_commit(self, tree_type):
        f = io.BytesIO()
        db = DBDB(f, tree_type=tree_type)
        db["a"] = "1"
        db.commit()

        # Reopen and check
        db2 = DBDB(f)
        assert db2["a"] == "1"
        assert len(db2) == 1
        if tree_type == "btree":
            assert isinstance(db2._tree, BTree)
        elif tree_type == "avl":
            assert isinstance(db2._tree, AVLTree)
        else:
            assert isinstance(db2._tree, BinaryTree)

    @pytest.mark.parametrize("tree_type", ["bst", "avl", "btree"])
    def test_contains_len(self, tree_type):
        f = io.BytesIO()
        db = DBDB(f, tree_type=tree_type)

        # Set two keys
        db["a"] = "1"
        db["b"] = "2"

        # Check contains
        assert "a" in db
        assert "b" in db
        assert "c" not in db

        # Check len
        assert len(db) == 2

        # Delete a key and check again
        del db["a"]
        assert "a" not in db
        assert len(db) == 1
