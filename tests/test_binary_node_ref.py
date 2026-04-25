"""Tests for BinaryNode / BinaryNodeRef (Phase 3)."""

import io
import msgpack
from dataclasses import dataclass

import pytest

from dbdb.binary_tree import BinaryNode, BinaryNodeRef
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
        height=0,
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
        height=0,
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
    root = BinaryNode(left, "k", ValueRef("x"), right, length=1, height=0)
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
        height=0,
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
        height=0,
    )
    node.store_refs(storage)
    assert value.address != 0
    assert left.address != 0
    assert right.address != 0


def test_binary_node_ref_prepare_to_store_persists_leaf_value_and_children():
    """Root ref's hook runs `store_refs` so value/child refs have addresses before root bytes."""
    buf = io.BytesIO()
    storage = Storage(buf)
    left = ValueRef("")
    right = ValueRef("")
    value = ValueRef("leaf")
    node = BinaryNode(
        left_ref=left, key="k", value_ref=value, right_ref=right, length=1, height=0
    )
    root = BinaryNodeRef(referent=node)
    root.prepare_to_store(storage)
    assert value.address != 0
    assert left.address != 0
    assert right.address != 0


def test_binary_node_ref_prepare_to_store_no_referent_is_safe():
    BinaryNodeRef().prepare_to_store(Storage(io.BytesIO()))


def test_binary_node_ref_referent_to_bytes_packs_address_dict():
    """Packed payload is a dict with left, key, value, right, length (addresses only for refs)."""
    left = BinaryNodeRef(address=11)
    right = BinaryNodeRef(address=22)
    value = ValueRef(address=33)
    node = BinaryNode(
        left_ref=left, key="k", value_ref=value, right_ref=right, length=7, height=0
    )
    raw = BinaryNodeRef.referent_to_bytes(node)
    d = msgpack.unpackb(raw, raw=False)
    assert set(d) == {"left", "key", "value", "right", "length", "height"}
    assert d["left"] == 11
    assert d["key"] == "k"
    assert d["value"] == 33
    assert d["right"] == 22
    assert d["length"] == 7


def test_binary_node_ref_length_delegates_to_loaded_referent():
    node = BinaryNode(BinaryNodeRef(), "k", ValueRef("v"), BinaryNodeRef(), 42, 0)
    ref = BinaryNodeRef(referent=node)
    assert ref.length == 42


def test_binary_node_ref_length_empty_ref_is_zero():
    assert BinaryNodeRef().length == 0
    assert BinaryNodeRef(referent=None, address=0).length == 0


def test_binary_node_ref_length_unloaded_with_address_raises():
    with pytest.raises(RuntimeError, match="unloaded node"):
        BinaryNodeRef(address=4096).length


def test_binary_node_ref_bytes_to_referent_inverts_packed_dict():
    raw = BinaryNodeRef.referent_to_bytes(
        BinaryNode(
            BinaryNodeRef(address=5),
            "x",
            ValueRef(address=6),
            BinaryNodeRef(address=7),
            2,
            0,
        )
    )
    node = BinaryNodeRef.bytes_to_referent(raw)
    assert node.key == "x" and node.length == 2
    assert isinstance(node.left_ref, BinaryNodeRef) and node.left_ref.address == 5
    assert isinstance(node.right_ref, BinaryNodeRef) and node.right_ref.address == 7
    assert isinstance(node.value_ref, ValueRef) and node.value_ref.address == 6


def test_binary_node_ref_roundtrip_store_then_get_matches_chapter_leaf_shape():
    """RAM leaf with `BinaryNodeRef` children → store → address-only ref → `get` rebuilds node."""
    buf = io.BytesIO()
    storage = Storage(buf)
    node = BinaryNode(
        BinaryNodeRef(),
        "k",
        ValueRef("payload"),
        BinaryNodeRef(),
        1,
        0,
    )
    root = BinaryNodeRef(referent=node)
    root.store(storage)
    addr = root.address
    loaded = BinaryNodeRef(address=addr).get(storage)
    assert loaded.key == "k"
    assert loaded.length == 1
    assert loaded.value_ref.get(storage) == "payload"
    assert isinstance(loaded.left_ref, BinaryNodeRef)
    assert isinstance(loaded.right_ref, BinaryNodeRef)
    assert loaded.left_ref.address == 0
    assert loaded.right_ref.address == 0


def test_binary_node_ref_store_nested_persists_packed_nodes():
    """Nested `store` writes inner node bytes first, then outer root; blobs unpack to address dicts."""
    buf = io.BytesIO()
    storage = Storage(buf)
    inner = BinaryNode(
        ValueRef("L"),
        "inner",
        ValueRef("mid"),
        ValueRef("R"),
        length=1,
        height=0,
    )
    inner_wrapped = BinaryNodeRef(referent=inner)
    outer = BinaryNode(
        inner_wrapped,
        "root",
        ValueRef("rootv"),
        ValueRef(""),
        length=1,
        height=1,
    )
    root = BinaryNodeRef(referent=outer)
    root.store(storage)

    assert root.address != 0
    outer_doc = msgpack.unpackb(storage.read(root.address), raw=False)
    assert set(outer_doc) == {"left", "key", "value", "right", "length", "height"}
    assert outer_doc["key"] == "root"
    assert outer_doc["length"] == 1
    assert outer_doc["left"] == inner_wrapped.address
    assert outer_doc["value"] != 0
    assert outer_doc["right"] != 0

    assert inner_wrapped.address != 0
    inner_doc = msgpack.unpackb(storage.read(inner_wrapped.address), raw=False)
    assert inner_doc["key"] == "inner"
    assert set(inner_doc) == {"left", "key", "value", "right", "length", "height"}
    assert inner_doc["length"] == 1
    assert all(inner_doc[k] != 0 for k in ("left", "value", "right"))
