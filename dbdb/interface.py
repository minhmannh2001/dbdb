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
