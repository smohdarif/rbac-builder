# Phase 15: Design Document — UI Grouping & Tab Layout

| Field | Value |
|-------|-------|
| **Phase** | 15 |
| **Status** | 📋 Design Complete |
| **Goal** | Tab-based grouped layout for the permission matrix |
| **Dependencies** | Phase 5 (UI Modules), Phase 14 (Observability) |

## Related Documents

| Document | Link |
|----------|------|
| Phase README | [README.md](./README.md) |
| Python Concepts | [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) |
| Current matrix UI | `ui/matrix_tab.py` |
| Action constants | `core/ld_actions.py` |

---

## High-Level Design (HLD)

### What Are We Building and Why?

A UX improvement to the permission matrix: replace one wide flat table with tabs grouped by feature domain. The underlying data model does not change — only the rendering layer changes.

### Architecture Diagram

```
BEFORE (Phase 14 state):
┌──────────────────────────────────────────────────────────────────────┐
│  Per-Project Permissions                                             │
│                                                                      │
│  Team | Create | Update | Archive | Client | Metrics | ... (15 cols)│
│  ─────┼────────┼────────┼─────────┼────────┼─────────┼─────────────│
│  Dev  │  □     │  □     │  □      │  □     │  □      │  ...        │
└──────────────────────────────────────────────────────────────────────┘
         ↑ truncated headers, horizontal scroll, no grouping

AFTER (Phase 15):
┌──────────────────────────────────────────────────────────────────────┐
│  Per-Project Permissions                                             │
│                                                                      │
│  [🚩 Flag Lifecycle][📊 Metrics][🤖 AI Configs][🔭 Observability][📋 Summary]│
│                                                                      │
│  🚩 Flag Lifecycle tab active:                                       │
│                                                                      │
│  Team        | Create Flags | Update Flags | Archive Flags | Client  │
│  ────────────┼──────────────┼──────────────┼──────────────┼─────── │
│  Developer   │      □       │      □       │      □       │   □    │
│  QA Engineer │      □       │      □       │      □       │   □    │
└──────────────────────────────────────────────────────────────────────┘
         ↑ full headers, no scroll, logical grouping
```

### Data Flow

```
UNCHANGED: session state data model
  st.session_state.project_matrix  ← DataFrame with ALL permission columns
  st.session_state.env_matrix      ← DataFrame with ALL env permission columns
          │
          │  (same data, different rendering)
          ▼
NEW: tab-aware rendering
  st.tabs(["🚩 Flag Lifecycle", "📊 Metrics", ...])
          │
          ├─ Tab 1: render only PROJECT_PERMISSION_GROUPS["Flag Lifecycle"] columns
          ├─ Tab 2: render only PROJECT_PERMISSION_GROUPS["Metrics & Pipelines"] columns
          ├─ Tab 3: render only PROJECT_PERMISSION_GROUPS["AI Configs"] columns
          ├─ Tab 4: render only PROJECT_PERMISSION_GROUPS["Observability"] columns
          └─ Tab 5: render summary (read-only, all columns)
```

### Core Features Table

| Feature | Before | After |
|---------|--------|-------|
| Column headers | Truncated | Full names |
| Horizontal scroll | Required | Not needed |
| Logical grouping | None | By feature domain |
| Column count per view | 15+ | 3–7 per tab |
| Observability visibility | Hidden in expander | Dedicated tab |
| Summary view | None | Read-only Summary tab |
| Data model change | — | None (UI only) |

---

## Detailed Low-Level Design (DLD)

### 1. New Constants in `core/ld_actions.py`

#### `PROJECT_PERMISSION_GROUPS`

