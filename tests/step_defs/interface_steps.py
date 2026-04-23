# tests/step_defs/interface_steps.py
import io
import pytest
from pytest_bdd import given, when, then

# This import will fail until the class is created
from dbdb.interface import DBDB
from dbdb.physical import Storage
from dbdb.binary_tree import BinaryTree


@pytest.fixture
def context():
    return {}


@given("a temporary file object", target_fixture="temp_file")
def temp_file_object():
    return io.BytesIO()


@when("I create a DBDB instance with the file object")
def create_dbdb_instance(temp_file, context):
    db = DBDB(temp_file)
    context["db"] = db


@then("the DBDB instance should be successfully created")
def dbdb_instance_created(context):
    assert "db" in context
    assert isinstance(context["db"], DBDB)


@then("the instance should have a private Storage object")
def instance_has_storage(context):
    assert hasattr(context["db"], "_storage")
    assert isinstance(context["db"]._storage, Storage)


@then("the instance should have a private BinaryTree object")
def instance_has_tree(context):
    assert hasattr(context["db"], "_tree")
    assert isinstance(context["db"]._tree, BinaryTree)
