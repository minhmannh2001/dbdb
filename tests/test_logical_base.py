"""Unit tests for LogicalBase scaffolding used by BinaryTree."""

import pytest

from dbdb.logical import LogicalBase


class _StubStorage:
    def __init__(self, root_address=0):
        self._root_address = root_address

    def get_root_address(self):
        return self._root_address


class _DummyNodeRef:
    def __init__(self, referent=None, address=0):
        self.referent = referent
        self.address = address
        self.seen_storage = None

    def get(self, storage):
        self.seen_storage = storage
        return self.referent


class _DummyTree(LogicalBase):
    node_ref_class = _DummyNodeRef


def test_logical_base_init_refreshes_tree_ref_from_storage_root_address():
    storage = _StubStorage(root_address=1234)
    tree = _DummyTree(storage)
    assert tree._storage is storage
    assert isinstance(tree._tree_ref, _DummyNodeRef)
    assert tree._tree_ref.address == 1234


def test_logical_base_follow_calls_ref_get_with_storage():
    storage = _StubStorage(root_address=99)
    tree = _DummyTree(storage)
    ref = _DummyNodeRef(referent="v")
    assert tree._follow(ref) == "v"
    assert ref.seen_storage is storage


def test_logical_base_algorithm_hooks_raise_until_subclass_implements_them():
    tree = _DummyTree(_StubStorage())
    with pytest.raises(NotImplementedError):
        tree._get(None, "k")
    with pytest.raises(NotImplementedError):
        tree._insert(None, "k", object())
    with pytest.raises(NotImplementedError):
        tree._delete(None, "k")
