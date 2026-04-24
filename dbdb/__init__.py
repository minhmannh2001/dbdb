# dbdb/__init__.py
import os
from .interface import DBDB

__all__ = ["connect"]


def connect(dbname: str) -> DBDB:
    """
    Connect to a database file.

    :param dbname: The path to the database file.
    :return: A DBDB object.
    """
    try:
        f = open(dbname, "r+b")
    except IOError:
        f = open(dbname, "w+b")
    return DBDB(f)
