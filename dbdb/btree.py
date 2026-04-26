"""B-tree nodes and node references."""

from __future__ import annotations

import msgpack
from dataclasses import dataclass
from typing import Any, Optional

from dbdb.logical import LogicalBase, ValueRef
from dbdb.physical import Storage


@dataclass
class BTreeNode:
    """In-memory B-tree node: keys, value refs, child refs, subtree length, leaf flag."""

    keys: list[str]
    value_refs: list[ValueRef]
    child_refs: list[BTreeNodeRef]
    length: int
    is_leaf: bool

    def __post_init__(self) -> None:
        if self.is_leaf:
            if self.child_refs:
                raise ValueError("Leaf node must have empty child_refs")
        else:
            if len(self.child_refs) != len(self.keys) + 1:
                raise ValueError(f"Internal node must have len(child_refs) == len(keys) + 1, got {len(self.child_refs)} != {len(self.keys)} + 1")
        # Note: len(keys) constraint not enforced here, as root may have 0 when empty

    def iter_keys(self, storage):
        """In-order key iterator."""
        if self.is_leaf:
            yield from self.keys
        else:
            for i in range(len(self.keys)):
                child = self.child_refs[i].get(storage)
                yield from child.iter_keys(storage)
                yield self.keys[i]
            # Last child
            child = self.child_refs[-1].get(storage)
            yield from child.iter_keys(storage)

    def iter_items(self, storage):
        """In-order (key, value) iterator."""
        if self.is_leaf:
            for key, value_ref in zip(self.keys, self.value_refs):
                yield key, value_ref.get(storage)
        else:
            for i in range(len(self.keys)):
                child = self.child_refs[i].get(storage)
                yield from child.iter_items(storage)
                yield self.keys[i], self.value_refs[i].get(storage)
            # Last child
            child = self.child_refs[-1].get(storage)
            yield from child.iter_items(storage)


class BTreeNodeRef(ValueRef):
    """Pointer to a BTreeNode; ensures nested refs hit disk before this ref is encoded."""

    @property
    def length(self) -> int:
        """Subtree size from loaded referent; unloaded ref with a disk address raises."""
        if self._referent is None and self._address:
            raise RuntimeError("Asking for BTreeNodeRef length of unloaded node")
        if self._referent:
            return self._referent.length
        return 0

    def prepare_to_store(self, storage: Storage) -> None:
        if self._referent:
            # Store all value refs
            for value_ref in self._referent.value_refs:
                value_ref.store(storage)
            # Store all child refs
            for child_ref in self._referent.child_refs:
                child_ref.store(storage)

    @staticmethod
    def referent_to_bytes(referent: BTreeNode) -> bytes:
        """Pack node into msgpack dict."""
        return msgpack.packb({
            "keys": referent.keys,
            "values": [vr.address for vr in referent.value_refs],
            "children": [cr.address for cr in referent.child_refs],
            "length": referent.length,
            "is_leaf": referent.is_leaf,
        })

    @staticmethod
    def bytes_to_referent(data: bytes) -> BTreeNode:
        """Unpack bytes into BTreeNode."""
        d = msgpack.unpackb(data, raw=False)
        return BTreeNode(
            keys=d["keys"],
            value_refs=[ValueRef(address=addr) for addr in d["values"]],
            child_refs=[BTreeNodeRef(address=addr) for addr in d["children"]],
            length=d["length"],
            is_leaf=d["is_leaf"],
        )