```python
# =============================================================================
# LESSON: Dict of lists as a grouping structure (Phase 15)
# =============================================================================
# Maps tab name → list of permission column names for that tab.
# The ORDER of items in each list determines the column order in the UI.
# Adding a new permission to a group = one line change here.

PROJECT_PERMISSION_GROUPS: Dict[str, List[str]] = {
    "🚩 Flag Lifecycle": [
        "Create Flags",
        "Update Flags",
        "Archive Flags",
        "Update Client Side Availability",
    ],
    "📊 Metrics & Pipelines": [
        "Manage Metrics",
        "Manage Release Pipelines",
        "View Project",
    ],
    "🤖 AI Configs": [
        "Create AI Configs",
        "Update AI Configs",
        "Delete AI Configs",
        "Manage AI Variations",
    ],
    "🔭 Observability": [
        # Default (always visible within this tab)
        "View Sessions",
        "View Errors",
        "View Logs",
        "View Traces",
        # Optional (also in this tab — no more separate expander)
        "Manage Alerts",
        "Manage Observability Dashboards",
        "Talk to Vega",
    ],
}
```

> **Design decision:** The optional expander from Phase 14 is removed. Observability optional permissions move into the Observability tab. Simpler — one place for all observability.

#### `ENV_PERMISSION_GROUPS`

```python
ENV_PERMISSION_GROUPS: Dict[str, List[str]] = {
    "🎯 Targeting & Approvals": [
        "Update Targeting",
        "Review Changes",
        "Apply Changes",
    ],
    "🗂️ Segments": [
        "Manage Segments",
    ],
    "🧪 Experiments": [
        "Manage Experiments",
    ],
    "🔑 SDK & AI": [
        "View SDK Key",
        "Update AI Config Targeting",
    ],
}
```

---

### 2. Refactored `_render_project_matrix_with_checkboxes()`

#### Before (Phase 14 — single flat table)

```python
def _render_project_matrix_with_checkboxes():
    # ... one big table with all 15 columns
    cols = st.columns([2] + [1] * len(PROJECT_PERMISSIONS))
    # ... render all columns
```

#### After (Phase 15 — tabs)

```python
def _render_project_matrix_with_checkboxes():
    st.subheader("🏗️ Per-Project Permissions")
    st.caption("These permissions impact ALL environments in the project")

    # ... (init/sync logic unchanged) ...

    tab_names = list(PROJECT_PERMISSION_GROUPS.keys()) + ["📋 Summary"]
    tabs = st.tabs(tab_names)

    # Render each feature group tab
    for tab, (group_name, perms) in zip(tabs[:-1], PROJECT_PERMISSION_GROUPS.items()):
        with tab:
            _render_permission_group(perms, group_key=group_name)

    # Summary tab — read-only overview
    with tabs[-1]:
        _render_project_summary()
```

---

### 3. New Helper: `_render_permission_group(perms, group_key)`

Renders a focused matrix for one group of permissions.

```python
def _render_permission_group(perms: List[str], group_key: str) -> None:
    """
    Render a matrix section for a specific permission group.

    Args:
        perms:     List of permission column names for this group
        group_key: Group name used to generate unique widget keys
    """
    team_names = [n for n in st.session_state.teams["Name"].tolist() if n]

    # Header row with SHORT_NAMES for display
    cols = st.columns([2] + [1] * len(perms))
    cols[0].markdown("**Team**")
    for i, perm in enumerate(perms):
        cols[i + 1].markdown(f"**{SHORT_NAMES.get(perm, perm)}**")

    # Checkbox rows per team
    for team_idx, team in enumerate(team_names):
        cols = st.columns([2] + [1] * len(perms))
        cols[0].write(team)

        for perm_idx, perm in enumerate(perms):
            current_value = _get_matrix_value(team, perm)
            key = f"proj_{group_key}_{team_idx}_{perm_idx}"
            new_value = cols[perm_idx + 1].checkbox(
                perm, value=current_value, key=key, label_visibility="collapsed"
            )
            if new_value != current_value:
                _set_matrix_value(team, perm, new_value)
```

---

### 4. New Helper: `_render_project_summary()`

Read-only overview across all groups.

```python
def _render_project_summary() -> None:
    """
    Render a read-only summary of all project permissions across all groups.
    Uses st.dataframe() for a compact, scrollable overview.
    """
    st.caption("Read-only overview. Edit permissions in the individual tabs above.")

    if "project_matrix" not in st.session_state:
        st.info("No permissions configured yet.")
        return

    # Show only teams that have at least one permission enabled
    df = st.session_state.project_matrix.copy()

    # Display with colour highlighting for True values
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )
```

