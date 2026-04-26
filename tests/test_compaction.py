# tests/test_compaction.py
import os
import tempfile
import pytest

import dbdb


class TestCompaction:
    @pytest.mark.parametrize("tree_type", ["bst", "avl"])
    def test_compaction_reduces_size_and_keeps_data(self, tree_type):
        f = tempfile.NamedTemporaryFile(delete=False)
        path = f.name
        f.close()

        try:
            db = dbdb.connect(path, tree_type=tree_type)
            db["a"] = "1" * 1000
            db.commit()
            db["a"] = "2" * 1000  # Overwrite to create garbage
            db.commit()
            db.close()

            initial_size = os.path.getsize(path)

            # Reopen and compact
            db = dbdb.connect(path)
            db.compact()
            db.close()

            new_size = os.path.getsize(path)

            assert new_size < initial_size

            # Verify data
            db = dbdb.connect(path)
            assert db["a"] == "2" * 1000
            assert len(db) == 1
            db.close()
        finally:
            os.remove(path)
