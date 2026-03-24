# Phase 28: Config Upload & Resume

| Field | Value |
|-------|-------|
| **Phase** | 28 |
| **Status** | 📋 Design Complete — Ready for Implementation |
| **Priority** | 🔴 High |
| **Goal** | Upload a previously saved JSON config and resume exactly where you left off |
| **Depends on** | Phase 2 (Storage Service), Phase 1 (Data Models) |

---

## The Problem

SAs frequently work on RBAC designs across multiple sessions:
- Start a design in a customer call, need to finish later
- Download a config JSON, close the browser, come back next day
- On Streamlit Cloud, server storage is ephemeral — configs vanish on restart

Today the app can **save/download** configs but has no way to **upload/resume** them.
The SA has to manually re-enter everything.

## The Solution

A **file uploader** on the Setup tab that:
1. Accepts a previously downloaded `*_rbac_config.json`
2. Parses it and restores the full session: customer name, project key, teams, environments, permissions
3. SA picks up exactly where they left off — all tabs pre-populated

Works identically on localhost and Streamlit Cloud.

---

## What the SA Sees

```
┌──────────────────────────────────────────────────────────────────────┐
│  Step 1: Setup                                                        │
│                                                                       │
│  ┌─ Resume Previous Work ──────────────────────────────────────────┐  │
│  │                                                                  │  │
│  │  📂 Upload a saved config to resume where you left off          │  │
│  │                                                                  │  │
│  │  [ Browse files ]  or  [ drag and drop ]                        │  │
│  │  Accepted: .json                                                │  │
│  │                                                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ── OR start fresh ──────────────────────────────────────────────────  │
│                                                                       │
│  Customer: Voya  |  Mode: Manual                                      │
│  ... (existing Setup UI) ...                                          │
└──────────────────────────────────────────────────────────────────────┘
```

After upload, a success banner shows what was restored:
```
✅ Config loaded! Restored: customer "Voya", project "voya-web",
   4 teams, 2 environments, 18 project permissions, 8 environment permissions.
   Switch to the Design Matrix tab to review.
```

---

## Design Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, test cases, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Python concepts: file_uploader, JSON parsing, session_state hydration |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `ui/setup_tab.py` | ADD file uploader section + `_restore_config_to_session()` |
| `tests/test_config_upload.py` | CREATE — test cases for upload/restore |

---

## Implementation Checklist

- [x] DESIGN.md complete
- [x] PYTHON_CONCEPTS.md complete
- [ ] `ui/setup_tab.py` — file uploader + restore logic
- [ ] `tests/test_config_upload.py` — all tests passing
- [ ] Manual test: download config → refresh page → upload → verify all tabs populated
- [ ] Manual test: upload on Streamlit Cloud
