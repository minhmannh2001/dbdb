# tests/test_connect_function.py
import os
import tempfile
import pytest

import dbdb
from dbdb.interface import DBDB


@pytest.fixture
def temp_db_path():
    # A fixture to create and clean up a temporary database file path
    fd, path = tempfile.mkstemp()
    os.close(fd)
    os.remove(path)  # Ensure it doesn't exist initially
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestConnect:
    def test_connect_creates_new_file(self, temp_db_path):
        assert not os.path.exists(temp_db_path)
        db = dbdb.connect(temp_db_path)
        assert os.path.exists(temp_db_path)
        db.close()

    def test_connect_opens_existing_file(self, temp_db_path):
        # Create and populate a DB file first
        db1 = dbdb.connect(temp_db_path)
        db1["a"] = "1"
        db1.commit()
        db1.close()

        # Now, connect to it again and verify content
        db2 = dbdb.connect(temp_db_path)
        assert db2["a"] == "1"
        db2.close()
