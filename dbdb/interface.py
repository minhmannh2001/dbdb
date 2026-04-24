# dbdb/interface.py
import os
import tempfile
from typing import IO

import dbdb
from dbdb.physical import Storage
from dbdb.binary_tree import BinaryTree


class DBDB:
    """
    A public-facing API for the database, providing a dictionary-like
    interface to the underlying key-value store.
    """

    def __init__(self, f: IO):
        """
        Initializes a new DBDB instance.

        :param f: A file-like object for the database storage.
        """
        self._storage = Storage(f)
        self._tree = BinaryTree(self._storage)

    def _assert_not_closed(self) -> None:
        if self._storage.closed:
            raise ValueError("Database closed.")

    def _reopen_if_replaced(self) -> None:
        """Reopen storage if another process replaced the file (e.g. via compaction)."""
        if self._storage.is_file_replaced():
            path = self._storage._f.name
            self._storage.close()
            self._storage = Storage(open(path, "r+b"))
            self._tree = BinaryTree(self._storage)

    def __getitem__(self, key: str) -> str:
        self._assert_not_closed()
        self._reopen_if_replaced()
        return self._tree.get(key)

    def __setitem__(self, key: str, value: str) -> None:
        self._assert_not_closed()
        self._reopen_if_replaced()
        return self._tree.set(key, value)

    def __delitem__(self, key: str) -> None:
        self._assert_not_closed()
        self._reopen_if_replaced()
        return self._tree.pop(key)

    def __contains__(self, key: str) -> bool:
        self._assert_not_closed()
        self._reopen_if_replaced()
        try:
            self._tree.get(key)
            return True
        except KeyError:
            return False

    def __len__(self) -> int:
        self._assert_not_closed()
        self._reopen_if_replaced()
        return len(self._tree)

    def commit(self) -> None:
        self._assert_not_closed()
        self._tree.commit()

    def close(self) -> None:
        self._storage.close()

    def __iter__(self):
        return iter(self._tree)

    def items(self):
        self._assert_not_closed()
        for key in self:
            yield (key, self[key])

    def compact(self) -> None:
        self._assert_not_closed()
        self._storage.lock()
        try:
            # Create a temporary file in the same directory to ensure
            # atomic rename works across filesystems.
            db_dir = os.path.dirname(self._storage._f.name)
            with tempfile.NamedTemporaryFile(dir=db_dir, delete=False) as f:
                temp_path = f.name

            # Open a new DB for the temp file and copy data
            new_db = dbdb.connect(temp_path)
            try:
                for key, value in self.items():
                    new_db[key] = value
                new_db.commit()
            finally:
                new_db.close()

            original_path = self._storage._f.name

            # Rename while holding the lock. POSIX allows renaming open files;
            # readers with existing handles continue reading the old inode safely
            # until they close. Writers blocked on the lock will open original_path
            # after close() and find the compacted file.
            os.rename(temp_path, original_path)

            # Close after rename so the lock covers the rename itself.
            self._storage.close()

            new_f = open(original_path, "r+b")
            self._storage = Storage(new_f)
            self._tree = BinaryTree(self._storage)

        except Exception:
            # If anything goes wrong, try to clean up the temp file
            if "temp_path" in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise
        finally:
            # Ensure the lock is always released
            if self._storage.locked:
                self._storage.unlock()
