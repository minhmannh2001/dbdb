"""Unit tests for BTree search and iteration."""

import io

import pytest

from dbdb.btree import BTree, BTreeNode, BTreeNodeRef
from dbdb.logical import ValueRef
from dbdb.physical import Storage


def test_search_single_node_leaf_found():
    """Search in a single-node leaf tree: found."""
    node = BTreeNode(
        keys=["a"],
        value_refs=[ValueRef("val_a")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()  # Prevent refresh
    tree._tree_ref = BTreeNodeRef(referent=node)

    assert tree.get("a") == "val_a"


def test_search_single_node_leaf_not_found():
    """Search in a single-node leaf tree: not found."""
    node = BTreeNode(
        keys=["a"],
        value_refs=[ValueRef("val_a")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()  # Prevent refresh
    tree._tree_ref = BTreeNodeRef(referent=node)

    with pytest.raises(KeyError):
        tree.get("b")


def test_search_two_level_tree():
    """Search in a 2-level tree: root with 2 keys, 3 leaf children."""
    # Create leaf children
    leaf0 = BTreeNode(
        keys=["a"],
        value_refs=[ValueRef("val_a")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    leaf1 = BTreeNode(
        keys=["c"],
        value_refs=[ValueRef("val_c")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    leaf2 = BTreeNode(
        keys=["e", "f"],
        value_refs=[ValueRef("val_e"), ValueRef("val_f")],
        child_refs=[],
        length=2,
        is_leaf=True
    )

    # Root node
    root = BTreeNode(
        keys=["b", "d"],
        value_refs=[ValueRef("val_b"), ValueRef("val_d")],
        child_refs=[
            BTreeNodeRef(referent=leaf0),
            BTreeNodeRef(referent=leaf1),
            BTreeNodeRef(referent=leaf2)
        ],
        length=5,  # 1 + 1 + 2 + 1 (root keys)
        is_leaf=False
    )

    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()  # Prevent refresh
    tree._tree_ref = BTreeNodeRef(referent=root)

    # Test found cases
    assert tree.get("a") == "val_a"
    assert tree.get("b") == "val_b"
    assert tree.get("c") == "val_c"
    assert tree.get("d") == "val_d"
    assert tree.get("e") == "val_e"
    assert tree.get("f") == "val_f"


def test_search_two_level_tree_missing():
    """KeyError on missing key in 2-level tree."""
    # Same tree as above
    leaf0 = BTreeNode(
        keys=["a"],
        value_refs=[ValueRef("val_a")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    leaf1 = BTreeNode(
        keys=["c"],
        value_refs=[ValueRef("val_c")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    leaf2 = BTreeNode(
        keys=["e", "f"],
        value_refs=[ValueRef("val_e"), ValueRef("val_f")],
        child_refs=[],
        length=2,
        is_leaf=True
    )

    root = BTreeNode(
        keys=["b", "d"],
        value_refs=[ValueRef("val_b"), ValueRef("val_d")],
        child_refs=[
            BTreeNodeRef(referent=leaf0),
            BTreeNodeRef(referent=leaf1),
            BTreeNodeRef(referent=leaf2)
        ],
        length=5,
        is_leaf=False
    )

    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()  # Prevent refresh
    tree._tree_ref = BTreeNodeRef(referent=root)

    # Test missing keys
    with pytest.raises(KeyError):
        tree.get("z")  # > all
    with pytest.raises(KeyError):
        tree.get("aa")  # between a and b
    with pytest.raises(KeyError):
        tree.get("g")  # > f


def test_iter_keys_single_node():
    """In-order key iteration on single-node leaf."""
    node = BTreeNode(
        keys=["a", "b", "c"],
        value_refs=[ValueRef("1"), ValueRef("2"), ValueRef("3")],
        child_refs=[],
        length=3,
        is_leaf=True
    )
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()  # Prevent refresh
    tree._tree_ref = BTreeNodeRef(referent=node)

    assert list(tree) == ["a", "b", "c"]


def test_iter_keys_two_level():
    """In-order iteration on 2-level tree."""
    # Same tree as search test
    leaf0 = BTreeNode(
        keys=["a"],
        value_refs=[ValueRef("val_a")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    leaf1 = BTreeNode(
        keys=["c"],
        value_refs=[ValueRef("val_c")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    leaf2 = BTreeNode(
        keys=["e", "f"],
        value_refs=[ValueRef("val_e"), ValueRef("val_f")],
        child_refs=[],
        length=2,
        is_leaf=True
    )

    root = BTreeNode(
        keys=["b", "d"],
        value_refs=[ValueRef("val_b"), ValueRef("val_d")],
        child_refs=[
            BTreeNodeRef(referent=leaf0),
            BTreeNodeRef(referent=leaf1),
            BTreeNodeRef(referent=leaf2)
        ],
        length=5,
        is_leaf=False
    )

    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()  # Prevent refresh
    tree._tree_ref = BTreeNodeRef(referent=root)

    assert list(tree) == ["a", "b", "c", "d", "e", "f"]


def test_iter_items_two_level():
    """In-order items iteration on 2-level tree."""
    # Same tree
    leaf0 = BTreeNode(
        keys=["a"],
        value_refs=[ValueRef("val_a")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    leaf1 = BTreeNode(
        keys=["c"],
        value_refs=[ValueRef("val_c")],
        child_refs=[],
        length=1,
        is_leaf=True
    )
    leaf2 = BTreeNode(
        keys=["e", "f"],
        value_refs=[ValueRef("val_e"), ValueRef("val_f")],
        child_refs=[],
        length=2,
        is_leaf=True
    )

    root = BTreeNode(
        keys=["b", "d"],
        value_refs=[ValueRef("val_b"), ValueRef("val_d")],
        child_refs=[
            BTreeNodeRef(referent=leaf0),
            BTreeNodeRef(referent=leaf1),
            BTreeNodeRef(referent=leaf2)
        ],
        length=5,
        is_leaf=False
    )

    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()  # Prevent refresh
    tree._tree_ref = BTreeNodeRef(referent=root)

    expected = [
        ("a", "val_a"),
        ("b", "val_b"),
        ("c", "val_c"),
        ("d", "val_d"),
        ("e", "val_e"),
        ("f", "val_f")
    ]
    assert list(tree.items()) == expected


def test_empty_tree_iter():
    """Empty tree iteration."""
    tree = BTree(Storage(io.BytesIO()))
    # _tree_ref is null ref
    assert list(tree) == []
    assert list(tree.items()) == []