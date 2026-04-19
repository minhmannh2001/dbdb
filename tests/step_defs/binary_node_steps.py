"""Step definitions for binary_node.feature."""

from dataclasses import dataclass

from pytest_bdd import given, then, when

from dbdb.binary_tree import BinaryNode, BinaryNodeRef
from dbdb.logical import ValueRef


@dataclass
class _StubBranchRef:
    """Minimal stand-in for a child ref with a subtree size (matches unit tests)."""

    length: int


@given("a chapter-shaped leaf behind a root BinaryNodeRef", target_fixture="root_ref")
def chapter_shaped_leaf_root_ref():
    return BinaryNodeRef(
        referent=BinaryNode(
            BinaryNodeRef(),
            "bdd-key",
            ValueRef("pay\u2014bdd"),
            BinaryNodeRef(),
            1,
        )
    )


@when("we persist that root reference")
def persist_root_ref(root_ref, storage):
    root_ref.store(storage)


@when("we load the tree root using only its disk address", target_fixture="loaded_root")
def load_root_by_address(root_ref, storage):
    return BinaryNodeRef(address=root_ref.address).get(storage)


@then("the node exposes the expected key and subtree length")
def assert_loaded_key_and_length(loaded_root):
    assert loaded_root.key == "bdd-key"
    assert loaded_root.length == 1


@then("the value slot reloads the UTF-8 payload from storage")
def assert_value_payload(loaded_root, storage):
    assert loaded_root.value_ref.get(storage) == "pay\u2014bdd"


@given("a single-key leaf with placeholder child refs", target_fixture="leaf")
def leaf_with_placeholder_children():
    return BinaryNode(ValueRef(), "k", ValueRef("v"), ValueRef(), 1)


@when(
    "we rebuild from-node with a stub left branch of larger subtree size",
    target_fixture="grown",
)
def rebuild_from_node_with_stub_left(leaf):
    return BinaryNode.from_node(leaf, left_ref=_StubBranchRef(length=1))


@then("the aggregate subtree length reflects the branch delta")
def assert_subtree_length_delta(grown):
    assert grown.length == 2
