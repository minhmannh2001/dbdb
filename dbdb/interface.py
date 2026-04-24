# dbdb/interface.py
from typing import IO

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

    def __getitem__(self, key: str) -> str:
        self._assert_not_closed()
        return self._tree.get(key)

    def __setitem__(self, key: str, value: str) -> None:
        self._assert_not_closed()
        return self._tree.set(key, value)

    def __delitem__(self, key: str) -> None:
        self._assert_not_closed()
        return self._tree.pop(key)

    def __contains__(self, key: str) -> bool:
        self._assert_not_closed()
        try:
            self._tree.get(key)
            return True
        except KeyError:
            return False

    def __len__(self) -> int:
        self._assert_not_closed()
        return len(self._tree)

    def commit(self) -> None:
        self._assert_not_closed()
        self._tree.commit()

    def close(self) -> None:
        self._storage.close()