class BTree(LogicalBase):
    """B-tree implementation extending LogicalBase."""

    node_ref_class = BTreeNodeRef
    value_ref_class = ValueRef
    T = 3  # minimum degree

    def _get(self, node, key):
        """Standard B-tree search."""
        if node is None:
            raise KeyError(key)
        # Linear scan for small T
        for i, k in enumerate(node.keys):
            if k == key:
                return self._follow(node.value_refs[i])
            elif k > key:
                if node.is_leaf:
                    raise KeyError(key)
                return self._get(self._follow(node.child_refs[i]), key)
        # Key > all keys, go to last child
        if node.is_leaf:
            raise KeyError(key)
        return self._get(self._follow(node.child_refs[-1]), key)

    def _insert(self, node, key, value_ref):
        """Insert key-value into the tree, returning new root ref."""
        if node is None:
            # Empty tree
            new_node = BTreeNode(
                keys=[key],
                value_refs=[value_ref],
                child_refs=[],
                length=1,
                is_leaf=True
            )
            return BTreeNodeRef(referent=new_node)

        if self._is_full(node):
            # Split root: create new root with old root as child
            new_root = BTreeNode(
                keys=[],
                value_refs=[],
                child_refs=[BTreeNodeRef(referent=node)],
                length=node.length,
                is_leaf=False
            )
            # Split the child
            new_root = self._split_child(new_root, 0)
            # Insert into non-full new root
            return self._insert_non_full(new_root, key, value_ref)
        else:
            return self._insert_non_full(node, key, value_ref)

    def _is_full(self, node):
        """Check if node has maximum keys."""
        return len(node.keys) == 2 * self.T - 1

    def _split_child(self, parent, child_index):
        """Split the child at child_index, promote median to parent."""
        child = parent.child_refs[child_index].get(self._storage)
        median_idx = self.T - 1  # T=3, median_idx=2

        if child.is_leaf:
            # Split leaf
            left_keys = child.keys[:median_idx]
            left_value_refs = child.value_refs[:median_idx]
            left = BTreeNode(left_keys, left_value_refs, [], len(left_keys), True)

            right_keys = child.keys[median_idx + 1:]
            right_value_refs = child.value_refs[median_idx + 1:]
            right = BTreeNode(right_keys, right_value_refs, [], len(right_keys), True)
        else:
            # Split internal
            left_keys = child.keys[:median_idx]
            left_value_refs = child.value_refs[:median_idx]
            left_child_refs = child.child_refs[:median_idx + 1]
            left = BTreeNode(left_keys, left_value_refs, left_child_refs,
                            sum(c.get(self._storage).length for c in left_child_refs) + len(left_keys), False)

            right_keys = child.keys[median_idx + 1:]
            right_value_refs = child.value_refs[median_idx + 1:]
            right_child_refs = child.child_refs[median_idx + 1:]
            right = BTreeNode(right_keys, right_value_refs, right_child_refs,
                             sum(c.get(self._storage).length for c in right_child_refs) + len(right_keys), False)

        # Median key/value
        median_key = child.keys[median_idx]
        median_value_ref = child.value_refs[median_idx]

        # New parent
        new_keys = parent.keys[:child_index] + [median_key] + parent.keys[child_index:]
        new_value_refs = parent.value_refs[:child_index] + [median_value_ref] + parent.value_refs[child_index:]
        new_child_refs = (parent.child_refs[:child_index] +
                         [BTreeNodeRef(referent=left), BTreeNodeRef(referent=right)] +
                         parent.child_refs[child_index + 1:])
        new_parent = BTreeNode(new_keys, new_value_refs, new_child_refs, parent.length, parent.is_leaf)

        return new_parent

    def _insert_non_full(self, node, key, value_ref):
        """Insert into a node that is guaranteed not full."""
        if node.is_leaf:
            # Find insertion point
            i = 0
            while i < len(node.keys) and node.keys[i] < key:
                i += 1
            if i < len(node.keys) and node.keys[i] == key:
                # Update existing
                new_value_refs = node.value_refs[:i] + [value_ref] + node.value_refs[i + 1:]
                new_node = BTreeNode(node.keys, new_value_refs, node.child_refs, node.length, node.is_leaf)
            else:
                # Insert new
                new_keys = node.keys[:i] + [key] + node.keys[i:]
                new_value_refs = node.value_refs[:i] + [value_ref] + node.value_refs[i:]
                new_node = BTreeNode(new_keys, new_value_refs, node.child_refs, node.length + 1, node.is_leaf)
            return BTreeNodeRef(referent=new_node)
        else:
            # Find child index
            i = 0
            while i < len(node.keys) and node.keys[i] < key:
                i += 1
            child_index = i
            child = node.child_refs[child_index].get(self._storage)

            if self._is_full(child):
                # Split child first
                node = self._split_child(node, child_index)
                # Re-find child_index in new node
                i = 0
                while i < len(node.keys) and node.keys[i] < key:
                    i += 1
                child_index = i

            # Now insert into the child
            child = node.child_refs[child_index].get(self._storage)
            new_child_ref = self._insert_non_full(child, key, value_ref)

            # Update node with new child
            new_child_refs = node.child_refs[:child_index] + [new_child_ref] + node.child_refs[child_index + 1:]
            new_length = node.length + 1
            new_node = BTreeNode(node.keys, node.value_refs, new_child_refs, new_length, node.is_leaf)
            return BTreeNodeRef(referent=new_node)

    def __iter__(self):
        """In-order key iteration."""
        if not self._storage.locked:
            self._refresh_tree_ref()
        root = self._follow(self._tree_ref)
        if root:
            return root.iter_keys(self._storage)
        return iter([])

    def items(self):
        """In-order (key, value) iteration."""
        if not self._storage.locked:
            self._refresh_tree_ref()
        root = self._follow(self._tree_ref)
        if root:
            return root.iter_items(self._storage)
        return iter([])