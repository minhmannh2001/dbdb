# dbdb/interface.py
import os
import random
import tempfile
from typing import IO

from dbdb.physical import Storage


class DBDB:
    """
    A public-facing API for the database, providing a dictionary-like
    interface to the underlying key-value store.
    """

    def __init__(self, f: IO, tree_type: str = "bst"):
        """
        Initializes a new DBDB instance.

        :param f: A file-like object for the database storage.
        :param tree_type: "bst" or "avl". Ignored if the file already contains a tree type.
        """
        self._storage = Storage(f)

        root_addr = self._storage.get_root_address()
        if root_addr == 0:
            # Empty or new file, we can set the requested type
            type_flag = 1 if tree_type == "avl" else 0
            self._storage.set_tree_type(type_flag)
        else:
            # Existing file with data, read its actual tree type
            type_flag = self._storage.get_tree_type()

        self._tree_type_flag = type_flag
        self._init_tree()

    def _init_tree(self) -> None:
        if self._tree_type_flag == 1:
            from dbdb.avl_tree import AVLTree

            self._tree = AVLTree(self._storage)
        else:
            from dbdb.binary_tree import BinaryTree

            self._tree = BinaryTree(self._storage)

    def _assert_not_closed(self) -> None:
        if self._storage.closed:
            raise ValueError("Database closed.")

    def _reopen_if_replaced(self) -> None:
        """Reopen storage if another process replaced the file (e.g. via compaction)."""
        if getattr(self._storage, "is_file_replaced", lambda: False)():
            if self._storage.is_file_replaced():
                path = self._storage._f.name
                self._storage.close()
                self._storage = Storage(open(path, "r+b"))
                self._tree_type_flag = self._storage.get_tree_type()
                self._init_tree()

    def _prepare_write(self) -> None:
        """Acquire the write lock, closing the TOCTOU window for write operations.

        _reopen_if_replaced() alone is not sufficient for writes: compact could
        run between the pre-lock check and the moment the lock is acquired, leaving
        the write targeting the orphaned inode.

        Fix: after acquiring the lock, check again. Once we hold the exclusive lock
        compact cannot run, so a True result here is conclusive.

        Two outcomes after this method returns:
          - No replacement: lock held, tree ref refreshed. self._tree.set/pop
            will see locked=True and skip their own lock+refresh.
          - Replacement detected post-lock: old storage closed (lock released),
            new storage+tree opened. self._tree.set/pop will acquire the lock
            and refresh on the new storage.
        """
        self._reopen_if_replaced()
        if self._storage.lock():
            if (
                getattr(self._storage, "is_file_replaced", lambda: False)()
                and self._storage.is_file_replaced()
            ):
                path = self._storage._f.name
                self._storage.close()
                self._storage = Storage(open(path, "r+b"))
                self._tree_type_flag = self._storage.get_tree_type()
                self._init_tree()
            else:
                self._tree._refresh_tree_ref()

    def __getitem__(self, key: str) -> str:
        self._assert_not_closed()
        self._reopen_if_replaced()
        return self._tree.get(key)

    def __setitem__(self, key: str, value: str) -> None:
        self._assert_not_closed()
        self._prepare_write()
        return self._tree.set(key, value)

    def __delitem__(self, key: str) -> None:
        self._assert_not_closed()
        self._prepare_write()
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
        self._reopen_if_replaced()
        return self._tree.items()

    def compact(self) -> None:
        self._assert_not_closed()
        self._storage.lock()
        try:
            # Create a temporary file in the same directory to ensure
            # atomic rename works across filesystems.
            db_dir = os.path.dirname(self._storage._f.name)
            with tempfile.NamedTemporaryFile(dir=db_dir, delete=False) as f:
                temp_path = f.name

            # Local import to break circular dependency
            from dbdb import connect

            tree_type_str = "avl" if self._tree_type_flag == 1 else "bst"

            # Open a new DB for the temp file and copy data
            new_db = connect(temp_path, tree_type=tree_type_str)
            try:
                # To avoid a skewed tree that would result from inserting
                # keys in sorted order, we load all items into memory,
                # shuffle them, and then insert. This is a memory-intensive
                # trade-off against the recursion limit.
                items = list(self.items())
                random.shuffle(items)
                for key, value in items:
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

            # Re-open the storage for the current instance with the new file
            new_f = open(original_path, "r+b")
            self._storage = Storage(new_f)
            self._init_tree()

        except Exception:
            # If anything goes wrong, try to clean up the temp file
            if "temp_path" in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise
        finally:
            # Ensure the lock is always released
            if self._storage.locked:
                self._storage.unlock()
