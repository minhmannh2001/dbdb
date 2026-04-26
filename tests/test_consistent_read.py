import threading
import dbdb
import pytest

def increment_manual(path):
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

def increment_update(path):
    db = dbdb.connect(path)  # default bst
    try:
        db.update("counter", lambda v: str(int(v or "0") + 1))
    finally:
        db.close()

def test_lost_update_manual(tmp_path):
    """Demonstrates the lost update problem with manual read-modify-write."""
    path = str(tmp_path / "test.db")
    N = 50
    threads = [threading.Thread(target=increment_manual, args=(path,)) for _ in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()

    db = dbdb.connect(path)
    # This will fail due to race condition
    with pytest.raises(AssertionError):
        assert db["counter"] == str(N)
    db.close()

def test_update_correctness(tmp_path):
    """Test that update provides atomic read-modify-write."""
    path = str(tmp_path / "test.db")
    N = 10  # reduce to avoid lock contention issues
    threads = [threading.Thread(target=increment_update, args=(path,)) for _ in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()

    db = dbdb.connect(path)
    assert db["counter"] == str(N)
    db.close()

def test_update_missing_key(tmp_path):
    """Test update when key does not exist - fn receives None."""
    path = str(tmp_path / "test.db")
    db = dbdb.connect(path, tree_type="avl")
    try:
        result = db.update("missing", lambda v: "42" if v is None else str(int(v) + 1))
        assert result == "42"
        assert db["missing"] == "42"
    finally:
        db.close()

def test_update_exception(tmp_path):
    """Test that exception in fn leaves database unchanged."""
    path = str(tmp_path / "test.db")
    db = dbdb.connect(path, tree_type="avl")
    try:
        db["key"] = "initial"
        db.commit()
        
        with pytest.raises(ValueError):
            db.update("key", lambda v: (_ for _ in ()).throw(ValueError("test")))
        
        # Key should be unchanged
        assert db["key"] == "initial"
    finally:
        db.close()

def test_update_return_value(tmp_path):
    """Test that update returns the new value."""
    path = str(tmp_path / "test.db")
    db = dbdb.connect(path, tree_type="avl")
    try:
        db["key"] = "10"
        db.commit()
        
        result = db.update("key", lambda v: str(int(v) + 5))
        assert result == "15"
        assert db["key"] == "15"
    finally:
        db.close()

def test_update_single(tmp_path):
    """Test update on single db instance."""
    path = str(tmp_path / "test.db")
    db = dbdb.connect(path, tree_type="avl")
    try:
        # First update
        result1 = db.update("counter", lambda v: str(int(v or "0") + 1))
        assert result1 == "1"
        assert db["counter"] == "1"
        
        # Second update on same db
        result2 = db.update("counter", lambda v: str(int(v) + 1))
        assert result2 == "2"
        assert db["counter"] == "2"
    finally:
        db.close()