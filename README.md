# DBDB — Dog Bed Database

A from-scratch rebuild of [DBDB](https://aosabook.org/en/500L/dbdb-dog-bed-database.html)
from *500 Lines or Less*, extended with compaction, concurrent-access safety, and a CLI tool.

DBDB is a persistent key-value store backed by an append-only binary file and an
immutable binary search tree. It fits in 665 lines of source code.

## Architecture

```
physical.py     bytes ↔ disk addresses     (append-only file, superblock, locking)
logical.py      addresses ↔ values         (ValueRef, LogicalBase, lazy loading)
binary_tree.py  values ↔ keys              (immutable BST nodes, msgpack serialization)
interface.py    keys ↔ dict syntax         (DBDB class, compaction, auto-reopen)
__init__.py     dict syntax ↔ file path    (connect() entry point)
tool.py         file path ↔ shell command  (CLI: get / set / delete)
```

Each layer knows exactly one thing about the layer below it.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
```

Or with Make:

```bash
make install
```

## Usage

**Python API**

```python
import dbdb

db = dbdb.connect("mydb.db")
db["city"] = "Hanoi"
db["lang"] = "Python"
db.commit()

print(db["city"])    # "Hanoi"
print(len(db))       # 2
print("lang" in db)  # True

db.compact()         # reclaim space from overwritten/deleted keys
db.close()
```

**CLI**

```bash
python -m dbdb.tool mydb.db set city Hanoi
python -m dbdb.tool mydb.db get city
python -m dbdb.tool mydb.db delete city
```

## Tests

```bash
pytest        # runs all 143 unit tests + BDD scenarios
make test     # same
```

Tests are split between plain pytest (`tests/test_*.py`) and
pytest-bdd scenarios (`features/*.feature` + `tests/step_defs/`).

## Blog

This project was built over a series of 12 posts. The `DEVLOG.md` file contains the raw notes and Q&A sessions used to write them.

| Part | Title |
|------|-------|
| 0 | [Project Setup](https://minhmannh2001.github.io/2026/04/21/build-dbdb-from-scratch-part-0-project-setup-en.html) |
| 1 | [Append-Only Storage](https://minhmannh2001.github.io/2026/04/22/build-dbdb-from-scratch-part-1-append-only-storage-en.html) |
| 2 | [ValueRef & Lazy Loading](https://minhmannh2001.github.io/2026/04/23/build-dbdb-from-scratch-part-2-valueref-en.html) |
| 3 | [Immutable Tree & `BinaryNodeRef`](https://minhmannh2001.github.io/2026/04/24/build-dbdb-from-scratch-part-3-binarynode-en.html) |
| 4 | [The Logical Layer](https://minhmannh2001.github.io/2026/04/25/build-dbdb-from-scratch-part-4-logical-layer-en.html) |
| 5 | [End-to-End Trace](https://minhmannh2001.github.io/2026/04/26/build-dbdb-from-scratch-part-5-how-it-all-fits-en.html) |
| 6 | [Locking Across Layers](https://minhmannh2001.github.io/2026/04/27/build-dbdb-from-scratch-part-6-locking-across-layers-en.html) |
| 7 | [The Commit](https://minhmannh2001.github.io/2026/04/28/build-dbdb-from-scratch-part-7-commit-en.html) |
| 8 | [An Interface Facade](https://minhmannh2001.github.io/2026/04/29/build-dbdb-from-scratch-part-8-interface-en.html) |
| 9 | [The CLI](https://minhmannh2001.github.io/2026/04/30/build-dbdb-from-scratch-part-9-cli-en.html) |
| 10 | [Compaction](https://minhmannh2001.github.io/2026/05/01/build-dbdb-from-scratch-part-10-compaction-en.html) |
| 11 | [Retrospective](https://minhmannh2001.github.io/2026/05/02/build-dbdb-from-scratch-part-11-retrospective-en.html) |

## Known Limitations

- **Tree does not rebalance.** Compaction inserts keys in sorted order, producing a skewed BST with O(n) lookup. A B-tree would fix this.
- **Compaction is blocking.** `compact()` holds the write lock for its full duration. No background compaction.
- **No serialization versioning.** The msgpack format has no version field; format changes are breaking.
- **No snapshot isolation across reads.** A reader may see different tree states across two `get()` calls if a writer commits in between.
- **Read-modify-write is not atomic.** Concurrent processes doing `get` → compute → `set` can produce lost updates. The lock only prevents concurrent writes, not the read-modify-write race.
