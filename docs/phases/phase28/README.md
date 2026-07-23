# Phase 28: Config Upload & Resume

| Field | Value |
|-------|-------|
| **Phase** | 28 |
| **Status** | ✅ Implemented (2026-07-23) |
| **Priority** | 🔴 High |
| **Goal** | Upload a previously saved JSON config and resume exactly where you left off |
| **Depends on** | Phase 2 (Storage Service), Phase 1 (Data Models) |
| **Client driver** | iSeatz — Dan Berkowitz requested the "Upload Config" button (2026-07-23) |

> ⚠️ **Scope revised 2026-07-23.** A real downloaded config from iSeatz revealed that the
> **Download** button and this **Upload** design use two *different* JSON schemas. Phase 28
> must normalise both. Full analysis: **[REQUIREMENT-iseatz-upload.md](./REQUIREMENT-iseatz-upload.md)**.
> Sample fixture: `configs/customers/iseatz/2026.05.12iseatz_rbac_config.json`.

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

## Files Created/Modified

| File | Action | Status |
|------|--------|--------|
| `services/config_importer.py` | **CREATED** — schema autodetect, normalise (A **or** B) → `NormalizedConfig`, `to_rbac_config()`, pure DataFrame builders | ✅ |
| `services/__init__.py` | Export the importer API | ✅ |
| `ui/setup_tab.py` | ADD `_render_upload_section()` + `_restore_config_to_session()` (calls the importer) | ✅ |
| `tests/test_config_upload.py` | CREATED — 21 tests (both schemas, iSeatz fixture) | ✅ |
| `models/permissions.py` | EXTENDED — `ProjectPermission` gains observability + `manage_ai_variations` fields | ✅ |
| `ui/deploy_tab.py` | Download emits **canonical Schema A**; **Save** (`build_config_from_session`) rerouted through the importer so it writes complete configs too (FIX-006) | ✅ |

---

## Implementation Checklist

- [x] DESIGN.md complete
- [x] PYTHON_CONCEPTS.md complete
- [x] REQUIREMENT-iseatz-upload.md — client request + schema-mismatch analysis
- [x] Sample fixture saved — `configs/customers/iseatz/2026.05.12iseatz_rbac_config.json`
- [x] `services/config_importer.py` — schema autodetect + normalise (A and B) + null coalescing + team-name→key resolution
- [x] `ui/setup_tab.py` — file uploader + restore logic
- [x] `tests/test_config_upload.py` — 21 tests passing (incl. schema-B cases using the iSeatz fixture)
- [ ] Manual test: download config → refresh page → upload → verify all tabs populated
- [ ] Manual test: upload the **iSeatz** file specifically → 6 teams, 10 envs, 6 project + 60 env permissions restored
- [ ] Manual test: upload on Streamlit Cloud

---

## Key Implementation Decisions

1. **Schema unified to A (done).** `ProjectPermission` was extended with the Phase 14
   observability columns + `manage_ai_variations`, so the model now holds **all 18** project
   columns. With that gap closed, the **Download button emits canonical Schema A**
   (`RBACConfig.to_dict()`) — the same schema the Save button writes. There is now **one
   write format**. The importer still reads legacy Schema B so files already downloaded in
   the field (like iSeatz's) keep importing.

2. **`NormalizedConfig` intermediate.** The importer still returns a schema-agnostic
   `NormalizedConfig` keyed by UI label — it's what the Setup-tab restore hydrates the
   matrix DataFrames from, and it's what reads legacy Schema B. `to_rbac_config()` is now
   **lossless** (the model holds every column) and is used by both the download and save
   paths.

   - **FIX-006 (same work):** the 💾 Save button's `build_config_from_session()` used to
     drop the permission matrices (teams + env_groups only), silently saving configs with
     zero permissions. It now shares the importer path, so **Save and Download write
     identical, complete Schema-A configs.**

3. **`_advisor_applied` is set to `False` on restore.** Setting it `True` would trigger the
   Matrix tab to regenerate team keys from names ("Developer" → "developer"), clobbering the
   real keys ("dev"). Restore preserves the uploaded keys and relies on the normal sync path.

4. **Critical env auto-sets Requires Approval = True (affirmed).** Because Download now
   routes through the model layer, `EnvironmentGroup`'s rule — a Critical environment
   implies approvals — applies to downloaded configs too. This is intentional: a critical
   env with `Requires Approvals` left blank/false serialises as `requires_approval: true`.
   Decision affirmed 2026-07-23. Locked by `tests/test_config_upload.py::
   test_critical_env_auto_sets_requires_approval_on_download` and `test_models.py`.
