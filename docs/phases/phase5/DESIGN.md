# Phase 5: UI Modules

> **Status:** 📋 Planned
> **Goal:** Refactor monolithic app.py into modular UI components
> **Dependencies:** Phases 1-4 (models, storage, payload_builder, validation)

---

## Related Documents

| Document | Description |
|----------|-------------|
| [README.md](./README.md) | Quick overview, checklist, status |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Streamlit patterns, callbacks, session state |
| [Phase 4: Validation](../phase4/) | Previous phase |
| [Phase 6: LD Client](../phase6/) | Next phase (planned) |

---

## Table of Contents

1. [High-Level Design (HLD)](#high-level-design-hld)
2. [Detailed Low-Level Design (DLD)](#detailed-low-level-design-dld)
3. [Pseudo Logic](#pseudo-logic)
4. [Test Cases](#test-cases)
5. [Implementation Plan](#implementation-plan)

---

## High-Level Design (HLD)

### What Are We Building?

We're refactoring the monolithic `app.py` (1200+ lines) into separate, maintainable UI modules. Each tab becomes its own module with clear responsibilities.

### Why Modularize?

| Problem (Current) | Solution (Phase 5) |
|-------------------|-------------------|
| 1200+ lines in single file | ~200-300 lines per module |
| Hard to navigate | Clear file boundaries |
| Merge conflicts likely | Team can work on different tabs |
| Difficult to test | Each module testable in isolation |
| Cognitive overload | Focus on one tab at a time |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           app.py (Main Entry)                        │
│                         ~100 lines - orchestration only              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│   │ setup_tab   │  │ matrix_tab  │  │ deploy_tab  │  │ reference │ │
│   │    .py      │  │    .py      │  │    .py      │  │  _tab.py  │ │
│   │             │  │             │  │             │  │           │ │
│   │ - Customer  │  │ - Project   │  │ - Validate  │  │ - Diagrams│ │
│   │ - Teams     │  │   Matrix    │  │ - Generate  │  │ - Terms   │ │
│   │ - Env Grps  │  │ - Env       │  │ - Save/Load │  │ - Examples│ │
│   │             │  │   Matrix    │  │ - Download  │  │           │ │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘ │
│          │                │                │                │       │
│          └────────────────┴────────────────┴────────────────┘       │
│                                    │                                 │
│                          st.session_state                            │
│                    (shared state across all tabs)                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SESSION STATE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  customer_name ─────────────────────────────────────────────────►   │
│  project_key ───────────────────────────────────────────────────►   │
│                                                                      │
│  teams_df ──────────────┬───────────────────────────────────────►   │
│                         │                                            │
│  env_groups_df ─────────┼───────────────────────────────────────►   │
│                         │                                            │
│                         ▼                                            │
│  project_matrix_df ◄────┴─────────────────────────────────────►     │
│  env_matrix_df ◄──────────────────────────────────────────────►     │
│                                                                      │
│  validation_result ◄──────────────────────────────────────────      │
│  deploy_payload ◄─────────────────────────────────────────────      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
    ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
    │ Setup   │          │ Matrix  │          │ Deploy  │
    │ Tab     │          │ Tab     │          │ Tab     │
    └─────────┘          └─────────┘          └─────────┘
```

### Module Responsibilities

| Module | Lines (Est.) | Responsibilities |
|--------|--------------|------------------|
| `app.py` | ~100 | Page config, sidebar, tab creation, imports |
| `setup_tab.py` | ~200 | Customer info, teams editor, env groups editor |
| `matrix_tab.py` | ~300 | Project matrix, env matrix, matrix sync logic |
| `deploy_tab.py` | ~300 | Validation, payload generation, save/download |
| `reference_tab.py` | ~400 | RBAC diagrams, terms, examples (static content) |
| `components.py` | ~100 | Shared UI components (optional) |

---

## Detailed Low-Level Design (DLD)

### File Structure

```
rbac-builder/
├── app.py                          # Main entry (slimmed down)
├── ui/
│   ├── __init__.py                 # Exports render functions
│   ├── setup_tab.py                # Tab 1: Setup
│   ├── matrix_tab.py               # Tab 2: Design Matrix
│   ├── deploy_tab.py               # Tab 3: Deploy
│   ├── reference_tab.py            # Tab 4: Reference Guide
│   └── components.py               # Shared UI components (optional)
```

### ui/__init__.py

```python
"""
UI modules for RBAC Builder.

Each module exports a render function that draws one tab.
"""

from .setup_tab import render_setup_tab
from .matrix_tab import render_matrix_tab
from .deploy_tab import render_deploy_tab
from .reference_tab import render_reference_tab

__all__ = [
    "render_setup_tab",
    "render_matrix_tab",
    "render_deploy_tab",
    "render_reference_tab",
]
```

### Module Interface Pattern

Each tab module follows the same pattern:

```python
# ui/setup_tab.py

import streamlit as st
import pandas as pd
from typing import Optional

def render_setup_tab() -> None:
    """
    Render the Setup tab UI.

    Reads from and writes to st.session_state:
    - customer_name: str
    - project_key: str
    - teams_df: pd.DataFrame
    - env_groups_df: pd.DataFrame
    """
    st.header("Step 1: Setup")
    # ... tab content
```

### setup_tab.py Design

| Function | Purpose | Session State |
|----------|---------|---------------|
| `render_setup_tab()` | Main entry point | Reads/writes all setup state |
| `_render_customer_info()` | Customer name, project key inputs | customer_name, project_key |
| `_render_teams_editor()` | Teams DataFrame editor | teams_df |
| `_render_env_groups_editor()` | Env groups DataFrame editor | env_groups_df |

**Session State Keys Used:**

| Key | Type | Default |
|-----|------|---------|
| `customer_name` | `str` | `""` |
| `project_key` | `str` | `""` |
| `teams_df` | `pd.DataFrame` | Default teams |
| `env_groups_df` | `pd.DataFrame` | Default env groups |

### matrix_tab.py Design

| Function | Purpose | Session State |
|----------|---------|---------------|
| `render_matrix_tab()` | Main entry point | Reads teams/envs, writes matrices |
| `_render_project_matrix()` | Project-level permissions | project_matrix_df |
| `_render_env_matrix()` | Environment-level permissions | env_matrix_df |
| `_sync_matrix_with_teams()` | Update matrix when teams change | Both matrices |
| `_create_default_project_matrix()` | Generate default project matrix | - |
| `_create_default_env_matrix()` | Generate default env matrix | - |

**Session State Keys Used:**

| Key | Type | Default |
|-----|------|---------|
| `project_matrix_df` | `pd.DataFrame` | Generated from teams |
| `env_matrix_df` | `pd.DataFrame` | Generated from teams × envs |

### deploy_tab.py Design

| Function | Purpose | Session State |
|----------|---------|---------------|
| `render_deploy_tab()` | Main entry point | Reads all, writes validation/payload |
| `_render_validation_section()` | Show validation results | validation_result |
| `_render_generate_section()` | Generate payloads button | deploy_payload |
| `_render_payload_preview()` | Show generated JSON | deploy_payload |
| `_render_save_download()` | Save/download buttons | - |

**Session State Keys Used:**

| Key | Type | Default |
|-----|------|---------|
| `validation_result` | `ValidationResult` | `None` |
| `deploy_payload` | `DeployPayload` | `None` |

### reference_tab.py Design

| Function | Purpose | Session State |
|----------|---------|---------------|
| `render_reference_tab()` | Main entry point | None (read-only) |
| `_render_hierarchy_diagram()` | RBAC hierarchy ASCII art | - |
| `_render_key_terms()` | Terminology table | - |
| `_render_members_teams()` | Members & teams explanation | - |
| `_render_builtin_roles()` | Built-in roles table | - |
| `_render_policies_section()` | Policy JSON examples | - |
| `_render_resources_section()` | Resource string patterns | - |
| `_render_actions_reference()` | All LD actions reference | - |

### app.py (Refactored)

```python
"""
RBAC Builder - Main Application Entry Point
============================================

This is the main entry point. Each tab is rendered by a separate module.
"""

import streamlit as st

# UI modules
from ui import (
    render_setup_tab,
    render_matrix_tab,
    render_deploy_tab,
    render_reference_tab,
)

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="RBAC Builder",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.title("🔐 RBAC Builder")
    # ... sidebar content (settings, cloud warning, etc.)

# =============================================================================
# MAIN TABS
# =============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 1. Setup",
    "📊 2. Design Matrix",
    "🚀 3. Deploy",
    "📚 4. Reference Guide"
])

with tab1:
    render_setup_tab()

with tab2:
    render_matrix_tab()

with tab3:
    render_deploy_tab()

with tab4:
    render_reference_tab()
```

---

## Pseudo Logic

### render_setup_tab()

```
FUNCTION render_setup_tab():
    # Header
    DISPLAY "Step 1: Setup" header

    # Customer Info Section
    CREATE two columns (col1, col2)
    IN col1:
        INPUT customer_name from text_input
        SAVE to session_state.customer_name
    IN col2:
        INPUT project_key from text_input
        SAVE to session_state.project_key

    # Teams Section
    DISPLAY "Teams" subheader
    DISPLAY info about teams

    # Initialize teams_df if not exists
    IF "teams_df" NOT IN session_state:
        session_state.teams_df = DEFAULT_TEAMS

    # Show teams editor
    edited_teams = DATA_EDITOR(session_state.teams_df)
    session_state.teams_df = edited_teams

    # Environment Groups Section
    DISPLAY "Environment Groups" subheader

    # Initialize env_groups_df if not exists
    IF "env_groups_df" NOT IN session_state:
        session_state.env_groups_df = DEFAULT_ENV_GROUPS

    # Show env groups editor
    edited_envs = DATA_EDITOR(session_state.env_groups_df)
    session_state.env_groups_df = edited_envs
```

### render_matrix_tab()

```
FUNCTION render_matrix_tab():
    # Header
    DISPLAY "Step 2: Design Permission Matrix" header

    # Check prerequisites
    IF teams_df is empty OR env_groups_df is empty:
        DISPLAY warning "Complete Setup tab first"
        RETURN

    # Get current teams and envs
    teams = GET team names from session_state.teams_df
    envs = GET env keys from session_state.env_groups_df

    # ─────────────────────────────────────────────────
    # PROJECT-LEVEL MATRIX
    # ─────────────────────────────────────────────────
    DISPLAY "Project-Level Permissions" subheader

    # Initialize or sync project matrix
    IF "project_matrix_df" NOT IN session_state:
        session_state.project_matrix_df = create_default_project_matrix(teams)
    ELSE:
        session_state.project_matrix_df = sync_matrix_with_teams(
            session_state.project_matrix_df,
            teams
        )

    # Show project matrix editor
    edited_project = DATA_EDITOR(
        session_state.project_matrix_df,
        disabled=["Team"],  # Team column not editable
        num_rows="fixed"    # Can't add/remove rows
    )
    session_state.project_matrix_df = edited_project

    # ─────────────────────────────────────────────────
    # ENVIRONMENT-LEVEL MATRIX
    # ─────────────────────────────────────────────────
    DISPLAY "Environment-Level Permissions" subheader

    # Initialize or sync env matrix
    IF "env_matrix_df" NOT IN session_state:
        session_state.env_matrix_df = create_default_env_matrix(teams, envs)
    ELSE:
        session_state.env_matrix_df = sync_env_matrix(
            session_state.env_matrix_df,
            teams,
            envs
        )

    # Show env matrix editor
    edited_env = DATA_EDITOR(
        session_state.env_matrix_df,
        disabled=["Team", "Environment"],
        num_rows="fixed"
    )
    session_state.env_matrix_df = edited_env


FUNCTION create_default_project_matrix(teams: List[str]) -> DataFrame:
    RETURN DataFrame with:
        - "Team" column = teams
        - Permission columns = all False


FUNCTION create_default_env_matrix(teams: List[str], envs: List[str]) -> DataFrame:
    rows = []
    FOR each team IN teams:
        FOR each env IN envs:
            rows.append({
                "Team": team,
                "Environment": env,
                ...permission columns: False
            })
    RETURN DataFrame(rows)


FUNCTION sync_matrix_with_teams(matrix_df, current_teams) -> DataFrame:
    existing_teams = matrix_df["Team"].tolist()

    # Remove rows for deleted teams
    matrix_df = matrix_df[matrix_df["Team"].isin(current_teams)]

    # Add rows for new teams
    FOR team IN current_teams:
        IF team NOT IN existing_teams:
            new_row = {"Team": team, ...all permissions: False}
            matrix_df = matrix_df.append(new_row)

    RETURN matrix_df
```

### render_deploy_tab()

```
FUNCTION render_deploy_tab():
    # Header
    DISPLAY "Step 3: Review & Deploy" header

    # ─────────────────────────────────────────────────
    # VALIDATION SECTION
    # ─────────────────────────────────────────────────
    DISPLAY "Configuration Validation" subheader

    # Run validation
    validator = ConfigValidator(
        customer_name=session_state.customer_name,
        project_key=session_state.project_key,
        teams_df=session_state.teams_df,
        env_groups_df=session_state.env_groups_df,
        project_matrix_df=session_state.project_matrix_df,
        env_matrix_df=session_state.env_matrix_df
    )
    result = validator.validate()
    session_state.validation_result = result

    # Display validation status
    IF result.is_valid:
        DISPLAY success "Configuration is valid!"
    ELSE:
        DISPLAY error with error count
        FOR each error IN result.errors:
            DISPLAY error message with suggestion

    IF result.warning_count > 0:
        FOR each warning IN result.warnings:
            DISPLAY warning message

    # ─────────────────────────────────────────────────
    # GENERATE SECTION
    # ─────────────────────────────────────────────────
    DISPLAY "Generate Payloads" subheader

    # Generate button (disabled if invalid)
    IF BUTTON("Generate Payloads", disabled=NOT result.is_valid):
        builder = PayloadBuilder(
            customer_name=session_state.customer_name,
            project_key=session_state.project_key,
            teams_df=session_state.teams_df,
            env_groups_df=session_state.env_groups_df,
            project_matrix_df=session_state.project_matrix_df,
            env_matrix_df=session_state.env_matrix_df
        )
        payload = builder.build()
        session_state.deploy_payload = payload
        DISPLAY success "Payloads generated!"

    # ─────────────────────────────────────────────────
    # PAYLOAD PREVIEW
    # ─────────────────────────────────────────────────
    IF session_state.deploy_payload is not None:
        DISPLAY "Generated Payloads" subheader

        # Show tabs for different views
        role_tab, team_tab, full_tab = TABS(["Roles", "Teams", "Full"])

        IN role_tab:
            DISPLAY JSON of payload.roles
        IN team_tab:
            DISPLAY JSON of payload.teams
        IN full_tab:
            DISPLAY full payload JSON

    # ─────────────────────────────────────────────────
    # SAVE & DOWNLOAD
    # ─────────────────────────────────────────────────
    DISPLAY "Save & Export" subheader

    col1, col2 = COLUMNS(2)

    IN col1:
        IF BUTTON("Save Configuration"):
            storage = StorageService()
            config = build_config_from_session()
            storage.save(config)
            DISPLAY success "Saved!"

    IN col2:
        IF payload exists:
            DOWNLOAD_BUTTON(
                label="Download JSON",
                data=payload.to_json(),
                filename=f"{project_key}-rbac.json"
            )
```

### render_reference_tab()

```
FUNCTION render_reference_tab():
    # Header
    DISPLAY "LaunchDarkly RBAC Reference Guide" header
    DISPLAY subtitle

    # All content in collapsible expanders
    WITH EXPANDER("How It All Connects", expanded=True):
        DISPLAY ASCII hierarchy diagram
        DISPLAY flow explanation

    WITH EXPANDER("Key Terms & Definitions"):
        DISPLAY terminology table

    WITH EXPANDER("Members & Teams"):
        DISPLAY members explanation
        DISPLAY teams explanation with comparison table

    WITH EXPANDER("Built-in Roles"):
        DISPLAY roles table (Reader, Writer, Admin, Owner)

    WITH EXPANDER("Policies (JSON Structure)"):
        DISPLAY policy JSON example
        DISPLAY evaluation rules diagram

    WITH EXPANDER("Resources"):
        DISPLAY resource string patterns
        DISPLAY examples table

    WITH EXPANDER("Actions Reference"):
        DISPLAY all available actions grouped by category
```

---

## Test Cases

### Test File Structure

```
tests/
├── test_ui_modules.py        # All UI module tests
└── conftest.py               # Shared fixtures
```

### test_ui_modules.py Test Cases

#### Setup Tab Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| ST-01 | `test_render_setup_tab_initializes_session_state` | Verify session state keys created |
| ST-02 | `test_setup_tab_customer_name_saved` | Customer name saves to session state |
| ST-03 | `test_setup_tab_project_key_saved` | Project key saves to session state |
| ST-04 | `test_setup_tab_teams_df_default` | Default teams DataFrame created |
| ST-05 | `test_setup_tab_env_groups_df_default` | Default env groups created |
| ST-06 | `test_setup_tab_teams_editable` | Teams can be edited |
| ST-07 | `test_setup_tab_env_groups_editable` | Env groups can be edited |

#### Matrix Tab Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| MT-01 | `test_matrix_tab_requires_setup` | Shows warning if setup incomplete |
| MT-02 | `test_project_matrix_created_from_teams` | Matrix rows match teams |
| MT-03 | `test_project_matrix_has_permission_columns` | All permission columns present |
| MT-04 | `test_env_matrix_created_from_teams_envs` | Rows = teams × envs |
| MT-05 | `test_env_matrix_has_permission_columns` | All env permission columns present |
| MT-06 | `test_matrix_syncs_when_team_added` | New team gets matrix row |
| MT-07 | `test_matrix_syncs_when_team_removed` | Removed team loses matrix row |
| MT-08 | `test_matrix_syncs_when_env_added` | New env gets matrix rows |
| MT-09 | `test_project_matrix_team_column_disabled` | Team column not editable |
| MT-10 | `test_env_matrix_team_env_columns_disabled` | Team/Env columns not editable |

#### Deploy Tab Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| DT-01 | `test_deploy_tab_runs_validation` | Validation runs on render |
| DT-02 | `test_deploy_tab_shows_errors` | Errors displayed to user |
| DT-03 | `test_deploy_tab_shows_warnings` | Warnings displayed to user |
| DT-04 | `test_deploy_tab_generate_disabled_if_invalid` | Button disabled when errors |
| DT-05 | `test_deploy_tab_generate_enabled_if_valid` | Button enabled when valid |
| DT-06 | `test_deploy_tab_generates_payload` | Payload created on click |
| DT-07 | `test_deploy_tab_shows_payload_preview` | JSON preview displayed |
| DT-08 | `test_deploy_tab_save_creates_file` | Save button creates file |
| DT-09 | `test_deploy_tab_download_button_present` | Download button shown |

#### Reference Tab Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| RT-01 | `test_reference_tab_renders` | Tab renders without error |
| RT-02 | `test_reference_tab_has_hierarchy_section` | Hierarchy diagram present |
| RT-03 | `test_reference_tab_has_terms_section` | Terms section present |
| RT-04 | `test_reference_tab_has_roles_section` | Roles section present |
| RT-05 | `test_reference_tab_has_policies_section` | Policies section present |
| RT-06 | `test_reference_tab_has_resources_section` | Resources section present |

#### Integration Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| IT-01 | `test_full_workflow_setup_to_deploy` | Complete flow works |
| IT-02 | `test_session_state_shared_across_tabs` | State persists between tabs |
| IT-03 | `test_matrix_updates_reflect_in_deploy` | Matrix changes affect payload |

### Test Implementation Notes

```python
# tests/test_ui_modules.py

"""
Tests for Phase 5: UI Modules
=============================

Tests for setup_tab, matrix_tab, deploy_tab, reference_tab.

Note: Streamlit UI testing requires special handling.
We use streamlit.testing.v1 for component testing.

Run with: pytest tests/test_ui_modules.py -v
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

# For Streamlit testing (if available)
try:
    from streamlit.testing.v1 import AppTest
    STREAMLIT_TESTING_AVAILABLE = True
except ImportError:
    STREAMLIT_TESTING_AVAILABLE = False


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_session_state():
    """Create mock session state with default values."""
    return {
        "customer_name": "Test Corp",
        "project_key": "test-project",
        "teams_df": pd.DataFrame({
            "Key": ["dev", "qa"],
            "Name": ["Developer", "QA Engineer"],
            "Description": ["", ""]
        }),
        "env_groups_df": pd.DataFrame({
            "Key": ["Test", "Production"],
            "Critical": [False, True]
        }),
        "project_matrix_df": None,
        "env_matrix_df": None,
        "validation_result": None,
        "deploy_payload": None,
    }


# =============================================================================
# Setup Tab Tests
# =============================================================================

class TestSetupTab:
    """Tests for setup_tab module."""

    def test_render_setup_tab_initializes_session_state(self):
        """Test that session state keys are created."""
        # This would use Streamlit's testing framework
        pass

    def test_setup_tab_default_teams_created(self, mock_session_state):
        """Test default teams DataFrame is created."""
        assert "teams_df" in mock_session_state
        assert len(mock_session_state["teams_df"]) > 0


# =============================================================================
# Matrix Tab Tests
# =============================================================================

class TestMatrixTab:
    """Tests for matrix_tab module."""

    def test_create_default_project_matrix(self):
        """Test project matrix creation from teams."""
        from ui.matrix_tab import create_default_project_matrix

        teams = ["Developer", "QA Engineer"]
        matrix = create_default_project_matrix(teams)

        assert len(matrix) == 2
        assert list(matrix["Team"]) == teams

    def test_create_default_env_matrix(self):
        """Test env matrix creation from teams × envs."""
        from ui.matrix_tab import create_default_env_matrix

        teams = ["Developer", "QA"]
        envs = ["Test", "Production"]
        matrix = create_default_env_matrix(teams, envs)

        # Should have teams × envs rows
        assert len(matrix) == 4


# =============================================================================
# Deploy Tab Tests
# =============================================================================

class TestDeployTab:
    """Tests for deploy_tab module."""

    def test_validation_runs_on_render(self, mock_session_state):
        """Test that validation is triggered."""
        # Would mock ConfigValidator and verify it's called
        pass


# =============================================================================
# Reference Tab Tests
# =============================================================================

class TestReferenceTab:
    """Tests for reference_tab module."""

    def test_reference_tab_renders_without_error(self):
        """Test that reference tab renders."""
        # Static content, mainly smoke test
        pass
```

---

## Implementation Plan

### Step-by-Step Order

| Step | Task | Files | Estimated Lines |
|------|------|-------|-----------------|
| 1 | Create `ui/` folder structure | `ui/__init__.py` | 20 |
| 2 | Extract setup tab | `ui/setup_tab.py` | 200 |
| 3 | Extract matrix tab | `ui/matrix_tab.py` | 300 |
| 4 | Extract deploy tab | `ui/deploy_tab.py` | 300 |
| 5 | Extract reference tab | `ui/reference_tab.py` | 400 |
| 6 | Refactor app.py | `app.py` | 100 |
| 7 | Create shared components (optional) | `ui/components.py` | 100 |
| 8 | Write tests | `tests/test_ui_modules.py` | 200 |
| 9 | Verify integration | - | - |

### Python Concepts Used

| Concept | Where Used | Why |
|---------|------------|-----|
| Module imports | All files | Code organization |
| Function composition | Tab modules | Break down UI into functions |
| Session state | All tabs | Cross-tab data sharing |
| Type hints | Function signatures | Documentation, IDE support |
| Docstrings | All public functions | Self-documenting code |
| Callbacks | Data editors | Handle user interactions |
| Context managers | `with st.expander()` | Clean UI grouping |

### Checklist

- [ ] Create `ui/__init__.py`
- [ ] Create `ui/setup_tab.py`
- [ ] Create `ui/matrix_tab.py`
- [ ] Create `ui/deploy_tab.py`
- [ ] Create `ui/reference_tab.py`
- [ ] Refactor `app.py` to use modules
- [ ] Create `tests/test_ui_modules.py`
- [ ] Run tests and verify
- [ ] Update CLAUDE.md with Phase 5 status

---

## Navigation

| Previous | Up | Next |
|----------|------|------|
| [Phase 4: Validation](../phase4/) | [All Phases](../) | [Phase 6: LD Client](../phase6/) |
