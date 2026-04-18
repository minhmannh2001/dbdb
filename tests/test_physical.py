import io

from dbdb.physical import Storage


def test_storage_keeps_same_file_handle():
    buf = io.BytesIO()
    storage = Storage(buf)
    assert storage._f is buf
