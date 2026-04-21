"""Unit tests for BinaryTree scaffolding (Phase 4 starts with StubStorage)."""

import pytest

from dbdb.binary_tree import BinaryNode, BinaryNodeRef, BinaryTree
from dbdb.logical import ValueRef


class StubStorage:
    """In-memory storage used by tree tests; mirrors chapter-style behavior."""

    def __init__(self):
        self.d = [0]
        self.locked = False

    def lock(self):
        if not self.locked:
            self.locked = True
            return True
        return False

    def unlock(self):
        pass

    def get_root_address(self):
        return 0

    def write(self, data):
        address = len(self.d)
        self.d.append(data)
        return address

    def read(self, address):
        return self.d[address]


def test_stub_storage_starts_unlocked():
    storage = StubStorage()
    assert storage.locked is False


def test_stub_storage_lock_returns_true_then_false():
    storage = StubStorage()
    assert storage.lock() is True
    assert storage.locked is True
    assert storage.lock() is False


def test_stub_storage_write_read_roundtrip():
    storage = StubStorage()
    payload = ValueRef.referent_to_bytes("payload")
    address = storage.write(payload)
    assert address == 1
    assert storage.read(address) == payload


def test_stub_storage_root_address_is_zero_in_phase4_scaffold():
    storage = StubStorage()
    assert storage.get_root_address() == 0


def test_binary_tree_wires_node_and_value_ref_classes():
    tree = BinaryTree(StubStorage())
    assert tree.node_ref_class is BinaryNodeRef
    assert tree.value_ref_class is ValueRef
    assert isinstance(tree._tree_ref, BinaryNodeRef)
    assert tree._tree_ref.address == 0


def test_binary_tree_get_missing_key_raises_key_error():
    tree = BinaryTree(StubStorage())
    with pytest.raises(KeyError):
        tree._get(None, "missing")

    root = BinaryNode(
        left_ref=BinaryNodeRef(),
        key="m",
        value_ref=ValueRef("v"),
        right_ref=BinaryNodeRef(),
        length=1,
    )
    with pytest.raises(KeyError):
        tree._get(root, "x")


def test_binary_tree_insert_none_creates_leaf_node_ref():
    tree = BinaryTree(StubStorage())
    value_ref = ValueRef("b")
    root_ref = tree._insert(None, "a", value_ref)
    root = tree._follow(root_ref)
    assert isinstance(root_ref, BinaryNodeRef)
    assert root.key == "a"
    assert root.length == 1
    assert root.value_ref is value_ref
    assert root.left_ref.length == 0
    assert root.right_ref.length == 0


def test_binary_tree_insert_then_get_single_key():
    tree = BinaryTree(StubStorage())
    root_ref = tree._insert(None, "a", ValueRef("b"))
    root = tree._follow(root_ref)
    assert tree._get(root, "a") == "b"


def test_binary_tree_insert_smaller_key_builds_left_branch():
    tree = BinaryTree(StubStorage())
    root_ref = tree._insert(None, "m", ValueRef("root"))
    root = tree._follow(root_ref)
    new_root_ref = tree._insert(root, "a", ValueRef("left"))
    new_root = tree._follow(new_root_ref)
    left = tree._follow(new_root.left_ref)
    assert new_root.key == "m"
    assert new_root.length == 2
    assert left.key == "a"


def test_binary_tree_insert_duplicate_key_overwrites_value():
    tree = BinaryTree(StubStorage())
    root_ref = tree._insert(None, "k", ValueRef("old"))
    root = tree._follow(root_ref)
    overwritten_ref = tree._insert(root, "k", ValueRef("new"))
    overwritten = tree._follow(overwritten_ref)
    assert overwritten.length == 1
    assert tree._get(overwritten, "k") == "new"


def _build_root(tree, *pairs):
    root = None
    for key, value in pairs:
        root = tree._follow(tree._insert(root, key, ValueRef(value)))
    return root


def test_binary_tree_delete_missing_key_raises_key_error():
    tree = BinaryTree(StubStorage())
    with pytest.raises(KeyError):
        tree._delete(None, "x")


def test_binary_tree_delete_leaf_key():
    tree = BinaryTree(StubStorage())
    root = _build_root(tree, ("b", "2"))
    new_root_ref = tree._delete(root, "b")
    assert tree._follow(new_root_ref) is None


def test_binary_tree_delete_root_promotes_left_child():
    tree = BinaryTree(StubStorage())
    root = _build_root(tree, ("b", "2"), ("a", "1"))
    new_root_ref = tree._delete(root, "b")
    new_root = tree._follow(new_root_ref)
    assert new_root.key == "a"
    assert tree._get(new_root, "a") == "1"
    with pytest.raises(KeyError):
        tree._get(new_root, "b")


def test_binary_tree_delete_root_promotes_right_child():
    tree = BinaryTree(StubStorage())
    root = _build_root(tree, ("b", "2"), ("c", "3"))
    new_root_ref = tree._delete(root, "b")
    new_root = tree._follow(new_root_ref)
    assert new_root.key == "c"
    assert tree._get(new_root, "c") == "3"
    with pytest.raises(KeyError):
        tree._get(new_root, "b")


def test_binary_tree_delete_root_with_two_children_uses_left_max_replacement():
    tree = BinaryTree(StubStorage())
    root = _build_root(tree, ("b", "2"), ("a", "1"), ("c", "3"))
    new_root_ref = tree._delete(root, "b")
    new_root = tree._follow(new_root_ref)
    assert new_root.key == "a"
    assert tree._get(new_root, "a") == "1"
    assert tree._get(new_root, "c") == "3"
    with pytest.raises(KeyError):
        tree._get(new_root, "b")


def test_binary_tree_len_returns_zero_for_empty_tree():
    tree = BinaryTree(StubStorage())
    assert len(tree) == 0


def test_binary_tree_len_tracks_node_count_when_tree_ref_is_dirty_in_locked_session():
    storage = StubStorage()
    tree = BinaryTree(storage)
    storage.locked = True
    root = _build_root(tree, ("b", "2"), ("a", "1"), ("c", "3"))
    tree._tree_ref = BinaryNodeRef(referent=root)
    assert len(tree) == 3
