
# Simple Persistent Key-Value Store

A simple persistent key-value store written in Python. It behaves like a `dict`, but also saves its contents to disk, so data survives program termination. The design is based on log-structured storage with an in-memory hash table index.

- [User Documentation](#user-documentation)
- [Programmer Documentation](#programmer-documentation)

---

# User Documentation

## What the program does

The program implements a simple persistent key-value store. It behaves much like a Python dictionary (`dict`), but unlike one, it also stores its contents on disk, so the data survives program termination. On the next start, the store is automatically restored to the state in which it was last saved.

The program is not a standalone application with standard input and output. It is a library (the `Database` class) that you import and whose methods you call directly in your code:

```python
from database import Database

db = Database("data.db")
db.set("name", "Martin")
print(db.get("name"))  # "Martin"
db.delete("name")
db.close()
```

Using the `with` statement is recommended, as it guarantees the file is closed properly even if an exception occurs:

```python
with Database("data.db") as db:
    db.set("age", "20")
```

## Input and output

The input consists of key-value string pairs passed to the `set`, `get`, `delete` and `contains` methods. The output consists of the return values of these methods and a file on disk (the path given when creating the `Database`) to which changes are written.

## Things you might not expect

- **Keys and values must be strings (`str`).** Any other type raises `TypeError`. Additionally, the key must not be an empty string, which raises `ValueError`. An empty value (`""`) is allowed.
- **The value must not contain a newline character.** The data file is line-oriented (one record = one line), so storing such a value would break the file format and the record could not be parsed correctly on the next load.
- **The data file keeps growing while the program runs**, even when the same key is overwritten repeatedly or deleted. Every call to `set` or `delete` merely appends a new record to the end of the file (see the file format section below); old records are not removed on the fly. The file is only actually shrunk (obsolete and deleted records removed) when `close()` is called (or when the `with` block ends).
- **If the program terminates unexpectedly** (crashes or is killed) without calling `close()`, no data is lost: on the next start the store is reconstructed by replaying the whole file. However, the file remains uncompacted (larger than it needs to be).
- **`get()` on a nonexistent key does not raise an exception**; it returns `None`.
- **`delete()` returns `True`/`False`** depending on whether the key existed in the store, not the value.
- **Concurrent access is not handled.** If two running programs write to the same file at the same time, the data may become corrupted.

## Data file format

The data file is a human-readable text file in which each record has one of the following forms:

```
PUT <key_length> <key> <value>
DEL <key_length> <key>
```

Editing the file by hand is not recommended. If a line that does not match this format appears in it (or if the stated key length does not match the actual one), the program silently skips that line when loading.

---

# Programmer Documentation

## Overall concept

The project consists of two main parts:

- **`HashTable`**: a general-purpose hash table data structure that holds data in memory and serves as an index over the data on disk.
- **`Database`**: a layer on top of `HashTable` that provides persistence. Every change (`set`, `delete`) is first written to a file and only then reflected in the in-memory index.

The design follows the principle of **log-structured storage**: all writes are append-only (added only to the end of the file), and nothing is ever written into the middle of the file. This makes writes fast (they are just an append to the end of the file) and resilient to program crashes: the log contains the complete history of operations, from which the state can be reconstructed at any time by replaying it from the beginning (the `load` method).

## Record serialization

The functions `encode_put` and `encode_delete` convert an operation into a text line, and `decode_line` does the reverse. The length of the key in characters is stored before the key itself (`PUT <len> <key> <value>`). Because of this, a key may contain spaces without being confused with the separator: the parser knows exactly how many characters after the length field belong to the key, and takes the rest of the line (after one space) as the value.

The value, on the other hand, has no stored length, because it is read "to the end of the line". This is also why the value must not contain a newline character.

Invalid lines (corrupted, not following the format, or with an incorrect key length) are evaluated by `decode_line` as `None` and skipped by `load`. This makes the program robust even against a partially corrupted file.

## Loading and compaction

The `load` method is called in the `Database` constructor and sequentially replays the whole file: for every `PUT` it inserts the pair into the `HashTable`, and for every `DEL` it removes it. The resulting state of the index therefore corresponds to the latest valid value for each key.

The `compact` method (called on `close`) writes the current contents of the in-memory index (that is, only valid, "live" pairs) into a new temporary file and then atomically replaces (`os.replace`) the original data file with it. This rids the log of redundant and obsolete records. The approach is analogous to the merge/compaction operation used in systems such as Bitcask or in LSM trees (log-structured merge-trees). Writing to a temporary file and swapping atomically guarantees that if a failure occurs during compaction, the original file remains unchanged.

## `HashTable` implementation

Key collisions are resolved by **separate chaining**: each slot of the `buckets` array is the head of a linked list of nodes (`Node`). The hash function is polynomial (Horner's scheme):

$$h = \left( \sum_{i} c_i \cdot 31^{\,n-i} \right) \bmod \text{capacity}$$

where $c_i$ are the character codes (`ord`) of the individual characters of the key. This is the same principle used, for example, by the `hashCode()` method of strings in Java (multiplying by the constant 31 and successively adding character codes).

**Lazy deletion:** the `delete` method does not physically remove the node from the linked list; it only sets the flag `node.deleted = True`. This avoids having to handle more complex relinking of the list on deletion, and at the same time a deleted key can later be inserted again: the `insert` method finds such a node and clears the flag, thereby avoiding the creation of a duplicate node with the same key.

**Dynamic resizing (rehashing):** before every insertion, the `maybe_rehash` method checks whether inserting a new element would exceed `max_load_factor` (the ratio of the number of elements to the table capacity, default `0.75`). If so, the capacity is doubled and all existing key-value pairs are rehashed into a new, larger array. This keeps the expected time complexity of `insert`, `get` and `delete` at O(1) on average.

## Sources

- The string hashing principle (multiplying by the constant 31) corresponds to the standard polynomial rolling hash algorithm: <https://www.geeksforgeeks.org/dsa/string-hashing-using-polynomial-rolling-hash-function/>
- Separate chaining hash table in Python: <https://www.geeksforgeeks.org/dsa/implementation-of-hash-table-in-python-using-separate-chaining/>
