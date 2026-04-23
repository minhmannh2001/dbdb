"""Logical layer: value references and (later) tree / database logic."""


class ValueRef:
    """In-memory value with optional on-disk address (lazy persist later in this phase)."""

    def __init__(self, referent=None, address=0):
        self._referent = referent
        self._address = address

    @property
    def address(self):
        return self._address

    @property
    def length(self):
        """Used as child ref in `BinaryNode.from_node`; plain values are not subtrees."""
        return 0

    def prepare_to_store(self, storage):
        """Hook before persisting; subclasses may validate or mutate state."""
        pass

    @staticmethod
    def referent_to_bytes(referent):
        """UTF-8 encode for `Storage.write` (Python 3: returns ``bytes``)."""
        return referent.encode("utf-8")

    @staticmethod
    def bytes_to_referent(data):
        """UTF-8 decode of a blob read from `Storage.read` (expects ``bytes``)."""
        return data.decode("utf-8")

    def get(self, storage):
        if self._referent is None and self._address:
            self._referent = self.bytes_to_referent(storage.read(self._address))
        return self._referent

    def store(self, storage):
        if self._referent is not None and not self._address:
            self.prepare_to_store(storage)
            self._address = storage.write(self.referent_to_bytes(self._referent))


class BytesValueRef(ValueRef):
    """Value reference for raw binary payloads (no UTF-8 text encoding)."""

    def __init__(self, referent=None, address=0):
        if referent is not None and not isinstance(referent, (bytes, bytearray)):
            raise TypeError("BytesValueRef referent must be bytes, bytearray, or None")
        normalized = None if referent is None else bytes(referent)
        super().__init__(referent=normalized, address=address)

    @staticmethod
    def referent_to_bytes(referent):
        return bytes(referent)

    @staticmethod
    def bytes_to_referent(data):
        return bytes(data)


class LogicalBase:
    """Minimal base for tree operations; concrete trees provide algorithm hooks."""

    node_ref_class = None
    value_ref_class = ValueRef

    def __init__(self, storage):
        self._storage = storage
        self._refresh_tree_ref()

    def _refresh_tree_ref(self):
        self._tree_ref = self.node_ref_class(address=self._storage.get_root_address())

    def _follow(self, ref):
        return ref.get(self._storage)

    def get(self, key):
        if not self._storage.locked:
            self._refresh_tree_ref()
        return self._get(self._follow(self._tree_ref), key)

    def set(self, key, value):
        if self._storage.lock():
            self._refresh_tree_ref()
        self._tree_ref = self._insert(
            self._follow(self._tree_ref), key, self.value_ref_class(value)
        )

    def pop(self, key):
        if self._storage.lock():
            self._refresh_tree_ref()
        self._tree_ref = self._delete(self._follow(self._tree_ref), key)

    def _get(self, node, key):
        raise NotImplementedError()

    def _insert(self, node, key, value_ref):
        raise NotImplementedError()

    def _delete(self, node, key):
        raise NotImplementedError()

    def __len__(self):
        if not self._storage.locked:
            self._refresh_tree_ref()
        root = self._follow(self._tree_ref)
        if root:
            return root.length
        return 0
