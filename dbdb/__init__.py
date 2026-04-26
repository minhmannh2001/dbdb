# dbdb/__init__.py
import os
from .interface import DBDB

__all__ = ["connect"]


def connect(dbname: str, tree_type: str = "bst") -> DBDB:
    """
    Connect to a database file.

    :param dbname: The path to the database file.
    :param tree_type: The type of tree to use ("bst", "avl", or "btree"). Defaults to "bst".
                      If opening an existing file, its stored tree type takes precedence.
    :return: A DBDB object.
    """
    try:
        f = open(dbname, "r+b")
    except IOError:
        f = open(dbname, "w+b")
    return DBDB(f, tree_type=tree_type)
