"""BDD: physical Storage binds a file-like object."""

from pytest_bdd import scenario


@scenario("storage.feature", "Storage wraps a file-like object")
def test_storage_wraps_file_like_bdd():
    pass
