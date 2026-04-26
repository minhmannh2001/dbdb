"""Logical layer: value references and (later) tree / database logic."""

from typing import Any, Optional, Type

from dbdb.physical import Storage


class ValueRef:
    """In-memory value with optional on-disk address (lazy persist later in this phase)."""

    def __init__(self, referent: Any = None, address: int = 0):
        self._referent = referent
        self._address = address

    @property
    def address(self) -> int:
        return self._address

    @property
    def length(self) -> int:
        """Used as child ref in `BinaryNode.from_node`; plain values are not subtrees."""
        return 0

    def prepare_to_store(self, storage: Storage) -> None:
        """Hook before persisting; subclasses may validate or mutate state."""
        pass

    @staticmethod
    def referent_to_bytes(referent: Any) -> bytes:
        """UTF-8 encode for `Storage.write` (Python 3: returns ``bytes``)."""
        return referent.encode("utf-8")

    @staticmethod
    def bytes_to_referent(data: bytes) -> Any:
        """UTF-8 decode of a blob read from `Storage.read` (expects ``bytes``)."""
        return data.decode("utf-8")

    def get(self, storage: Storage) -> Any:
        if self._referent is None and self._address:
            self._referent = self.bytes_to_referent(storage.read(self._address))
        return self._referent

    def store(self, storage: Storage) -> None:
        if self._referent is not None and not self._address:
            self.prepare_to_store(storage)
            self._address = storage.write(self.referent_to_bytes(self._referent))


class BytesValueRef(ValueRef):
    """Value reference for raw binary payloads (no UTF-8 text encoding)."""

    def __init__(self, referent: Optional[bytes] = None, address: int = 0):
        if referent is not None and not isinstance(referent, (bytes, bytearray)):
            raise TypeError("BytesValueRef referent must be bytes, bytearray, or None")
        normalized: Optional[bytes] = None if referent is None else bytes(referent)
        super().__init__(referent=normalized, address=address)

    @staticmethod
    def referent_to_bytes(referent: bytes) -> bytes:
        return bytes(referent)

    @staticmethod
    def bytes_to_referent(data: bytes) -> bytes:
        return bytes(data)


class LogicalBase:
    """Minimal base for tree operations; concrete trees provide algorithm hooks."""

    node_ref_class: Optional[Type[ValueRef]] = None
    value_ref_class: Type[ValueRef] = ValueRef

    def __init__(self, storage: Storage):
        self._storage = storage
        self._refresh_tree_ref()

    def _refresh_tree_ref(self) -> None:
        self._tree_ref = self.node_ref_class(address=self._storage.get_root_address())

    def _follow(self, ref: ValueRef) -> Any:
        return ref.get(self._storage)

    def get(self, key: str) -> str:
        if self._tree_ref is None:
            raise KeyError(key)
        return self._get(self._follow(self._tree_ref), key)

    def set(self, key: str, value: str) -> None:
        self._tree_ref = self._insert(
            self._follow(self._tree_ref), key, self.value_ref_class(value)
        )

    def pop(self, key: str) -> None:
        if self._tree_ref is None:
            raise KeyError(key)
        self._tree_ref = self._delete(self._follow(self._tree_ref), key)

    def commit(self) -> None:
        if self._tree_ref:
            self._tree_ref.store(self._storage)
            self._storage.commit_root_address(self._tree_ref.address)
        else:
            self._storage.commit_root_address(0)

    def _get(self, node: Any, key: str) -> str:
        raise NotImplementedError()

    def _insert(self, node: Any, key: str, value_ref: ValueRef) -> ValueRef:
        raise NotImplementedError()

    def _delete(self, node: Any, key: str) -> Optional[ValueRef]:
        raise NotImplementedError()

    def __len__(self) -> int:
        if self._tree_ref is None:
            return 0
        root = self._follow(self._tree_ref)
        if root:
            return root.length
        return 0

    def __iter__(self):
        return iter(self._tree_ref)

    def items(self):
        if self._tree_ref is None:
            return iter([])
        return self._tree_ref.items()