---

### 5. Short Names Reference

Updated `SHORT_NAMES` dict — used for column headers within each tab.

| Permission | Short Name |
|------------|-----------|
| Create Flags | Create |
| Update Flags | Update |
| Archive Flags | Archive |
| Update Client Side Availability | Client Side |
| Manage Metrics | Metrics |
| Manage Release Pipelines | Pipelines |
| View Project | View Proj |
| Create AI Configs | Create |
| Update AI Configs | Update |
| Delete AI Configs | Delete |
| Manage AI Variations | Variations |
| View Sessions | Sessions |
| View Errors | Errors |
| View Logs | Logs |
| View Traces | Traces |
| Manage Alerts | Alerts |
| Manage Observability Dashboards | Dashboards |
| Talk to Vega | Vega AI |
| Update Targeting | Targeting |
| Review Changes | Review |
| Apply Changes | Apply |
| Manage Segments | Segments |
| Manage Experiments | Experiments |
| View SDK Key | SDK Key |
| Update AI Config Targeting | AI Targeting |

---

### 6. Remove Optional Expander

Phase 14 introduced an `st.expander("Optional Permissions")` for Manage Alerts, Manage Dashboards, and Talk to Vega. This is **removed in Phase 15** — all observability permissions move into the **🔭 Observability** tab. The `OPTIONAL_PROJECT_PERMISSIONS` constant is removed from `matrix_tab.py`.

---

## Pseudo Logic

### 1. Render Per-Project Permissions (tabbed)

```
FUNCTION _render_project_matrix_with_checkboxes():

  # Setup (unchanged from Phase 14)
  team_names = get_team_names_from_session_state()
  IF no teams: show warning, RETURN

  initialise_matrix_if_needed(team_names)
  sync_matrix_with_current_teams(team_names)

  # Create tabs
  group_names  = keys of PROJECT_PERMISSION_GROUPS   # e.g. ["🚩 Flag Lifecycle", ...]
  tab_labels   = group_names + ["📋 Summary"]
  tabs         = st.tabs(tab_labels)

  # Render each feature group tab
  FOR each (tab, group_name) in zip(tabs[:-1], group_names):
    WITH tab:
      perms = PROJECT_PERMISSION_GROUPS[group_name]
      _render_permission_group(perms, group_key=group_name)

  # Render summary tab (last tab)
  WITH tabs[-1]:
    _render_project_summary()

END FUNCTION
```

### 2. Render Permission Group

```
FUNCTION _render_permission_group(perms, group_key):

  # Header row
  cols = st.columns([2] + [1 for each perm in perms])
  cols[0] = "Team" header
  FOR i, perm in perms:
    cols[i+1] = SHORT_NAMES[perm]

  # Checkbox rows
  FOR team_idx, team in team_names:
    cols = st.columns([2] + [1 for each perm in perms])
    cols[0] = team name

    FOR perm_idx, perm in perms:
      current_value = project_matrix[team][perm]
      widget_key    = f"proj_{group_key}_{team_idx}_{perm_idx}"
                      ↑ unique across tabs — avoids Streamlit DuplicateWidgetID error

      new_value = st.checkbox(value=current_value, key=widget_key)

      IF new_value != current_value:
        project_matrix[team][perm] = new_value   # update session state

END FUNCTION
```

### 3. Render Summary Tab

```
FUNCTION _render_project_summary():

  show caption: "Read-only overview. Edit in individual tabs."

  IF no project_matrix in session_state:
    show info message
    RETURN

  df = session_state.project_matrix.copy()

  # Replace True/False with readable symbols for display
  display_df = df.replace({True: "✅", False: "—"})

  st.dataframe(display_df, use_container_width=True)

END FUNCTION
```

---

## Implementation Plan

