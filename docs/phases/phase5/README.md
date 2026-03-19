# Phase 5: UI Modules

> **Status:** 📋 Planned
> **Goal:** Refactor monolithic app.py into modular UI components

---

## Quick Links

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, test cases, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Module system, session state, callbacks, testing |

---

## Overview

Phase 5 refactors the 1200+ line `app.py` into separate, maintainable UI modules. Each tab becomes its own module with clear responsibilities.

```
┌─────────────────────────────────────────────────────────────────┐
│                    BEFORE (Monolithic)                          │
├─────────────────────────────────────────────────────────────────┤
│  app.py (1200+ lines)                                           │
│    - Setup tab code                                              │
│    - Matrix tab code                                             │
│    - Deploy tab code                                             │
│    - Reference tab code                                          │
│    - All helpers mixed together                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AFTER (Modular)                              │
├─────────────────────────────────────────────────────────────────┤
│  app.py (~100 lines) ──► Orchestration only                     │
│  ui/                                                             │
│    ├── setup_tab.py (~200 lines)                                │
│    ├── matrix_tab.py (~300 lines)                               │
│    ├── deploy_tab.py (~300 lines)                               │
│    └── reference_tab.py (~400 lines)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files to Create

| File | Purpose | Lines (Est.) |
|------|---------|--------------|
| `ui/__init__.py` | Package exports | ~20 |
| `ui/setup_tab.py` | Tab 1: Customer, teams, envs | ~200 |
| `ui/matrix_tab.py` | Tab 2: Permission matrices | ~300 |
| `ui/deploy_tab.py` | Tab 3: Validate, generate, save | ~300 |
| `ui/reference_tab.py` | Tab 4: RBAC reference guide | ~400 |
| `tests/test_ui_modules.py` | Unit tests | ~200 |

---

## Module Interface

Each tab module exports a single render function:

```python
# ui/setup_tab.py
def render_setup_tab() -> None:
    """Render the Setup tab UI."""
    st.header("Step 1: Setup")
    # ... tab content

# Usage in app.py
from ui import render_setup_tab

with tab1:
    render_setup_tab()
```

---

## Session State Keys

All tabs share state through `st.session_state`:

| Key | Type | Set By | Used By |
|-----|------|--------|---------|
| `customer_name` | `str` | Setup | Deploy |
| `project_key` | `str` | Setup | Deploy |
| `teams_df` | `DataFrame` | Setup | Matrix, Deploy |
| `env_groups_df` | `DataFrame` | Setup | Matrix, Deploy |
| `project_matrix_df` | `DataFrame` | Matrix | Deploy |
| `env_matrix_df` | `DataFrame` | Matrix | Deploy |
| `validation_result` | `ValidationResult` | Deploy | Deploy |
| `deploy_payload` | `DeployPayload` | Deploy | Deploy |

---

## Key Concepts

| Concept | Purpose | Example |
|---------|---------|---------|
| Python Modules | Code organization | `from ui import render_setup_tab` |
| Session State | Cross-tab data sharing | `st.session_state.teams_df` |
| Callbacks | Handle interactions | `on_change=validate_key` |
| Context Managers | UI layout | `with st.expander():` |
| Type Hints | Documentation | `def func() -> None:` |

---

## Checklist

### Documentation
- [x] Create `docs/phases/phase5/` folder
- [x] Create `DESIGN.md` with HLD, DLD, pseudo logic
- [x] Create `PYTHON_CONCEPTS.md`
- [x] Create `README.md`

### Implementation
- [ ] Create `ui/__init__.py`
- [ ] Create `ui/setup_tab.py`
- [ ] Create `ui/matrix_tab.py`
- [ ] Create `ui/deploy_tab.py`
- [ ] Create `ui/reference_tab.py`
- [ ] Refactor `app.py` to use modules
- [ ] Create `tests/test_ui_modules.py`
- [ ] Run tests and verify
- [ ] Update app to ensure it works

### Verification
- [ ] All tabs render correctly
- [ ] Session state persists across tabs
- [ ] Matrix syncs with team changes
- [ ] Validation works
- [ ] Generate/Save/Download works
- [ ] All tests pass

---

## Navigation

| Previous | Up | Next |
|----------|------|------|
| [Phase 4: Validation](../phase4/) | [All Phases](../) | [Phase 6: LD Client](../phase6/) |
