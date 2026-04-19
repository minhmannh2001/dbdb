"""Binary tree nodes and (later) node references / tree logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
