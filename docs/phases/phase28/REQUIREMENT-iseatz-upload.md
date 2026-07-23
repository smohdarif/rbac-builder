# Requirement: "Upload Config" button — iSeatz field request

| Field | Value |
|-------|-------|
| **Requested by** | Dan Berkowitz (iSeatz) |
| **Date raised** | 2026-07-23 |
| **Channel** | Email — *"Hey, Arif! Were you able to get the Upload Config button added?"* |
| **Maps to** | **Phase 28 — Config Upload & Resume** (already designed, not yet implemented) |
| **Sample file** | `configs/customers/iseatz/2026.05.12iseatz_rbac_config.json` |
| **Tracker IDs** | `ENH-037`, `FIX-005`, `ENH-038` (see `docs/ENHANCEMENT_TRACKER.md`) |
| **Priority** | 🔴 P1 (client-blocking for their round-trip workflow) |

---

## What the client is asking for

Dan downloaded an RBAC config from the builder (the iSeatz/amex file above) and now
wants to **upload it back** to resume editing. This is exactly the feature scoped in
**Phase 28** — a file uploader on the Setup tab that restores customer, project, teams,
environments, and both permission matrices.

**The button itself is not new work conceptually — Phase 28 already designs it.** What
this request adds is a hard constraint discovered from a *real* downloaded file: the
upload must accept the schema the **Download button actually emits**.

---

## Critical finding — the download and upload schemas do not match

The iSeatz sample is a genuine artifact of our own **Download** button
(`ui/deploy_tab.py` → `_build_config_dict`, lines 94–103). That function serialises the
in-memory Streamlit DataFrames directly:

```python
"teams":               st.session_state.teams.to_dict(orient="records"),
"env_groups":          st.session_state.env_groups.to_dict(orient="records"),
"project_permissions": st.session_state.project_matrix.to_dict(orient="records"),
"env_permissions":     st.session_state.env_matrix.to_dict(orient="records"),
```

Because the DataFrame columns are the **UI display labels**, the download uses
**Title-Case keys with spaces**, and references teams **by display name**. But Phase 28's
`_parse_uploaded_config()` / `_restore_config_to_session()` (see `DESIGN.md`) were
written against the **snake_case `RBACConfig.to_dict()` schema** used by the Storage
service. **They are two different formats.** Uploading a real downloaded file with the
Phase 28 code as-designed would fail validation and never restore.

There are genuinely **two persisted config formats in the repo today:**

| # | Schema | Produced by | Example on disk | Team ref | Casing |
|---|--------|-------------|-----------------|----------|--------|
| **A** | Canonical / storage | `services/storage.py` (Save), `RBACConfig.to_dict()` | `configs/customers/voya/config.json` | `team_key` (key) | `snake_case` |
| **B** | Display / download | `ui/deploy_tab.py` Download button | `configs/customers/iseatz/2026.05.12iseatz_rbac_config.json` | `"Team"` (name) | `Title Case` |

### Field-by-field comparison

| Concept | Schema A (storage) | Schema B (download — what iSeatz has) |
|---|---|---|
| Team | `{"key","name","description"}` | `{"Key","Name","Description"}` |
| Env group | `{"key","requires_approval","is_critical","notes"}` | `{"Key","Requires Approvals","Critical","Notes"}` |
| Project perm | `{"team_key","create_flags",...}` | `{"Team":<name>,"Create Flags",...}` |
| Env perm | `{"team_key","environment_key","update_targeting",...}` | `{"Team":<name>,"Environment":<env key>,"Update Targeting",...}` |
| Top level | includes `created_at`,`updated_at` | includes `version`, no timestamps |

**Consequence for Phase 28 as designed:**
- `_parse_uploaded_config` checks each team for lowercase `"key"`/`"name"` → **raises**
  `ConfigUploadError("Team missing 'key' or 'name'")` on schema B.
- `_restore_config_to_session` reads `t["key"]`, `e["requires_approval"]`,
  `pp["team_key"]`, `pp["create_flags"]` → **`KeyError`** on schema B.
- Project/env permissions key off `team_key`, but schema B only has the team **name** →
  even after a casing fix, the lookup wouldn't join without a name→key map.

---

## Data-quality notes from the iSeatz sample (handle on import)

The real file also exercises edge cases the importer must tolerate:

1. **Null env-group flags** — `qa`, `int`, `pt`, `stage`, `amex-stage`, `cert` have
   `"Requires Approvals": null` and/or `"Critical": null`. Coalesce `null → false`.
2. **Null descriptions** — teams `pd` and `devlead` have `"Description": null`. Coalesce
   `null → ""`.
3. **Likely mislabeled notes** — the `dev` env group is annotated *"Production
   environments"* while `test` is *"Development, QA, Staging"*. Not an importer bug, but
   worth surfacing to the SA on load (a soft warning, not a hard failure).
4. **Team referenced by name** — `"Team": "Developer"` must be resolved to key `dev` via
   the `teams` array (`Name` → `Key`). Fails safely if a permission row names a team not
   present in `teams`.

---

## Recommendation — extend Phase 28, add one small service module

This does **not** warrant a new phase. It stays **Phase 28**, with a scope addition:

1. **Introduce `services/config_importer.py`** — a normaliser that accepts *either*
   schema A or schema B (autodetected by inspecting keys) and returns a canonical
   `RBACConfig`. Keeping this in `services/` (not the UI) makes it unit-testable and
   reusable by Storage-load and the uploader alike.
2. **Phase 28 UI calls the importer** instead of parsing inline, then hydrates
   session_state from the canonical model.
3. **Align the round-trip contract** — ✅ **DONE (ENH-040).** `ProjectPermission` was
   extended with the observability columns so the model is lossless, and Download now emits
   canonical Schema A via `RBACConfig.to_dict()`. Save and Download share one schema; the
   importer keeps reading legacy Schema B files already in the field (like iSeatz's).

See `DESIGN.md` → *"Schema Compatibility"* for the detailed design and new test cases
(`TC-UP-15` … `TC-UP-19`).

---

## Navigation

- [← Phase 28 README](./README.md)
- [DESIGN.md](./DESIGN.md)
- [Enhancement Tracker](../../ENHANCEMENT_TRACKER.md)
