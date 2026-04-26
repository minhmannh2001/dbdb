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

    def _delete(self, node, key):
        """Delete key from tree, returning new root ref or None."""
        if node is None:
            raise KeyError(key)

        # Find position
        i = 0
        while i < len(node.keys) and node.keys[i] < key:
            i += 1

        if node.is_leaf:
            if i < len(node.keys) and node.keys[i] == key:
                # Remove from leaf
                new_keys = node.keys[:i] + node.keys[i+1:]
                new_value_refs = node.value_refs[:i] + node.value_refs[i+1:]
                if not new_keys:
                    return None  # Empty tree
                new_node = BTreeNode(new_keys, new_value_refs, node.child_refs, node.length - 1, node.is_leaf)
                return BTreeNodeRef(referent=new_node)
            else:
                raise KeyError(key)
        else:
            # Internal node
            if i < len(node.keys) and node.keys[i] == key:
                # Key is in this node, replace with predecessor or successor
                return self._delete_internal_key(node, i)
            else:
                # Key is in child subtree
                child_index = i
                # Ensure child has at least t keys
                node, child_index = self._ensure_min_keys(node, child_index)
                # Recurse
                child = node.child_refs[child_index].get(self._storage)
                new_child_ref = self._delete(child, key)
                # Update node
                new_child_refs = node.child_refs[:child_index] + [new_child_ref] + node.child_refs[child_index+1:]
                new_length = node.length - 1
                new_node = BTreeNode(node.keys, node.value_refs, new_child_refs, new_length, node.is_leaf)
                # Check if root needs to shrink
                if len(new_node.keys) == 0:
                    if len(new_node.child_refs) == 0:
                        return None
                    elif len(new_node.child_refs) == 1:
                        return new_node.child_refs[0]
                return BTreeNodeRef(referent=new_node)

    def _delete_internal_key(self, node, key_index):
        """Delete key at key_index in internal node."""
        left_child = node.child_refs[key_index].get(self._storage)
        right_child = node.child_refs[key_index + 1].get(self._storage)

        if len(left_child.keys) >= self.T:
            # Use predecessor
            pred_key, pred_value_ref = self._get_predecessor(left_child)
            new_keys = node.keys[:key_index] + [pred_key] + node.keys[key_index+1:]
            new_value_refs = node.value_refs[:key_index] + [pred_value_ref] + node.value_refs[key_index+1:]
            # Delete predecessor from left child
            new_left_ref = self._delete(left_child, pred_key)
            new_child_refs = node.child_refs[:key_index] + [new_left_ref] + node.child_refs[key_index+1:]
        elif len(right_child.keys) >= self.T:
            # Use successor
            succ_key, succ_value_ref = self._get_successor(right_child)
            new_keys = node.keys[:key_index] + [succ_key] + node.keys[key_index+1:]
            new_value_refs = node.value_refs[:key_index] + [succ_value_ref] + node.value_refs[key_index+1:]
            # Delete successor from right child
            new_right_ref = self._delete(right_child, succ_key)
            new_child_refs = node.child_refs[:key_index] + [node.child_refs[key_index], new_right_ref] + node.child_refs[key_index+2:]
        else:
            # Merge children
            merged = self._merge_children(left_child, node.keys[key_index], node.value_refs[key_index], right_child)
            new_keys = node.keys[:key_index] + node.keys[key_index+1:]
            new_value_refs = node.value_refs[:key_index] + node.value_refs[key_index+1:]
            new_child_refs = node.child_refs[:key_index] + [BTreeNodeRef(referent=merged)] + node.child_refs[key_index+2:]
            # Now delete the key from merged
            new_merged_ref = self._delete(merged, node.keys[key_index])
            new_child_refs = node.child_refs[:key_index] + [new_merged_ref] + node.child_refs[key_index+2:]

        new_length = node.length - 1
        new_node = BTreeNode(new_keys, new_value_refs, new_child_refs, new_length, node.is_leaf)
        if len(new_node.keys) == 0 and len(new_node.child_refs) == 1:
            return new_node.child_refs[0]
        return BTreeNodeRef(referent=new_node)

    def _get_predecessor(self, node):
        """Get rightmost key/value from subtree."""
        if node.is_leaf:
            return node.keys[-1], node.value_refs[-1]
        child = node.child_refs[-1].get(self._storage)
        return self._get_predecessor(child)

    def _get_successor(self, node):
        """Get leftmost key/value from subtree."""
        if node.is_leaf:
            return node.keys[0], node.value_refs[0]
        child = node.child_refs[0].get(self._storage)
        return self._get_successor(child)

    def _merge_children(self, left, separator_key, separator_value_ref, right):
        """Merge two children with separator."""
        if left.is_leaf:
            new_keys = left.keys + [separator_key] + right.keys
            new_value_refs = left.value_refs + [separator_value_ref] + right.value_refs
            new_child_refs = []
        else:
            new_keys = left.keys + [separator_key] + right.keys
            new_value_refs = left.value_refs + [separator_value_ref] + right.value_refs
            new_child_refs = left.child_refs + right.child_refs
        return BTreeNode(new_keys, new_value_refs, new_child_refs, left.length + right.length + 1, left.is_leaf)

    def _ensure_min_keys(self, parent, child_index):
        """Ensure child has at least t keys, borrowing or merging if needed."""
        child = parent.child_refs[child_index].get(self._storage)
        if len(child.keys) >= self.T:
            return parent, child_index

        # Try borrow from left sibling
        if child_index > 0:
            left_sibling = parent.child_refs[child_index - 1].get(self._storage)
            if len(left_sibling.keys) >= self.T:
                new_parent = self._borrow_from_left(parent, child_index)
                return new_parent, child_index

        # Try borrow from right sibling
        if child_index < len(parent.child_refs) - 1:
            right_sibling = parent.child_refs[child_index + 1].get(self._storage)
            if len(right_sibling.keys) >= self.T:
                new_parent = self._borrow_from_right(parent, child_index)
                return new_parent, child_index

        # Merge with left sibling
        if child_index > 0:
            new_parent = self._merge_with_left(parent, child_index)
            return new_parent, child_index - 1
        else:
            new_parent = self._merge_with_right(parent, child_index)
            return new_parent, child_index

    def _borrow_from_left(self, parent, child_index):
        """Borrow from left sibling."""
        left_sibling = parent.child_refs[child_index - 1].get(self._storage)
        child = parent.child_refs[child_index].get(self._storage)

        # Rotate: parent key down to child, left sibling's last key up to parent
        down_key = parent.keys[child_index - 1]
        down_value_ref = parent.value_refs[child_index - 1]
        up_key = left_sibling.keys[-1]
        up_value_ref = left_sibling.value_refs[-1]

        new_parent_keys = parent.keys[:child_index - 1] + [up_key] + parent.keys[child_index:]
        new_parent_value_refs = parent.value_refs[:child_index - 1] + [up_value_ref] + parent.value_refs[child_index:]

        if not left_sibling.is_leaf:
            # Move last child ref from left to front of child
            move_ref = left_sibling.child_refs[-1]
            new_child_keys = [down_key] + child.keys
            new_child_value_refs = [down_value_ref] + child.value_refs
            new_child_refs = [move_ref] + child.child_refs
            new_left_keys = left_sibling.keys[:-1]
            new_left_value_refs = left_sibling.value_refs[:-1]
            new_left_refs = left_sibling.child_refs[:-1]
        else:
            new_child_keys = [down_key] + child.keys
            new_child_value_refs = [down_value_ref] + child.value_refs
            new_child_refs = child.child_refs
            new_left_keys = left_sibling.keys[:-1]
            new_left_value_refs = left_sibling.value_refs[:-1]
            new_left_refs = left_sibling.child_refs

        new_left = BTreeNode(new_left_keys, new_left_value_refs, new_left_refs, left_sibling.length - 1, left_sibling.is_leaf)
        new_child = BTreeNode(new_child_keys, new_child_value_refs, new_child_refs, child.length + 1, child.is_leaf)
        new_child_refs_list = parent.child_refs[:child_index - 1] + [BTreeNodeRef(referent=new_left), BTreeNodeRef(referent=new_child)] + parent.child_refs[child_index + 1:]
        new_parent = BTreeNode(new_parent_keys, new_parent_value_refs, new_child_refs_list, parent.length, parent.is_leaf)
        return new_parent

    def _borrow_from_right(self, parent, child_index):
        """Borrow from right sibling."""
        right_sibling = parent.child_refs[child_index + 1].get(self._storage)
        child = parent.child_refs[child_index].get(self._storage)

        down_key = parent.keys[child_index]
        down_value_ref = parent.value_refs[child_index]
        up_key = right_sibling.keys[0]
        up_value_ref = right_sibling.value_refs[0]

        new_parent_keys = parent.keys[:child_index] + [up_key] + parent.keys[child_index + 1:]
        new_parent_value_refs = parent.value_refs[:child_index] + [up_value_ref] + parent.value_refs[child_index + 1:]

        if not right_sibling.is_leaf:
            move_ref = right_sibling.child_refs[0]
            new_child_keys = child.keys + [down_key]
            new_child_value_refs = child.value_refs + [down_value_ref]
            new_child_refs = child.child_refs + [move_ref]
            new_right_keys = right_sibling.keys[1:]
            new_right_value_refs = right_sibling.value_refs[1:]
            new_right_refs = right_sibling.child_refs[1:]
        else:
            new_child_keys = child.keys + [down_key]
            new_child_value_refs = child.value_refs + [down_value_ref]
            new_child_refs = child.child_refs
            new_right_keys = right_sibling.keys[1:]
            new_right_value_refs = right_sibling.value_refs[1:]
            new_right_refs = right_sibling.child_refs

        new_right = BTreeNode(new_right_keys, new_right_value_refs, new_right_refs, right_sibling.length - 1, right_sibling.is_leaf)
        new_child = BTreeNode(new_child_keys, new_child_value_refs, new_child_refs, child.length + 1, child.is_leaf)
        new_child_refs_list = parent.child_refs[:child_index] + [BTreeNodeRef(referent=new_child), BTreeNodeRef(referent=new_right)] + parent.child_refs[child_index + 2:]
        new_parent = BTreeNode(new_parent_keys, new_parent_value_refs, new_child_refs_list, parent.length, parent.is_leaf)
        return new_parent

    def _merge_with_left(self, parent, child_index):
        """Merge child with left sibling."""
        left_sibling = parent.child_refs[child_index - 1].get(self._storage)
        child = parent.child_refs[child_index].get(self._storage)
        separator_key = parent.keys[child_index - 1]
        separator_value_ref = parent.value_refs[child_index - 1]

        merged = self._merge_children(left_sibling, separator_key, separator_value_ref, child)
        new_parent_keys = parent.keys[:child_index - 1] + parent.keys[child_index:]
        new_parent_value_refs = parent.value_refs[:child_index - 1] + parent.value_refs[child_index:]
        new_child_refs = parent.child_refs[:child_index - 1] + [BTreeNodeRef(referent=merged)] + parent.child_refs[child_index + 1:]
        new_parent = BTreeNode(new_parent_keys, new_parent_value_refs, new_child_refs, parent.length - 1, parent.is_leaf)
        return new_parent

    def _merge_with_right(self, parent, child_index):
        """Merge child with right sibling (for when child_index == 0)."""
        child = parent.child_refs[child_index].get(self._storage)
        right_sibling = parent.child_refs[child_index + 1].get(self._storage)
        separator_key = parent.keys[child_index]
        separator_value_ref = parent.value_refs[child_index]

        merged = self._merge_children(child, separator_key, separator_value_ref, right_sibling)
        new_parent_keys = parent.keys[:child_index] + parent.keys[child_index + 1:]
        new_parent_value_refs = parent.value_refs[:child_index] + parent.value_refs[child_index + 1:]
        new_child_refs = parent.child_refs[:child_index] + [BTreeNodeRef(referent=merged)] + parent.child_refs[child_index + 2:]
        new_parent = BTreeNode(new_parent_keys, new_parent_value_refs, new_child_refs, parent.length - 1, parent.is_leaf)
        return new_parent

    def __iter__(self):
        """In-order key iteration."""
        if not self._storage.locked:
            self._refresh_tree_ref()
        if self._tree_ref is None:
            return iter([])
        root = self._follow(self._tree_ref)
        if root:
            return root.iter_keys(self._storage)
        return iter([])

    def items(self):
        """In-order (key, value) iteration."""
        if not self._storage.locked:
            self._refresh_tree_ref()
        if self._tree_ref is None:
            return iter([])
        root = self._follow(self._tree_ref)
        if root:
            return root.iter_items(self._storage)
        return iter([])