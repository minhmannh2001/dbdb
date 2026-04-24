# tests/test_format_change.py
import os
import tempfile
import pytest
import dbdb


class TestFormatChange:
    def test_can_write_and_read_msgpack_db(self):
        # We use a tempfile context that deletes the file on exit
        # to ensure cleanup, but we need the path to survive the
        # 'with' block to reopen it. So we get the name and then
        # manually handle cleanup.
        f = tempfile.NamedTemporaryFile(delete=False)
        path = f.name
        f.close()

        try:
            db = dbdb.connect(path)
            db["c"] = "3"
            db["d"] = "4"
            db.commit()
            db.close()

            db2 = dbdb.connect(path)
            assert db2["c"] == "3"
            assert db2["d"] == "4"
            db2.close()
        finally:
            os.remove(path)
