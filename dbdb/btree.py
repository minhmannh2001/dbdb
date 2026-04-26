"""B-tree nodes and node references."""

from __future__ import annotations

import msgpack
from dataclasses import dataclass
from typing import Any, Optional

from dbdb.logical import ValueRef
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