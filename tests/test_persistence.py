import os
import tempfile

import pytest

from dbdb.avl_tree import AVLTree
from dbdb.binary_tree import BinaryTree
from dbdb.physical import Storage


class TestPersistence:
    @pytest.fixture
    def db_file(self):
        """A fixture to create and clean up a temporary database file."""
        fd, path = tempfile.mkstemp()
        os.close(fd)
        yield path
        os.remove(path)

    @pytest.mark.parametrize("tree_class", [BinaryTree, AVLTree])
    def test_set_commit_get_reopen(self, db_file, tree_class):
        # First session: set and commit
        with open(db_file, "r+b") as f:
            storage1 = Storage(f)
            tree1 = tree_class(storage1)
            tree1.set("my_key", "my_value")
            tree1.commit()
            # Storage is closed automatically by 'with' context on f

        # Second session: reopen and get
        with open(db_file, "r+b") as f:
            storage2 = Storage(f)
            tree2 = tree_class(storage2)
            value = tree2.get("my_key")
            assert value == "my_value"

    @pytest.mark.parametrize("tree_class", [BinaryTree, AVLTree])
    def test_uncommitted_changes_are_lost(self, db_file, tree_class):
        # First session: set but do not commit
        with open(db_file, "r+b") as f:
            storage1 = Storage(f)
            tree1 = tree_class(storage1)
            tree1.set("lost_key", "lost_value")
            # No commit here

        # Second session: reopen and try to get
        with open(db_file, "r+b") as f:
            storage2 = Storage(f)
            tree2 = tree_class(storage2)
            with pytest.raises(KeyError):
                tree2.get("lost_key")

    @pytest.mark.parametrize("tree_class", [BinaryTree, AVLTree])
    def test_get_from_empty_db_raises_key_error(self, db_file, tree_class):
        with open(db_file, "r+b") as f:
            storage = Storage(f)
            tree = tree_class(storage)
            with pytest.raises(KeyError):
                tree.get("any_key")

    @pytest.mark.parametrize("tree_class", [BinaryTree, AVLTree])
    def test_only_committed_keys_are_persisted(self, db_file, tree_class):
        # First session
        with open(db_file, "r+b") as f:
            storage1 = Storage(f)
            tree1 = tree_class(storage1)
            tree1.set("a", "1")
            tree1.set("b", "2")
            tree1.commit()
            tree1.set("c", "3")

        # Second session
        with open(db_file, "r+b") as f:
            storage2 = Storage(f)
            tree2 = tree_class(storage2)
            assert tree2.get("a") == "1"
            assert tree2.get("b") == "2"
            with pytest.raises(KeyError):
                tree2.get("c")
