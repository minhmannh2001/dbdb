"""Step definitions for smoke.feature (pytest-bdd)."""

from pytest_bdd import given, then, when


@given("the Python path includes the project layout")
def project_layout_ok():
    """Editable install + pytest.ini pythonpath satisfy layout; no-op."""
    return


@when("we import the dbdb package", target_fixture="dbdb_pkg")
def import_dbdb():
    import dbdb

    return dbdb


@then("the dbdb package exposes a __file__ path")
def dbdb_has_file(dbdb_pkg):
    assert getattr(dbdb_pkg, "__file__", None)