| Step | Task | File |
|------|------|------|
| 1 | Add `PROJECT_PERMISSION_GROUPS` constant | `core/ld_actions.py` |
| 2 | Add `ENV_PERMISSION_GROUPS` constant | `core/ld_actions.py` |
| 3 | Remove `OPTIONAL_PROJECT_PERMISSIONS` | `ui/matrix_tab.py` |
| 4 | Update `create_default_project_matrix()` to use groups | `ui/matrix_tab.py` |
| 5 | Add `_render_permission_group()` helper | `ui/matrix_tab.py` |
| 6 | Add `_render_project_summary()` helper | `ui/matrix_tab.py` |
| 7 | Refactor `_render_project_matrix_with_checkboxes()` | `ui/matrix_tab.py` |
| 8 | Refactor `_render_env_matrix_with_checkboxes()` | `ui/matrix_tab.py` |
| 9 | Update `SHORT_NAMES` dict | `ui/matrix_tab.py` |
| 10 | Run full test suite — no failures expected | `pytest tests/ -v` |

### Python Concepts in This Phase

| Concept | Used for |
|---------|---------|
| `st.tabs()` | Creating tabbed UI sections |
| `dict.keys()` / `dict.items()` | Iterating over permission groups |
| `zip()` | Pairing tabs with group names |
| `List[str]` slicing | Getting all tabs except last (`tabs[:-1]`) |
| `str.replace()` on DataFrame | Converting True/False to ✅/— for summary |
| f-string with group key | Generating unique widget keys across tabs |

---

## Learning Resources

- Streamlit tabs: https://docs.streamlit.io/library/api-reference/layout/st.tabs
- Python dict.items(): https://docs.python.org/3/library/stdtypes.html#dict.items
- Python zip(): https://docs.python.org/3/library/functions.html#zip

---

## Test Cases

> **Note:** No payload builder changes — all existing tests remain valid.
> Phase 15 tests are UI-level, focusing on the grouping constants and rendering.

### Group 1: Permission Group Constants

#### TC-P15-01: All permissions covered across groups
```
GIVEN: PROJECT_PERMISSION_GROUPS
WHEN:  all group values are flattened into one list
THEN:
  - Every permission in PROJECT_PERMISSIONS is in exactly one group
  - Every permission in OPTIONAL_PROJECT_PERMISSIONS is in exactly one group
  - No permission appears in more than one group
  - No permission is missing
```

#### TC-P15-02: Env permission groups cover all env permissions
```
GIVEN: ENV_PERMISSION_GROUPS
WHEN:  all group values are flattened
THEN:
  - Every permission in ENV_PERMISSIONS is in exactly one group
  - No duplicates, no missing
```

#### TC-P15-03: Correct permissions in each group
```
GIVEN: PROJECT_PERMISSION_GROUPS
THEN:
  "🚩 Flag Lifecycle"    contains "Create Flags", "Update Flags", "Archive Flags", "Update Client Side Availability"
  "📊 Metrics & Pipelines" contains "Manage Metrics", "Manage Release Pipelines", "View Project"
  "🤖 AI Configs"        contains "Create AI Configs", "Update AI Configs", "Delete AI Configs", "Manage AI Variations"
  "🔭 Observability"     contains all 7 observability permissions
```

### Group 2: Matrix Initialisation

#### TC-P15-04: Default matrix includes all permissions from all groups
```
GIVEN: create_default_project_matrix(["Developer", "QA"])
WHEN:  DataFrame is created
THEN:
  - columns include ALL permissions from ALL PROJECT_PERMISSION_GROUPS
  - View Project defaults to True
  - All other permissions default to False
```

#### TC-P15-05: Summary tab shows all columns
```
GIVEN: project_matrix DataFrame with permissions set
WHEN:  _render_project_summary() is called
THEN:
  - DataFrame displayed contains all permission columns
  - True values shown as "✅"
  - False values shown as "—"
```

### Group 3: Widget Key Uniqueness

#### TC-P15-06: No duplicate widget keys across tabs
```
GIVEN: 3 teams, 4 permission groups
WHEN:  all widget keys are generated across all tabs
THEN:
  - Every key is unique
  - Keys follow pattern: "proj_{group_key}_{team_idx}_{perm_idx}"
  - No Streamlit DuplicateWidgetID error
```

---

## Navigation

- [← README](./README.md)
- [Python Concepts →](./PYTHON_CONCEPTS.md)
