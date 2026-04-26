"""Unit tests for BTree insertion with splitting."""

import io

import pytest

from dbdb.btree import BTree, BTreeNode, BTreeNodeRef
from dbdb.logical import ValueRef
from dbdb.physical import Storage


def _get_leaf_depths(root, storage, depth=0):
    """Helper to get depths of all leaves."""
    if root.is_leaf:
        return [depth]
    depths = []
    for child_ref in root.child_refs:
        child = child_ref.get(storage)
        depths.extend(_get_leaf_depths(child, storage, depth + 1))
    return depths


def test_insert_empty_tree():
    """Insert into empty tree creates single-node leaf."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    new_ref = tree._insert(None, "a", ValueRef("val_a"))
    tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    assert root.is_leaf
    assert root.keys == ["a"]
    assert len(root.value_refs) == 1
    assert root.child_refs == []
    assert root.length == 1
    assert list(tree) == ["a"]


def test_insert_fill_leaf():
    """Insert up to 5 keys (2t-1), no split."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    keys = ["a", "b", "c", "d", "e"]
    for key in keys:
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    assert root.is_leaf
    assert root.keys == keys
    assert root.length == 5
    assert list(tree) == keys


def test_insert_split_root():
    """Insert 6th key splits root, height grows."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    keys = ["a", "b", "c", "d", "e", "f"]
    for key in keys:
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    assert not root.is_leaf
    assert root.keys == ["c"]  # median
    assert len(root.child_refs) == 2
    assert root.length == 6

    # Check children
    left = root.child_refs[0].get(tree._storage)
    right = root.child_refs[1].get(tree._storage)
    assert left.is_leaf and left.keys == ["a", "b"]
    assert right.is_leaf and right.keys == ["d", "e", "f"]

    # All leaves at same depth
    depths = _get_leaf_depths(root, tree._storage)
    assert all(d == depths[0] for d in depths)
    assert list(tree) == keys


def test_insert_sorted_order_balanced():
    """Insert in sorted order, tree stays balanced."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    keys = ["a", "b", "c", "d", "e", "f", "g"]
    for key in keys:
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    depths = _get_leaf_depths(root, tree._storage)
    assert all(d == depths[0] for d in depths)
    assert list(tree) == keys


def test_insert_reverse_order_balanced():
    """Insert in reverse order, tree stays balanced."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    keys = ["g", "f", "e", "d", "c", "b", "a"]
    for key in keys:
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    depths = _get_leaf_depths(root, tree._storage)
    assert all(d == depths[0] for d in depths)
    assert list(tree) == sorted(keys)


def test_insert_duplicate_updates_value():
    """Insert duplicate key updates value, length unchanged."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    # Insert "a"
    new_ref = tree._insert(None, "a", ValueRef("val1"))
    tree._tree_ref = new_ref

    # Insert "a" again
    root = tree._follow(tree._tree_ref)
    new_ref = tree._insert(root, "a", ValueRef("val2"))
    tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    assert root.length == 1
    assert tree.get("a") == "val2"
    assert list(tree) == ["a"]


def test_insert_random_sorted_iteration():
    """After random inserts, in-order iteration yields sorted keys."""
    import random
    random.seed(42)

    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    keys = [f"key{i}" for i in range(20)]
    random_keys = keys.copy()
    random.shuffle(random_keys)

    for key in random_keys:
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    depths = _get_leaf_depths(root, tree._storage)
    assert all(d == depths[0] for d in depths)
    assert list(tree) == sorted(keys)
    assert root.length == 20


def test_length_after_inserts():
    """Length on root ref equals total key count."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    keys = ["a", "b", "c", "d", "e", "f"]
    for i, key in enumerate(keys, 1):
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

        root = tree._follow(tree._tree_ref)
        assert root.length == i