# Phase 15: UI Grouping & Tab Layout

| Field | Value |
|-------|-------|
| **Phase** | 15 |
| **Status** | ✅ Complete |
| **Goal** | Replace the flat wide permission matrix with a tab-based grouped layout, organised by feature domain — Flag Lifecycle, AI Configs, Observability, etc. |
| **Depends on** | Phase 5 (UI Modules), Phase 14 (Observability Permissions) |

---

## Problem

The current Per-Project Permissions matrix has 15+ columns in a single flat table:

```
Team | Create Flags | Update Flags | Archive Flags | Client Side | Metrics |
     | Pipelines | Create AI | Update AI | Delete AI | AI Variations |
     | View Project | Sessions | Errors | Logs | Traces | ...
```

**Issues:**
- Column headers are **truncated** (not enough space)
- **Horizontal scrolling** required
- **No logical grouping** — AI Configs sit next to Flag actions with no separation
- SAs must scan the entire table to find what they need
- Hard to answer "what can this team do with Observability?" at a glance

---

## Solution

Replace the flat table with **`st.tabs()`** — one tab per feature domain.

### Per-Project Permissions Tabs

| Tab | Icon | Permissions |
|-----|------|------------|
| Flag Lifecycle | 🚩 | Create Flags, Update Flags, Archive Flags, Update Client Side Availability |
| Metrics & Pipelines | 📊 | Manage Metrics, Manage Release Pipelines, View Project |
| AI Configs | 🤖 | Create AI Configs, Update AI Configs, Delete AI Configs, Manage AI Variations |
| Observability | 🔭 | View Sessions, View Errors, View Logs, View Traces, Manage Alerts, Manage Observability Dashboards, Talk to Vega |
| Summary | 📋 | Read-only overview of all permissions across all groups |

### Per-Environment Permissions Tabs

| Tab | Icon | Permissions |
|-----|------|------------|
| Targeting & Approvals | 🎯 | Update Targeting, Review Changes, Apply Changes |
| Segments | 🗂️ | Manage Segments |
| Experiments | 🧪 | Manage Experiments |
| SDK & AI | 🔑 | View SDK Key, Update AI Config Targeting |

---

## Design Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Python concepts: st.tabs(), dict of lists, refactoring render functions |

---

## Files to Modify

| File | Change |
|------|--------|
| `core/ld_actions.py` | ADD `PROJECT_PERMISSION_GROUPS` and `ENV_PERMISSION_GROUPS` constants |
| `ui/matrix_tab.py` | REFACTOR `_render_project_matrix_with_checkboxes()` and `_render_env_matrix_with_checkboxes()` to use `st.tabs()` |

> **No changes to payload builder or tests** — this is a pure UI refactor. The underlying data model (`project_matrix` and `env_matrix` DataFrames) does not change. All existing tests remain valid.

---

## Implementation Checklist

- [ ] `DESIGN.md` complete
- [ ] `PYTHON_CONCEPTS.md` complete
- [ ] `PROJECT_PERMISSION_GROUPS` added to `core/ld_actions.py`
- [ ] `ENV_PERMISSION_GROUPS` added to `core/ld_actions.py`
- [ ] `_render_project_matrix_with_checkboxes()` refactored with tabs
- [ ] `_render_env_matrix_with_checkboxes()` refactored with tabs
- [ ] Summary tab implemented (read-only)
- [ ] All existing tests still passing (no payload changes)
- [ ] Visual review: no truncated headers, no horizontal scroll
