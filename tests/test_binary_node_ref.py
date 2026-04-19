"""Tests for BinaryNode / BinaryNodeRef (Phase 3)."""

import io
from dataclasses import dataclass

from dbdb.binary_tree import BinaryNode
from dbdb.logical import ValueRef
from dbdb.physical import Storage


@dataclass
class _SubtreeRef:
    """Stand-in for a loaded child node ref with a subtree size (before BinaryNodeRef exists)."""

    length: int


def test_binary_node_leaf_in_ram():
    """Single-node tree shape: empty child refs, one key/value, length 1."""
    left = ValueRef()
    right = ValueRef()
    value = ValueRef("payload")
    node = BinaryNode(
        left_ref=left,
        key="k",
        value_ref=value,
        right_ref=right,
        length=1,
    )
    assert node.left_ref is left
    assert node.key == "k"
    assert node.value_ref is value
    assert node.right_ref is right
    assert node.length == 1


def test_from_node_updates_length_after_simulated_left_insert():
    """Replacing left child ref adjusts aggregate length by new subtree size minus old."""
    left = ValueRef()
    right = ValueRef()
    value = ValueRef("v")
    root = BinaryNode(
        left_ref=left,
        key="root",
        value_ref=value,
        right_ref=right,
        length=1,
    )
    new_left = _SubtreeRef(length=1)
    updated = BinaryNode.from_node(root, left_ref=new_left)
    assert updated.left_ref is new_left
    assert updated.right_ref is right
    assert updated.key == "root"
    assert updated.value_ref is value
    assert updated.length == 2


def test_from_node_updates_length_when_both_children_change():
    left = ValueRef()
    right = ValueRef()
    root = BinaryNode(left, "k", ValueRef("x"), right, length=1)
    out = BinaryNode.from_node(
        root,
        left_ref=_SubtreeRef(length=2),
        right_ref=_SubtreeRef(length=3),
    )
    assert out.length == 1 + (2 - 0) + (3 - 0) == 6


def test_from_node_value_replace_does_not_touch_subtree_length_formula():
    root = BinaryNode(
        ValueRef(),
        "k",
        ValueRef("old"),
        ValueRef(),
        length=1,
    )
    new_val = ValueRef("new")
    out = BinaryNode.from_node(root, value_ref=new_val)
    assert out.value_ref is new_val
    assert out.length == 1


def test_binary_node_leaf_store_refs_persists_all_three_refs():
    """Leaf: empty-string placeholders for children persist like the value ref."""
    buf = io.BytesIO()
    storage = Storage(buf)
    left = ValueRef("")
    right = ValueRef("")
    value = ValueRef("payload")
    node = BinaryNode(
        left_ref=left,
        key="k",
        value_ref=value,
        right_ref=right,
        length=1,
    )
    node.store_refs(storage)
    assert value.address != 0
    assert left.address != 0
    assert right.address != 0
