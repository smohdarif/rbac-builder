# Phase 26: Python Concepts

Concepts introduced when building a shared active user counter in Streamlit.

---

## Table of Contents

1. [`st.cache_resource` — Sharing State Across Sessions](#1-stcache_resource--sharing-state-across-sessions)
2. [`threading.Lock` — Protecting Shared Data](#2-threadinglock--protecting-shared-data)
3. [`uuid.uuid4()` — Generating Unique IDs](#3-uuiduuid4--generating-unique-ids)
4. [`time.time()` — Timestamps and Staleness](#4-timetime--timestamps-and-staleness)
5. [Dict Cleanup with List Comprehension](#5-dict-cleanup-with-list-comprehension)
6. [Quick Reference Card](#quick-reference-card)

---

## 1. `st.cache_resource` — Sharing State Across Sessions

### The problem

Each Streamlit session has its own `st.session_state` — completely isolated. Session A can't see Session B's data. But we need a counter visible to all sessions.

### The solution

`st.cache_resource` runs a function **once** and returns the **same object** to every caller. Since Python dicts are mutable, all sessions share the same dict.

```python
# This function runs ONCE, then every session gets the same dict
@st.cache_resource
def _get_session_store() -> dict:
    return {}

# Session A calls _get_session_store() → gets dict at memory address 0x1234
# Session B calls _get_session_store() → gets SAME dict at 0x1234
# Session A writes to the dict → Session B sees the change
```

### `cache_resource` vs `cache_data`

```python
# cache_data: returns a COPY each time (safe for immutable data)
@st.cache_data
def get_config():
    return {"key": "value"}
# Session A gets a copy, Session B gets a different copy
# Mutations are NOT shared

# cache_resource: returns the SAME object (for shared mutable state)
@st.cache_resource
def get_store():
    return {}
# Session A and B share the same dict
# Mutations ARE shared — this is what we want
```

### When to use each

| | `cache_data` | `cache_resource` |
|-|--------------|-----------------|
| Returns | Copy | Same object |
| Mutations shared? | No | Yes |
| Use for | Database query results, computed data | Database connections, shared state, locks |

---

## 2. `threading.Lock` — Protecting Shared Data

### The problem

Two Streamlit sessions can rerun at the same time (concurrent threads in the same process). If both modify the shared dict simultaneously, data can get corrupted.

```python
# WITHOUT lock — race condition possible
# Thread A reads store, sees 3 entries
# Thread B reads store, sees 3 entries
# Thread A deletes stale entry → 2 entries
# Thread B deletes same stale entry → KeyError!
```

### The solution

A `threading.Lock` ensures only one thread modifies the dict at a time.

```python
import threading

lock = threading.Lock()

# Approach 1: with statement (preferred — auto-releases)
with lock:
    store[session_id] = time.time()
# Lock is automatically released here, even if an exception occurs

# Approach 2: manual acquire/release (avoid — easy to forget release)
lock.acquire()
try:
    store[session_id] = time.time()
finally:
    lock.release()
```

### GOTCHA: Always use `with`

```python
# BAD — if an exception happens, the lock is never released → deadlock
lock.acquire()
store[session_id] = time.time()   # what if this line raises an error?
lock.release()                     # never reached → all other threads blocked forever

# GOOD — 'with' guarantees release even on exception
with lock:
    store[session_id] = time.time()
```

### Why `cache_resource` for the lock too?

```python
@st.cache_resource
def _get_lock() -> threading.Lock:
    return threading.Lock()
```

The lock must also be a singleton — all sessions need the SAME lock object. If each session created its own lock, they wouldn't actually synchronize.

---

## 3. `uuid.uuid4()` — Generating Unique IDs

### The concept

We need a unique identifier for each browser session. `uuid.uuid4()` generates a random 128-bit ID that is practically guaranteed to be unique.

```python
import uuid

session_id = str(uuid.uuid4())
# "a8098c1a-f86e-11da-bd1a-00112444be1e"
# ^^^^^^^^ ^^^^ ^^^^ ^^^^ ^^^^^^^^^^^^
# 8 chars   4    4    4    12 chars
# Total: 36 characters with hyphens, 32 hex digits

# UUID4 = random. Other versions:
# UUID1 = based on timestamp + MAC address (not private)
# UUID3 = based on MD5 hash of a name
# UUID5 = based on SHA-1 hash of a name
```

### Why not use Streamlit's session ID?

Streamlit has an internal session ID, but it's not reliably accessible across all versions and deployment environments. A self-generated UUID is simpler and portable.

```python
# Store it in session_state so it persists across reruns
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# First rerun:  generates "abc123..."
# Second rerun: already in session_state, reuses "abc123..."
# New tab:      new session_state, generates "def456..."
```

---

## 4. `time.time()` — Timestamps and Staleness

### The concept

`time.time()` returns the current time as a float — seconds since January 1, 1970 (the "Unix epoch").

```python
import time

now = time.time()
# 1711234567.89  ← seconds since 1970-01-01

# To check if something is "stale" (older than N seconds):
last_seen = 1711234500.0
elapsed = now - last_seen   # 67.89 seconds
is_stale = elapsed > 60     # True — over 60 seconds old
```

### Why `time.time()` and not `datetime.now()`?

```python
import time
from datetime import datetime

# time.time() → float (easy to subtract, compact to store)
t1 = time.time()          # 1711234567.89
t2 = time.time()          # 1711234570.12
elapsed = t2 - t1         # 2.23 seconds ← simple subtraction

# datetime.now() → datetime object (heavier, need timedelta math)
d1 = datetime.now()       # datetime(2026, 3, 23, 14, 22, 47, 890000)
d2 = datetime.now()       # datetime(2026, 3, 23, 14, 22, 50, 120000)
elapsed = (d2 - d1).total_seconds()  # 2.23 ← more verbose

# For a simple "seconds since last seen" check, time.time() wins
```

### Stale entry cleanup pattern

```python
def cleanup_stale(store: dict, timeout: int = 60) -> int:
    """Remove stale entries and return count of remaining."""
    now = time.time()

    # Step 1: Find stale keys (can't modify dict while iterating)
    stale = [sid for sid, ts in store.items() if now - ts > timeout]

    # Step 2: Delete them
    for key in stale:
        del store[key]

    return len(store)
```

### GOTCHA: Don't modify a dict while iterating it

```python
# BAD — RuntimeError: dictionary changed size during iteration
for sid, ts in store.items():
    if now - ts > 60:
        del store[sid]   # modifying dict while looping!

# GOOD — collect keys first, then delete
stale = [sid for sid, ts in store.items() if now - ts > 60]
for key in stale:
    del store[key]
```

---

## 5. Dict Cleanup with List Comprehension

### The pattern

We use a list comprehension as a "filter step" — identify which keys to delete, then delete them in a separate loop.

```python
# List comprehension to find stale keys
stale_keys = [
    sid                              # what to collect
    for sid, last_seen in store.items()  # iterate key-value pairs
    if now - last_seen > 60          # condition: older than 60s
]
# Result: ["uuid-ccc", "uuid-ddd"]  (only the stale ones)
```

### Why not dict comprehension to rebuild?

```python
# Alternative: rebuild the dict with only active entries
store = {
    sid: ts
    for sid, ts in store.items()
    if now - ts <= 60
}
# This WORKS, but creates a NEW dict.
# Problem: other sessions still hold a reference to the OLD dict.
# They wouldn't see the new one!

# That's why we DELETE from the existing dict instead of replacing it.
# The shared reference (from cache_resource) must stay the same object.
```

### Key insight: mutate, don't replace

```python
# BAD — replaces the dict object (other sessions still point to old one)
store = {k: v for k, v in store.items() if not stale(v)}

# GOOD — mutates the existing dict (all sessions see the change)
for key in stale_keys:
    del store[key]
```

This is the same reason we use `cache_resource` (shared reference) instead of `cache_data` (copies).

---

## Quick Reference Card

```python
# Shared singleton across all Streamlit sessions
@st.cache_resource
def _get_store() -> dict:
    return {}

# Thread-safe lock (also a singleton)
@st.cache_resource
def _get_lock() -> threading.Lock:
    return threading.Lock()

# Generate a unique session ID (once per session)
session_id = str(uuid.uuid4())

# Heartbeat: record "I'm still here"
with lock:
    store[session_id] = time.time()

# Count active users (cleanup stale entries)
now = time.time()
with lock:
    stale = [k for k, ts in store.items() if now - ts > 60]
    for k in stale:
        del store[k]
    active_count = len(store)

# GOTCHA: Don't replace the dict — mutate it
# del store[key]  ✅  (mutates shared object)
# store = {}      ❌  (creates new object, breaks sharing)

# GOTCHA: Don't modify dict during iteration
# Collect keys first, then delete in separate loop

# cache_resource = shared mutable object (connections, locks, state)
# cache_data     = copied immutable result (query results, computed data)
```

---

## Next Steps

- [← DESIGN.md](./DESIGN.md)
