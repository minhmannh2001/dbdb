# benchmark.py
import os
import random
import string
import time
import dbdb

# --- Configuration ---
DB_PATH = "benchmark.db"
RESULTS_PATH = "BENCHMARK-RESULTS.md"

# Settings for the general performance test
NUM_KEYS_GENERAL = 10_000

# Settings for the compaction impact test
NUM_KEYS_COMPACTION = 1_000
# Each key will be overwritten this many times to create "garbage" data
COMPACTION_OVERWRITES = 10

KEY_SIZE = 16
VALUE_SIZE = 100

# --- Helper Functions ---


def generate_random_string(size: int) -> str:
    """Generates a random string of a given size."""
    return "".join(random.choice(string.ascii_letters) for _ in range(size))


def run_write_benchmark(db: dbdb.DBDB, keys: list[str], values: list[str]) -> float:
    """
    Measures write performance.

    Args:
        db: An active DBDB connection.
        keys: A list of keys to write.
        values: A list of values to write.

    Returns:
        Write operations per second.
    """
    start_time = time.time()
    for key, value in zip(keys, values):
        db[key] = value
        db.commit()  # Commit after each write to simulate CLI/autocommit behavior
    end_time = time.time()
    duration = end_time - start_time
    ops_per_sec = len(keys) / duration
    return ops_per_sec


def run_read_benchmark(db: dbdb.DBDB, keys: list[str]) -> float:
    """
    Measures random read performance.

    Args:
        db: An active DBDB connection.
        keys: A list of keys to read.

    Returns:
        Read operations per second.
    """
    # Shuffle keys to ensure random access pattern
    keys_to_read = list(keys)
    random.shuffle(keys_to_read)
    start_time = time.time()
    for key in keys_to_read:
        _ = db[key]
    end_time = time.time()
    duration = end_time - start_time
    ops_per_sec = len(keys_to_read) / duration
    return ops_per_sec


# --- Test Suites ---


def run_general_performance_test(tree_type: str) -> tuple[float, float]:
    """
    Runs the general performance test for writes and reads on a fresh database.

    Returns:
        A tuple containing (writes_per_sec, reads_per_sec).
    """
    print(
        f"Running general performance test ({tree_type.upper()}) with {NUM_KEYS_GENERAL} keys..."
    )
    keys = [generate_random_string(KEY_SIZE) for _ in range(NUM_KEYS_GENERAL)]
    values = [generate_random_string(VALUE_SIZE) for _ in range(NUM_KEYS_GENERAL)]

    db = dbdb.connect(DB_PATH, tree_type=tree_type)
    try:
        writes_per_sec = run_write_benchmark(db, keys, values)
        reads_per_sec = run_read_benchmark(db, keys)
    finally:
        db.close()

    return writes_per_sec, reads_per_sec


def run_compaction_test(tree_type: str) -> dict:
    """
    Runs a test to measure the impact of compaction on file size and read performance.

    Returns:
        A dictionary containing benchmark results before and after compaction.
    """
    print(
        f"Running compaction test ({tree_type.upper()}) with {NUM_KEYS_COMPACTION} keys, overwritten {COMPACTION_OVERWRITES} times..."
    )
    keys = [generate_random_string(KEY_SIZE) for _ in range(NUM_KEYS_COMPACTION)]

    # 1. Create a "bloated" database by overwriting keys repeatedly
    db = dbdb.connect(DB_PATH, tree_type=tree_type)
    try:
        for i in range(COMPACTION_OVERWRITES):
            print(f"  Overwriting keys: pass {i + 1}/{COMPACTION_OVERWRITES}...")
            values = [
                generate_random_string(VALUE_SIZE) for _ in range(NUM_KEYS_COMPACTION)
            ]
            for key, value in zip(keys, values):
                db[key] = value
            db.commit()

        # 2. Benchmark before compaction
        print("  Benchmarking before compaction...")
        size_before = os.path.getsize(DB_PATH)
        reads_before = run_read_benchmark(db, keys)

        # 3. Run compaction
        print("  Running compaction...")
        start_time = time.time()
        db.compact()
        compaction_time = time.time() - start_time

        # 4. Benchmark after compaction
        print("  Benchmarking after compaction...")
        size_after = os.path.getsize(DB_PATH)
        reads_after = run_read_benchmark(db, keys)
    finally:
        db.close()

    return {
        "size_before": size_before,
        "reads_before": reads_before,
        "size_after": size_after,
        "reads_after": reads_after,
        "compaction_time": compaction_time,
    }


