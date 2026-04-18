"""BDD smoke: binds Gherkin in features/smoke.feature to pytest."""

from pytest_bdd import scenario


@scenario("smoke.feature", "dbdb package is importable")
def test_dbdb_package_importable_bdd():
    """Steps live in tests.step_defs.smoke_steps (loaded via conftest)."""
    pass
