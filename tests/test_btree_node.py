"""Unit tests for BTreeNode and BTreeNodeRef."""

import io

import pytest

from dbdb.btree import BTreeNode, BTreeNodeRef
from dbdb.logical import ValueRef
from dbdb.physical import Storage


def test_leaf_node_creation():
    node = BTreeNode(
        keys=["key1"],
        value_refs=[ValueRef("value1")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    assert node.is_leaf is True
    assert node.child_refs == []


def test_internal_node_creation():
    node = BTreeNode(
        keys=["key1", "key2"],
        value_refs=[ValueRef("value1"), ValueRef("value2")],
        child_refs=[BTreeNodeRef(), BTreeNodeRef(), BTreeNodeRef()],
        length=5,  # total in subtree
        is_leaf=False
    )
    assert node.is_leaf is False
    assert len(node.child_refs) == len(node.keys) + 1 == 3


def test_leaf_node_with_child_refs_raises():
    with pytest.raises(ValueError, match="Leaf node must have empty child_refs"):
        BTreeNode(
            keys=["key1"],
            value_refs=[ValueRef("value1")],
            child_refs=[BTreeNodeRef()],
            length=1,
            is_leaf=True
        )


def test_internal_node_wrong_child_count_raises():
    with pytest.raises(ValueError, match="Internal node must have len\\(child_refs\\) == len\\(keys\\) \\+ 1"):
        BTreeNode(
            keys=["key1", "key2"],
            value_refs=[ValueRef("value1"), ValueRef("value2")],
            child_refs=[BTreeNodeRef(), BTreeNodeRef()],  # 2, but should be 3
            length=5,
            is_leaf=False
        )


def test_length_property_null_ref():
    ref = BTreeNodeRef(address=0)
    assert ref.length == 0


def test_length_property_loaded_ref():
    node = BTreeNode(
        keys=["key1"],
        value_refs=[ValueRef("value1")],
        child_refs=[],
        length=10,
        is_leaf=True
    )
    ref = BTreeNodeRef(referent=node)
    assert ref.length == 10


def test_length_property_unloaded_non_null_raises():
    ref = BTreeNodeRef(address=123)
    with pytest.raises(RuntimeError, match="Asking for BTreeNodeRef length of unloaded node"):
        _ = ref.length


def test_round_trip_serialization():
    original = BTreeNode(
        keys=["key1", "key2"],
        value_refs=[ValueRef("value1"), ValueRef("value2")],
        child_refs=[BTreeNodeRef(address=10), BTreeNodeRef(address=20), BTreeNodeRef(address=30)],
        length=42,
        is_leaf=False
    )
    data = BTreeNodeRef.referent_to_bytes(original)
    reconstructed = BTreeNodeRef.bytes_to_referent(data)
    
    assert reconstructed.keys == original.keys
    assert reconstructed.length == original.length
    assert reconstructed.is_leaf == original.is_leaf
    assert len(reconstructed.value_refs) == len(original.value_refs)
    assert len(reconstructed.child_refs) == len(original.child_refs)
    # Addresses should be preserved
    assert reconstructed.value_refs[0].address == 0  # not set yet
    assert reconstructed.child_refs[0].address == 10


def test_prepare_to_store_stores_nested_refs():
    # Create a node with value refs and child refs that have referents
    value_ref = ValueRef("value")
    child_node = BTreeNode(
        keys=["child_key"],
        value_refs=[ValueRef("child_value")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    child_ref = BTreeNodeRef(referent=child_node)
    empty_child_ref = BTreeNodeRef()  # Another child ref for internal node

    node = BTreeNode(
        keys=["key"],
        value_refs=[value_ref],
        child_refs=[child_ref, empty_child_ref],
        length=2,
        is_leaf=False
    )
    ref = BTreeNodeRef(referent=node)

    # Mock storage
    storage = Storage(io.BytesIO())
    storage.lock()

    # Before store, no addresses
    assert value_ref.address == 0
    assert child_ref.address == 0
    assert empty_child_ref.address == 0
    assert ref.address == 0

    # Prepare to store
    ref.prepare_to_store(storage)

    # Now they should have addresses
    assert value_ref.address != 0
    assert child_ref.address != 0
    # Empty child ref might not have address if no referent, but that's ok
    assert ref.address == 0  # Node ref itself not stored yet