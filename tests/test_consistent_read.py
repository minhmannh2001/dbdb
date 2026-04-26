import threading
import dbdb

def increment(path):
    db = dbdb.connect(path, tree_type="avl")
    try:
        try:
            val = db["counter"]         # read
        except KeyError:
            val = "0"
        new = str(int(val) + 1)  # compute
        db["counter"] = new             # write
        db.commit()
    finally:
        db.close()

def test_lost_update(tmp_path):
    path = str(tmp_path / "test.db")
    N = 50
    threads = [threading.Thread(target=increment, args=(path,)) for _ in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()

    db = dbdb.connect(path)
    assert db["counter"] == str(N)   # this will FAIL
    db.close()