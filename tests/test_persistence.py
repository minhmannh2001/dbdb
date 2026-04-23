import os
import tempfile

import pytest

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

    def test_set_commit_get_reopen(self, db_file):
        # First session: set and commit
        with open(db_file, "r+b") as f:
            storage1 = Storage(f)
            tree1 = BinaryTree(storage1)
            tree1.set("my_key", "my_value")
            tree1.commit()
            # Storage is closed automatically by 'with' context on f

        # Second session: reopen and get
        with open(db_file, "r+b") as f:
            storage2 = Storage(f)
            tree2 = BinaryTree(storage2)
            value = tree2.get("my_key")
            assert value == "my_value"

    def test_uncommitted_changes_are_lost(self, db_file):
        # First session: set but do not commit
        with open(db_file, "r+b") as f:
            storage1 = Storage(f)
            tree1 = BinaryTree(storage1)
            tree1.set("lost_key", "lost_value")
            # No commit here

        # Second session: reopen and try to get
        with open(db_file, "r+b") as f:
            storage2 = Storage(f)
            tree2 = BinaryTree(storage2)
            with pytest.raises(KeyError):
                tree2.get("lost_key")

    def test_get_from_empty_db_raises_key_error(self, db_file):
        with open(db_file, "r+b") as f:
            storage = Storage(f)
            tree = BinaryTree(storage)
            with pytest.raises(KeyError):
                tree.get("any_key")
