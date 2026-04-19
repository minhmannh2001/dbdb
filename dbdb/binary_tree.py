"""Binary tree nodes and (later) node references / tree logic."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from typing import Any

from dbdb.logical import ValueRef


@dataclass
class BinaryNode:
    """In-memory BST node: child refs, key, value ref, and subtree size."""

    left_ref: Any
    key: Any
    value_ref: Any
    right_ref: Any
    length: int

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
        )

    def store_refs(self, storage) -> None:
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

    def prepare_to_store(self, storage) -> None:
        if self._referent:
            self._referent.store_refs(storage)

    @staticmethod
    def referent_to_bytes(referent: BinaryNode) -> bytes:
        """Pickle a small dict of addresses and metadata (no nested Python objects)."""
        return pickle.dumps(
            {
                "left": referent.left_ref.address,
                "key": referent.key,
                "value": referent.value_ref.address,
                "right": referent.right_ref.address,
                "length": referent.length,
            }
        )

    @staticmethod
    def bytes_to_referent(data: bytes) -> BinaryNode:
        d = pickle.loads(data)
        return BinaryNode(
            BinaryNodeRef(address=d["left"]),
            d["key"],
            ValueRef(address=d["value"]),
            BinaryNodeRef(address=d["right"]),
            d["length"],
        )