# --- Main Execution ---
if __name__ == "__main__":
    try:
        if os.path.exists(RESULTS_PATH):
            # Add a timestamp to the old results file to avoid overwriting
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            os.rename(RESULTS_PATH, f"BENCHMARK-RESULTS_{timestamp}.md")

        results_general = {}
        results_compaction = {}

        for tree_type in ["bst", "avl"]:
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            writes_per_sec, reads_per_sec = run_general_performance_test(tree_type)
            results_general[tree_type] = {
                "writes": writes_per_sec,
                "reads": reads_per_sec,
            }

            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            compaction_results = run_compaction_test(tree_type)
            results_compaction[tree_type] = compaction_results

        with open(RESULTS_PATH, "w") as f:
            f.write("# DBDB Performance Benchmark Results\n\n")
            f.write(f"Timestamp: `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n\n")

            f.write("## General Performance Comparison\n\n")
            f.write(f"*   **Keys:** `{NUM_KEYS_GENERAL}`\n")
            f.write(f"*   **Key Size:** `{KEY_SIZE}` bytes\n")
            f.write(f"*   **Value Size:** `{VALUE_SIZE}` bytes\n\n")
            f.write(
                "| Operation              | BST Throughput (ops/sec) | AVL Throughput (ops/sec) |\n"
            )
            f.write(
                "|------------------------|--------------------------|--------------------------|\n"
            )
            f.write(
                f"| Sequential Writes      | `{results_general['bst']['writes']:.2f}`                   | `{results_general['avl']['writes']:.2f}`                   |\n"
            )
            f.write(
                f"| Random Reads           | `{results_general['bst']['reads']:.2f}`                   | `{results_general['avl']['reads']:.2f}`                   |\n\n"
            )

            f.write("## Compaction Impact Comparison\n\n")
            f.write(f"*   **Unique Keys:** `{NUM_KEYS_COMPACTION}`\n")
            f.write(f"*   **Overwrites per Key:** `{COMPACTION_OVERWRITES}`\n\n")
            f.write(
                "| Metric                   | BST Before | BST After  | AVL Before | AVL After  |\n"
            )
            f.write(
                "|--------------------------|------------|------------|------------|------------|\n"
            )
            f.write(
                f"| File Size (bytes)        | `{results_compaction['bst']['size_before']}`   | `{results_compaction['bst']['size_after']}`   | `{results_compaction['avl']['size_before']}`   | `{results_compaction['avl']['size_after']}`   |\n"
            )
            f.write(
                f"| Random Read (ops/sec)    | `{results_compaction['bst']['reads_before']:.2f}`    | `{results_compaction['bst']['reads_after']:.2f}`    | `{results_compaction['avl']['reads_before']:.2f}`    | `{results_compaction['avl']['reads_after']:.2f}`    |\n"
            )
            f.write(
                f"| Compaction Time (s)      | N/A        | `{results_compaction['bst']['compaction_time']:.4f}`     | N/A        | `{results_compaction['avl']['compaction_time']:.4f}`     |\n\n"
            )

        print(f"\nBenchmark complete. Results saved to '{RESULTS_PATH}'")

    finally:
        # Ensure the database file is always cleaned up
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print(f"Cleaned up '{DB_PATH}'")
