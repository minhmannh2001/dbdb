"""Logical layer: value references and (later) tree / database logic."""


class ValueRef:
    """In-memory value with optional on-disk address (lazy persist later in this phase)."""

    def __init__(self, referent=None, address=0):
        self._referent = referent
        self._address = address

    @property
    def address(self):
        return self._address

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
