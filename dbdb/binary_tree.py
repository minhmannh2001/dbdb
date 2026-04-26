"""Binary tree nodes and (later) node references / tree logic."""

from __future__ import annotations

import msgpack
import pickle
from dataclasses import dataclass
from typing import Any, Optional

from dbdb.logical import LogicalBase, ValueRef
from dbdb.physical import Storage


@dataclass
class BinaryNode:
    """In-memory BST node: child refs, key, value ref, and subtree size."""

    left_ref: BinaryNodeRef
    key: str
    value_ref: ValueRef
    right_ref: BinaryNodeRef
    length: int
    height: int

    @classmethod
    def from_node(cls, node: BinaryNode, **kwargs: Any) -> BinaryNode:
        """Copy node with optional field overrides; subtree `length` tracks child ref sizes."""
        length = node.length
        if "left_ref" in kwargs:
            length += kwargs["left_ref"].length - node.left_ref.length
        if "right_ref" in kwargs:
            length += kwargs["right_ref"].length - node.right_ref.length
        return cls(
            left_ref=kwargs.get("left_ref", node.left_ref),
            key=kwargs.get("key", node.key),
            value_ref=kwargs.get("value_ref", node.value_ref),
            right_ref=kwargs.get("right_ref", node.right_ref),
            length=length,
            height=kwargs.get("height", node.height),
        )

    def store_refs(self, storage: Storage) -> None:
        """Persist value ref then child refs (same order as reference `store_refs`)."""
        self.value_ref.store(storage)
        self.left_ref.store(storage)
        self.right_ref.store(storage)


class BinaryNodeRef(ValueRef):
    """Pointer to a `BinaryNode`; ensures nested refs hit disk before this ref is encoded."""

    @property
    def length(self) -> int:
        """Subtree size from loaded referent; unloaded ref with a disk address is undefined."""
        if self._referent is None and self._address:
            raise RuntimeError("Asking for BinaryNodeRef length of unloaded node")
        if self._referent:
            return self._referent.length
        return 0

    def prepare_to_store(self, storage: Storage) -> None:
        if self._referent:
            self._referent.store_refs(storage)

    @staticmethod
    def referent_to_bytes(referent: BinaryNode) -> bytes:
        """Pack a dict of addresses and metadata into bytes."""
        return msgpack.packb(
            {
                "left": referent.left_ref.address,
                "key": referent.key,
                "value": referent.value_ref.address,
                "right": referent.right_ref.address,
                "length": referent.length,
                "height": referent.height,
            }
        )

    @staticmethod
    def bytes_to_referent(data: bytes) -> BinaryNode:
        """Unpack bytes into a `BinaryNode`."""
        d = msgpack.unpackb(data, raw=False)
        return BinaryNode(
            BinaryNodeRef(address=d["left"]),
            d["key"],
            ValueRef(address=d["value"]),
            BinaryNodeRef(address=d["right"]),
            d["length"],
            d["height"],
        )


class BinaryTree(LogicalBase):
    """Tree shell wired to logical base; traversal/mutation hooks come next."""

    node_ref_class = BinaryNodeRef
    value_ref_class = ValueRef

    def _get(self, node: Optional[BinaryNode], key: str) -> str:
        while node is not None:
            if key < node.key:
                node = self._follow(node.left_ref)
            elif node.key < key:
                node = self._follow(node.right_ref)
            else:
                return self._follow(node.value_ref)
        raise KeyError

    def _insert(
        self, node: Optional[BinaryNode], key: str, value_ref: ValueRef
    ) -> BinaryNodeRef:
        if node is None:
            new_node = BinaryNode(
                self.node_ref_class(),
                key,
                value_ref,
                self.node_ref_class(),
                1,
                0,
            )
        elif key < node.key:
            new_node = BinaryNode.from_node(
                node,
                left_ref=self._insert(self._follow(node.left_ref), key, value_ref),
            )
        elif node.key < key:
            new_node = BinaryNode.from_node(
                node,
                right_ref=self._insert(self._follow(node.right_ref), key, value_ref),
            )
        else:
            new_node = BinaryNode.from_node(node, value_ref=value_ref)
        return self.node_ref_class(referent=new_node)

    def _delete(self, node: Optional[BinaryNode], key: str) -> Optional[BinaryNodeRef]:
        if node is None:
            raise KeyError
        elif key < node.key:
            new_node = BinaryNode.from_node(
                node,
                left_ref=self._delete(self._follow(node.left_ref), key),
            )
        elif node.key < key:
            new_node = BinaryNode.from_node(
                node,
                right_ref=self._delete(self._follow(node.right_ref), key),
            )
        else:
            left = self._follow(node.left_ref)
            right = self._follow(node.right_ref)
            if left and right:
                replacement = self._find_max(left)
                left_ref = self._delete(self._follow(node.left_ref), replacement.key)
                # Use from_node to correctly recalculate length
                new_node = BinaryNode.from_node(
                    node,
                    key=replacement.key,
                    value_ref=replacement.value_ref,
                    left_ref=left_ref,
                )
            elif left:
                return node.left_ref
            else:
                return node.right_ref
        return self.node_ref_class(referent=new_node)

    def _find_max(self, node: BinaryNode) -> BinaryNode:
        while True:
            next_node = self._follow(node.right_ref)
            if next_node is None:
                return node
            node = next_node

    def _iter_nodes(self, node: Optional[BinaryNode]):
        if node:
            yield from self._iter_nodes(self._follow(node.left_ref))
            yield node
            yield from self._iter_nodes(self._follow(node.right_ref))

    def _iter_items(self, node: Optional[BinaryNode]):
        if node:
            yield from self._iter_items(self._follow(node.left_ref))
            yield (node.key, self._follow(node.value_ref))
            yield from self._iter_items(self._follow(node.right_ref))

    def __iter__(self):
        root = self._follow(self._tree_ref)
        for node in self._iter_nodes(root):
            yield node.key

    def items(self):
        root = self._follow(self._tree_ref)
        yield from self._iter_items(root)
