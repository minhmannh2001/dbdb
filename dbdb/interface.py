# dbdb/interface.py
from dbdb.physical import Storage
from dbdb.binary_tree import BinaryTree


class DBDB:
    """
    A public-facing API for the database, providing a dictionary-like
    interface to the underlying key-value store.
    """

    def __init__(self, f):
        """
        Initializes a new DBDB instance.

        :param f: A file-like object for the database storage.
        """
        self._storage = Storage(f)
        self._tree = BinaryTree(self._storage)

    def _assert_not_closed(self):
        if self._storage.closed:
            raise ValueError("Database closed.")

    def __getitem__(self, key):
        self._assert_not_closed()
        return self._tree.get(key)

    def __setitem__(self, key, value):
        self._assert_not_closed()
        return self._tree.set(key, value)

    def __delitem__(self, key):
        self._assert_not_closed()
        return self._tree.pop(key)

    def __contains__(self, key):
        self._assert_not_closed()
        try:
            self._tree.get(key)
            return True
        except KeyError:
            return False

    def __len__(self):
        self._assert_not_closed()
        return len(self._tree)
