# Phase 26: Design Document — Active User Counter

| Field | Value |
|-------|-------|
| **Phase** | 26 |
| **Status** | 📋 Design Complete — Ready for Implementation |
| **Goal** | Show a live count of active users in the sidebar |
| **Dependencies** | None |

## Related Documents

| Document | Link |
|----------|------|
| Phase README | [README.md](./README.md) |
| Python Concepts | [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) |

---

## High-Level Design (HLD)

### What Are We Building and Why?

The RBAC Builder is used by a team of 24 SAs. The team lead wants visibility into concurrent usage to:
- Understand actual adoption
- Know if scaling is needed (Streamlit Cloud resource limits)
- Make deployment timing decisions (avoid restarts during peak usage)

We add a lightweight active user counter that shows in the sidebar on every page.

### Architecture Diagram

```
Session A (Browser Tab 1)          Session B (Browser Tab 2)
    │                                   │
    │  st.rerun() on interaction        │  st.rerun() on interaction
    │                                   │
    ▼                                   ▼
┌──────────────────────────────────────────────────────┐
│                   Python Process                      │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │   @st.cache_resource → SHARED DICT (singleton)  │  │
│  │                                                  │  │
│  │   {                                              │  │
│  │     "uuid-aaa": 1711234567.89,  ← Session A     │  │
│  │     "uuid-bbb": 1711234570.12,  ← Session B     │  │
│  │     "uuid-ccc": 1711234490.00,  ← STALE (>60s)  │  │
│  │   }                                              │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  threading.Lock protects concurrent writes             │
└──────────────────────────────────────────────────────┘
```

### Core Features Table

| Feature | Description |
|---------|-------------|
| Heartbeat | Each session updates its timestamp on every script rerun |
| Stale cleanup | Sessions with no heartbeat in 60s are removed |
| Thread safety | `threading.Lock` protects the shared dict |
| Sidebar display | `st.metric("Active Users", count)` in the sidebar |

### Data Flow

```
SA opens browser tab
        │
        ▼
app.py runs → heartbeat()
        │
        ├─ First time? Generate uuid, store in st.session_state
        │
        ├─ Update shared_dict[session_id] = time.time()
        │
        ▼
app.py sidebar → get_active_count()
        │
        ├─ Remove entries where (now - last_seen) > 60s
        │
        └─ Return len(shared_dict)
        │
        ▼
st.metric("Active Users", 7)
```

---

## Detailed Low-Level Design (DLD)

### 1. `core/session_tracker.py`

#### Shared State via `@st.cache_resource`

```python
import time
import uuid
import threading
import streamlit as st

SESSION_TIMEOUT_SECONDS = 60

@st.cache_resource
def _get_session_store() -> dict[str, float]:
    """
    Returns a dict shared across ALL sessions in this process.
    Key = session_id (str), Value = last_seen timestamp (float).

    LESSON: st.cache_resource
    ==========================
    st.cache_resource runs the function ONCE, then returns the SAME
    object to every caller. Since dicts are mutable, all sessions
    read and write the same dict. This is how we share state without
    a database.
    """
    return {}

@st.cache_resource
def _get_lock() -> threading.Lock:
    """
    A shared lock to prevent race conditions.

    LESSON: threading.Lock
    =======================
    Multiple Streamlit sessions can rerun concurrently in the same
    process. Without a lock, two sessions could modify the dict at
    the same time, causing data corruption. The lock ensures only
    one session modifies the dict at a time.
    """
    return threading.Lock()
```

#### `heartbeat()` — Call on Every Rerun

```python
def heartbeat() -> None:
    """
    Register the current session as active.
    Call this once at the top of app.py on every rerun.

    First call: generates a unique session_id via uuid4().
    Every call: updates the timestamp to now.
    """
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    store = _get_session_store()
    lock = _get_lock()

    with lock:
        store[st.session_state.session_id] = time.time()
```

#### `get_active_count()` — Read + Cleanup

```python
def get_active_count() -> int:
    """
    Returns the number of active sessions (heartbeat within timeout).
    Also removes stale entries as a side effect.
    """
    store = _get_session_store()
    lock = _get_lock()
    now = time.time()

    with lock:
        # Find and remove stale sessions
        stale_keys = [
            sid for sid, last_seen in store.items()
            if now - last_seen > SESSION_TIMEOUT_SECONDS
        ]
        for key in stale_keys:
            del store[key]

        return len(store)
```

#### `get_active_sessions()` — Optional Debug Helper

```python
def get_active_sessions() -> list[dict]:
    """
    Returns list of active sessions with their last seen time.
    Useful for debugging / admin view.
    """
    store = _get_session_store()
    lock = _get_lock()
    now = time.time()

    with lock:
        return [
            {
                "session_id": sid[:8] + "...",   # truncated for privacy
                "last_seen_seconds_ago": round(now - last_seen, 1),
            }
            for sid, last_seen in store.items()
            if now - last_seen <= SESSION_TIMEOUT_SECONDS
        ]
```

### 2. `app.py` Changes

```python
# At the top, after existing imports
from core.session_tracker import heartbeat, get_active_count

# Right after st.set_page_config(...)
heartbeat()

# Inside the sidebar block
with st.sidebar:
    # ... existing sidebar content ...

    # Active user count at the bottom of the sidebar
    st.divider()
    st.metric("Active Users", get_active_count())
```

### 3. `core/__init__.py` Changes

```python
from .session_tracker import heartbeat, get_active_count
```

---

## Pseudo Logic

### 1. `heartbeat()`

