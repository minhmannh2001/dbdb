"""Unit tests for LogicalBase scaffolding used by BinaryTree."""

import pytest

from dbdb.logical import LogicalBase


class _StubStorage:
    def __init__(self, root_address=0):
        self._root_address = root_address
        self.locked = False

    def get_root_address(self):
        return self._root_address

    def lock(self):
        if not self.locked:
            self.locked = True
            return True
        return False


class _StubStorageWithCommit(_StubStorage):
    def __init__(self, root_address=0):
        super().__init__(root_address)
        self.committed_root_address = None

    def get_root_address(self):
        # After a commit, this stub should return the committed address
        if self.committed_root_address is not None:
            return self.committed_root_address
        return self._root_address

    def commit_root_address(self, address):
        self.committed_root_address = address


class _DummyNode:
    def __init__(self, address=0, referent=None):
        self.address = address
        self.referent = referent
        self.stored = False  # Track if this node was stored

    def store(self, storage):
        self.stored = True
        if self.address == 0:  # Assign a dummy address if not already set
            self.address = 12345  # Arbitrary dummy address


class _DummyNodeRef:
    def __init__(self, referent=None, address=0):
        self.referent = referent
        self.address = address
        self.seen_storage = None
        self.stored = False  # Track if this ref was stored

    def get(self, storage):
        self.seen_storage = storage
        if self.referent is None and self.address != 0:
            # Simulate loading a node from storage based on its address
            return _DummyNode(address=self.address)
        return self.referent

    def store(self, storage):
        self.seen_storage = storage
        self.stored = True
        if self.referent:  # If there's a referent, store it too
            self.referent.store(storage)
        if self.address == 0:  # Assign a dummy address if not already set
            self.address = 98765  # Arbitrary dummy address


class _DummyTree(LogicalBase):
    node_ref_class = _DummyNodeRef

    def _insert(self, node, key, value_ref):
        self.last_insert = (node, key, value_ref)
        return _DummyNodeRef(referent=_DummyNode(address=777), address=777)


class _DummyTreeWithDelete(LogicalBase):
    node_ref_class = _DummyNodeRef

    def _insert(self, node, key, value_ref):
        self.last_insert = (node, key, value_ref)
        return _DummyNodeRef(referent=_DummyNode(address=777), address=777)

    def _delete(self, node, key):
        self.last_delete = (node, key)
        return _DummyNodeRef(referent=_DummyNode(address=888), address=888)


def test_logical_base_commit_stores_tree_ref_and_commits_root_address():
    storage = _StubStorageWithCommit(root_address=0)  # Use the new stub
    tree = _DummyTreeWithDelete(storage)

    # Simulate some changes to the tree_ref (e.g., via set or pop, but we'll manually set it for this test)
    # The dummy referent needs to be a _DummyNode instance, and it should have its own address
    dummy_node_referent = _DummyNode(address=500)  # Referent inside the ref
    new_root_ref = _DummyNodeRef(
        referent=dummy_node_referent, address=0
    )  # address=0 initially, will be set on store
    tree._tree_ref = new_root_ref

    tree.commit()

    assert new_root_ref.stored is True
    assert new_root_ref.seen_storage is storage
    assert dummy_node_referent.stored is True
    assert storage.committed_root_address == new_root_ref.address
    assert new_root_ref.address != 0  # Ensure a dummy address was assigned


def test_logical_base_refresh_tree_ref_reads_new_root_address_after_commit():
    storage = _StubStorageWithCommit(root_address=0)
    tree = _DummyTreeWithDelete(storage)

    # Simulate initial state where tree is empty (root_address = 0)
    assert tree._tree_ref.address == 0

    # Simulate a change and commit it
    dummy_node_referent = _DummyNode(address=500)
    new_root_ref = _DummyNodeRef(referent=dummy_node_referent, address=0)
    tree._tree_ref = new_root_ref  # Manually set for this test
    tree.commit()

    committed_address = new_root_ref.address
    assert committed_address != 0
    assert storage.get_root_address() == committed_address

    # Simulate a new tree instance (or refresh from storage)
    # The new instance should read the committed root address from storage
    new_tree_instance = _DummyTreeWithDelete(storage)
    assert new_tree_instance._tree_ref.address == committed_address
