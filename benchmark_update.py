#!/usr/bin/env python3
"""Benchmark: pessimistic update() vs optimistic update_optimistic().

Two workloads:
  write-heavy  all N threads increment the same counter key simultaneously
  mixed        N/2 writers increment the counter, N/2 readers scan other keys

Measures wall-clock time, final counter value (correctness), and retry count.
"""

import os
import tempfile
import threading
import time

import dbdb

# ---------------------------------------------------------------------------
# Thread-safe retry accumulator
# ---------------------------------------------------------------------------

_retry_total = 0
_failed_total = 0
_retry_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Worker functions
# ---------------------------------------------------------------------------


def _pessimistic_writer(path: str) -> None:
    db = dbdb.connect(path)
    try:
        db.update("counter", lambda v: str(int(v or "0") + 1))
    finally:
        db.close()


def _optimistic_writer(path: str, max_retries: int = 100) -> None:
    calls = [0]

    def fn(v):
        calls[0] += 1
        return str(int(v or "0") + 1)

    db = dbdb.connect(path)
    succeeded = True
    try:
        db.update_optimistic("counter", fn, max_retries=max_retries)
    except RuntimeError:
        succeeded = False
    finally:
        db.close()

    with _retry_lock:
        global _retry_total, _failed_total
        _retry_total += calls[0] - 1  # first call is not a retry
        if not succeeded:
            _failed_total += 1


def _reader(path: str) -> None:
    db = dbdb.connect(path)
    try:
        for i in range(50):
            try:
                _ = db[f"padding_{i}"]
            except KeyError:
                pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Single benchmark run
# ---------------------------------------------------------------------------


def _run_once(strategy: str, workload: str, n: int) -> dict:
    global _retry_total, _failed_total
    _retry_total = 0
    _failed_total = 0

    n_writers = n if workload == "write-heavy" else n // 2
    n_readers = 0 if workload == "write-heavy" else n // 2

    writer_fn = _pessimistic_writer if strategy == "pessimistic" else _optimistic_writer

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "bench.db")

        threads = (
            [threading.Thread(target=writer_fn, args=(path,)) for _ in range(n_writers)]
            + [threading.Thread(target=_reader, args=(path,)) for _ in range(n_readers)]
        )

        t0 = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.perf_counter() - t0

        db = dbdb.connect(path)
        try:
            counter = int(db["counter"] or "0")
        except KeyError:
            counter = 0
        finally:
            db.close()

    return {
        "elapsed": elapsed,
        "counter": counter,
        "expected": n_writers,
        "correct": counter == n_writers - _failed_total,
        "retries": _retry_total if strategy == "optimistic" else None,
        "failed": _failed_total if strategy == "optimistic" else None,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

N = 30        # concurrent writers per run
RUNS = 5      # averaged runs per config


def main() -> None:
    configs = [
        ("pessimistic", "write-heavy"),
        ("optimistic",  "write-heavy"),
        ("pessimistic", "mixed"),
        ("optimistic",  "mixed"),
    ]

    print(f"N={N} writers, {RUNS} runs each (mixed: N/2 writers + N/2 readers)\n")
    print(f"{'Strategy':<14} {'Workload':<12} {'Avg time':>9}  {'Correct':>8}  {'Avg retries':>12}  {'Avg failed':>10}")
    print("-" * 75)

    raw_results = {}

    for strategy, workload in configs:
        times, retries_all, failed_all = [], [], []
        last_correct = True
        for _ in range(RUNS):
            r = _run_once(strategy, workload, N)
            times.append(r["elapsed"])
            if r["retries"] is not None:
                retries_all.append(r["retries"])
            if r["failed"] is not None:
                failed_all.append(r["failed"])
            if not r["correct"]:
                last_correct = False

        avg_time = sum(times) / len(times)
        avg_retries = (sum(retries_all) / len(retries_all)) if retries_all else None
        avg_failed = (sum(failed_all) / len(failed_all)) if failed_all else None
        retries_str = f"{avg_retries:.1f}" if avg_retries is not None else "-"
        failed_str = f"{avg_failed:.1f}" if avg_failed is not None else "-"
        correct_str = "✓" if last_correct else "✗"

        print(
            f"{strategy:<14} {workload:<12} {avg_time:>8.3f}s  {correct_str:>8}  {retries_str:>12}  {failed_str:>10}"
        )
        raw_results[(strategy, workload)] = {
            "avg_time": avg_time,
            "avg_retries": avg_retries,
            "avg_failed": avg_failed,
            "correct": last_correct,
        }

    print()

    # Summary decision
    ph = raw_results[("pessimistic", "write-heavy")]["avg_time"]
    oh = raw_results[("optimistic",  "write-heavy")]["avg_time"]
    pm = raw_results[("pessimistic", "mixed")]["avg_time"]
    om = raw_results[("optimistic",  "mixed")]["avg_time"]
    or_ = raw_results[("optimistic", "write-heavy")]["avg_retries"] or 0.0

    print("Summary")
    print(f"  Write-heavy: pessimistic {ph:.3f}s vs optimistic {oh:.3f}s "
          f"({abs(ph - oh) / ph * 100:.0f}% {'slower' if oh > ph else 'faster'} optimistic, "
          f"avg {or_:.1f} retries/writer)")
    print(f"  Mixed:       pessimistic {pm:.3f}s vs optimistic {om:.3f}s "
          f"({abs(pm - om) / pm * 100:.0f}% {'slower' if om > pm else 'faster'} optimistic)")


if __name__ == "__main__":
    main()
