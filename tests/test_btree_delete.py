"""Unit tests for BTree deletion with merging and borrowing."""

import io
import random

import pytest

from dbdb.btree import BTree, BTreeNode, BTreeNodeRef
from dbdb.logical import ValueRef
from dbdb.physical import Storage


def test_delete_single_key_empty_tree():
    """Delete from single-key tree makes it empty."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    # Insert one key
    new_ref = tree._insert(None, "a", ValueRef("val_a"))
    tree._tree_ref = new_ref

    # Delete it
    root = tree._follow(tree._tree_ref)
    new_ref = tree._delete(root, "a")
    tree._tree_ref = new_ref

    assert tree._tree_ref is None
    assert list(tree) == []


def test_delete_nonexistent_key():
    """Delete non-existent key raises KeyError."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    # Insert one key
    new_ref = tree._insert(None, "a", ValueRef("val_a"))
    tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    with pytest.raises(KeyError):
        tree._delete(root, "b")


def test_delete_from_leaf_more_than_min():
    """Delete from leaf with more than t-1 keys, no structural change."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    # Insert 3 keys (t=3, min=2)
    keys = ["a", "b", "c"]
    for key in keys:
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    assert root.is_leaf and len(root.keys) == 3

    # Delete "b"
    new_ref = tree._delete(root, "b")
    tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    assert root.is_leaf
    assert root.keys == ["a", "c"]
    assert list(tree) == ["a", "c"]


def test_delete_borrow_from_left():
    """Delete from leaf, merges since can't borrow."""
    # Manually construct tree: root with ["b"], children: left leaf ["a"], right leaf ["c","d"]
    left_leaf = BTreeNode(["a"], [ValueRef("val_a")], [], 1, True)
    right_leaf = BTreeNode(["c", "d"], [ValueRef("val_c"), ValueRef("val_d")], [], 2, True)
    root = BTreeNode(
        ["b"],
        [ValueRef("val_b")],
        [BTreeNodeRef(referent=left_leaf), BTreeNodeRef(referent=right_leaf)],
        4, False
    )

    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()
    tree._tree_ref = BTreeNodeRef(referent=root)

    # Delete "c", merges to ["a","b","c","d"], delete "c" -> ["a","b","d"]
    new_ref = tree._delete(root, "c")
    tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    assert root.keys == ["a", "b", "d"]
    assert root.is_leaf
    assert list(tree) == ["a", "b", "d"]


def test_delete_internal_node():
    """Delete from internal node, merges since can't use pred/succ."""
    # Tree with internal node
    left_leaf = BTreeNode(["a"], [ValueRef("val_a")], [], 1, True)
    right_leaf = BTreeNode(["c", "d"], [ValueRef("val_c"), ValueRef("val_d")], [], 2, True)
    root = BTreeNode(
        ["b"],
        [ValueRef("val_b")],
        [BTreeNodeRef(referent=left_leaf), BTreeNodeRef(referent=right_leaf)],
        4, False
    )

    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()
    tree._tree_ref = BTreeNodeRef(referent=root)

    # Delete "b", merges to ["a","b","c","d"], delete "b" -> ["a","c","d"]
    new_ref = tree._delete(root, "b")
    tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    assert root.keys == ["a", "c", "d"]
    assert root.is_leaf
    assert list(tree) == ["a", "c", "d"]


def test_delete_root_collapse():
    """Delete last key from 1-level tree, root collapses."""
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    # Insert one key
    new_ref = tree._insert(None, "a", ValueRef("val_a"))
    tree._tree_ref = new_ref

    # Delete it
    root = tree._follow(tree._tree_ref)
    new_ref = tree._delete(root, "a")
    tree._tree_ref = new_ref

    assert tree._tree_ref is None


def test_random_inserts_deletes_to_empty():
    """After N random inserts then N deletes, tree is empty."""
    random.seed(42)
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    keys = [f"key{i}" for i in range(10)]
    random_keys = keys.copy()
    random.shuffle(random_keys)

    # Insert
    for key in random_keys:
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

    # Delete in random order
    random.shuffle(random_keys)
    for key in random_keys:
        root = tree._follow(tree._tree_ref)
        new_ref = tree._delete(root, key)
        tree._tree_ref = new_ref

    assert tree._tree_ref is None or tree._follow(tree._tree_ref) is None


def test_random_inserts_partial_deletes():
    """After random inserts and partial deletes, iteration correct."""
    random.seed(123)
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    keys = [f"key{i}" for i in range(15)]
    random_keys = keys.copy()
    random.shuffle(random_keys)

    # Insert all
    for key in random_keys:
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

    # Delete half
    to_delete = random_keys[:7]
    remaining = sorted(random_keys[7:])

    for key in to_delete:
        root = tree._follow(tree._tree_ref)
        new_ref = tree._delete(root, key)
        tree._tree_ref = new_ref

    assert list(tree) == remaining


def test_min_keys_invariant():
    """Every non-root node maintains t-1 <= len(keys) <= 2t-1."""
    random.seed(99)
    tree = BTree(Storage(io.BytesIO()))
    tree._storage.lock()

    keys = [f"key{i}" for i in range(20)]
    random_keys = keys.copy()
    random.shuffle(random_keys)

    # Insert all
    for key in random_keys:
        root = tree._follow(tree._tree_ref) if tree._tree_ref else None
        new_ref = tree._insert(root, key, ValueRef(f"val_{key}"))
        tree._tree_ref = new_ref

    def check_min_keys(node, is_root=False):
        if node is None:
            return
        if not is_root:
            assert 2 <= len(node.keys) <= 5  # t-1=2, 2t-1=5
        if not node.is_leaf:
            for child_ref in node.child_refs:
                child = child_ref.get(tree._storage)
                check_min_keys(child, False)

    root = tree._follow(tree._tree_ref)
    check_min_keys(root, True)

    # Delete some
    to_delete = random_keys[:10]
    for key in to_delete:
        root = tree._follow(tree._tree_ref)
        new_ref = tree._delete(root, key)
        tree._tree_ref = new_ref

    root = tree._follow(tree._tree_ref)
    if root:
        check_min_keys(root, True)