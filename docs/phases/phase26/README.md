# Phase 26: Active User Counter

| Field | Value |
|-------|-------|
| **Phase** | 26 |
| **Status** | 📋 Design Complete — Ready for Implementation |
| **Priority** | 🟡 Medium |
| **Goal** | Show how many SAs are currently using the app — live count in the sidebar |
| **Depends on** | None (standalone feature) |

---

## What the SA Sees

A small metric in the sidebar:

```
┌─────────────────────┐
│  👥 Active Users: 7 │
└─────────────────────┘
```

Updates on every page interaction. An "active" user = someone who interacted within the last 60 seconds.

---

## Key Design Decision: In-Memory Dict via `st.cache_resource`

| Approach | Verdict | Reason |
|----------|---------|--------|
| `st.cache_resource` shared dict | ✅ Chosen | Zero dependencies, works on Cloud, all sessions share one process |
| Shared file on disk | ❌ | File I/O on every rerun, needs `fcntl` locking, error-prone |
| External DB / Redis | ❌ | Overkill for 24 users, adds infra dependency |
| `st.session_state` alone | ❌ | Isolated per session — no cross-session visibility |
| `st.cache_data` | ❌ | Returns copies, not shared references — mutations don't propagate |

**Why `st.cache_resource`:** On Streamlit Cloud (and localhost), all sessions run in the **same Python process**. `cache_resource` returns a singleton object shared across every session. A mutable dict stored this way is visible to all users. No external services needed.

---

## Limitations

1. **Process restart resets count** — recovers in seconds as users interact
2. **60s timeout** — idle tabs drop off (configurable)
3. **Single-process only** — fine for 24 users on Streamlit Cloud
4. **No historical data** — live count only, no analytics
5. **Updates on interaction** — not auto-refreshing

---

## Design Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, 10 test cases, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Python concepts: `cache_resource`, `threading.Lock`, `uuid`, `time.time()`, stale entry cleanup |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `core/session_tracker.py` | CREATE — `heartbeat()`, `get_active_count()`, shared dict |
| `core/__init__.py` | ADD exports for new functions |
| `app.py` | ADD heartbeat call + sidebar metric display |
| `tests/test_session_tracker.py` | CREATE — 10 test cases |

---

## Implementation Checklist

- [x] DESIGN.md complete
- [x] PYTHON_CONCEPTS.md complete
- [ ] `core/session_tracker.py` created
- [ ] `core/__init__.py` updated
- [ ] `app.py` updated — heartbeat + sidebar metric
- [ ] `tests/test_session_tracker.py` created — all 10 tests passing
- [ ] Manual test: open 3 browser tabs, verify count = 3
- [ ] Manual test: close 1 tab, wait 60s, verify count drops to 2
