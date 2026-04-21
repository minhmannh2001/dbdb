"""Unit tests for BinaryTree scaffolding (Phase 4 starts with StubStorage)."""

from dbdb.binary_tree import BinaryNodeRef, BinaryTree
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