```
FUNCTION heartbeat():

  IF "session_id" NOT in st.session_state:
    session_id = generate random UUID
    st.session_state.session_id = session_id

  store = get shared dict (cache_resource singleton)
  lock  = get shared lock (cache_resource singleton)

  ACQUIRE lock:
    store[session_id] = current timestamp
  RELEASE lock
```

### 2. `get_active_count()`

```
FUNCTION get_active_count() -> int:

  store = get shared dict
  lock  = get shared lock
  now   = current timestamp

  ACQUIRE lock:
    stale_keys = []
    FOR each (session_id, last_seen) in store:
      IF (now - last_seen) > 60 seconds:
        stale_keys.append(session_id)

    FOR each key in stale_keys:
      DELETE store[key]

    RETURN length of store
  RELEASE lock
```

### 3. App integration

```
FUNCTION app_main():

  st.set_page_config(...)

  # Register this session as active
  heartbeat()

  # ... existing app logic ...

  WITH st.sidebar:
    # ... existing sidebar ...
    st.divider()
    count = get_active_count()
    st.metric("Active Users", count)
```

---

## Test Cases

**Test file:** `tests/test_session_tracker.py`

> **Note:** Tests must mock `st.cache_resource` and `st.session_state` since
> Streamlit's runtime is not available during `pytest`. We test the core logic
> (dict manipulation, timestamps, locking) directly.

### Group 1: Heartbeat Registration

#### TC-SC-01: First heartbeat creates a session entry
```
GIVEN: empty session store
WHEN:  heartbeat() is called with session_id = "aaa"
THEN:  store contains {"aaa": <timestamp>}
       len(store) == 1
```

#### TC-SC-02: Repeated heartbeats update the timestamp
```
GIVEN: store has {"aaa": 1000}
WHEN:  heartbeat() is called again with session_id = "aaa" at time 1005
THEN:  store["aaa"] == 1005 (updated, not duplicated)
       len(store) == 1
```

#### TC-SC-03: Multiple sessions get separate entries
```
GIVEN: empty store
WHEN:  heartbeat() called with session_id = "aaa"
       heartbeat() called with session_id = "bbb"
THEN:  len(store) == 2
       "aaa" in store and "bbb" in store
```

### Group 2: Active Count + Cleanup

#### TC-SC-04: Active count returns only non-stale sessions
```
GIVEN: store has:
  "aaa": now - 10s   (active)
  "bbb": now - 30s   (active)
  "ccc": now - 90s   (stale — over 60s)
WHEN:  get_active_count() is called
THEN:  returns 2
       "ccc" is removed from store
```

#### TC-SC-05: All sessions stale returns 0
```
GIVEN: store has:
  "aaa": now - 120s
  "bbb": now - 180s
WHEN:  get_active_count() is called
THEN:  returns 0
       store is empty
```

#### TC-SC-06: Empty store returns 0
```
GIVEN: empty store
WHEN:  get_active_count() is called
THEN:  returns 0
```

#### TC-SC-07: Session at exactly timeout boundary is removed
```
GIVEN: store has:
  "aaa": now - 60.001s  (just over timeout)
  "bbb": now - 59.999s  (just under timeout)
WHEN:  get_active_count() is called
THEN:  returns 1
       "aaa" removed, "bbb" remains
```

### Group 3: Thread Safety

#### TC-SC-08: Concurrent heartbeats don't corrupt the store
```
GIVEN: empty store
WHEN:  10 threads each call heartbeat() with unique session_ids simultaneously
THEN:  store has exactly 10 entries
       no exceptions raised
```

### Group 4: Edge Cases

#### TC-SC-09: Session ID is a valid UUID string
```
GIVEN: heartbeat() called (session_id generated internally)
THEN:  session_id in store is a valid UUID4 string
```

#### TC-SC-10: get_active_sessions returns truncated IDs
```
GIVEN: store has {"abcd1234-5678-..." : now}
WHEN:  get_active_sessions() is called
THEN:  result[0]["session_id"] == "abcd1234..."
       result[0]["last_seen_seconds_ago"] is a float >= 0
```

---

## Implementation Plan

| Step | Task | File |
|------|------|------|
| 1 | Create `_get_session_store()` with `@st.cache_resource` | `core/session_tracker.py` |
| 2 | Create `_get_lock()` with `@st.cache_resource` | `core/session_tracker.py` |
| 3 | Implement `heartbeat()` | `core/session_tracker.py` |
| 4 | Implement `get_active_count()` | `core/session_tracker.py` |
| 5 | Implement `get_active_sessions()` (optional debug) | `core/session_tracker.py` |
| 6 | Export from `core/__init__.py` | `core/__init__.py` |
| 7 | Add `heartbeat()` call in `app.py` | `app.py` |
| 8 | Add sidebar metric in `app.py` | `app.py` |
| 9 | Write all 10 tests | `tests/test_session_tracker.py` |
| 10 | Run full test suite | `pytest tests/ -v` |

### Python Concepts in This Phase

| Concept | Used for |
|---------|---------|
| `st.cache_resource` | Singleton shared dict across all sessions |
| `threading.Lock` | Prevent race conditions on shared state |
| `uuid.uuid4()` | Generate unique session identifiers |
| `time.time()` | Timestamps for heartbeat/staleness checks |
| Dict comprehension with filter | Cleanup stale entries |
| `with` statement (context manager) | Lock acquire/release |

---

## Navigation

- [← README](./README.md)
- [Python Concepts →](./PYTHON_CONCEPTS.md)
