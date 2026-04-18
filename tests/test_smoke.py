"""Smoke tests: minimal harness before Storage and tree modules exist."""


def test_import_dbdb_package():
    import dbdb

    assert dbdb.__file__
