# Phase 5: Python & Streamlit Concepts

> Deep dive into concepts used in UI Modules

---

## Table of Contents

1. [Python Module System](#1-python-module-system)
2. [Streamlit Session State](#2-streamlit-session-state)
3. [Streamlit Callbacks](#3-streamlit-callbacks)
4. [Function Composition for UI](#4-function-composition-for-ui)
5. [Type Hints for Streamlit](#5-type-hints-for-streamlit)
6. [Context Managers in Streamlit](#6-context-managers-in-streamlit)
7. [Testing Streamlit Apps](#7-testing-streamlit-apps)
8. [Quick Reference Card](#8-quick-reference-card)

---

## 1. Python Module System

### What is a Module?

A **module** is simply a Python file (`.py`) that contains code you want to reuse. When you split `app.py` into multiple files, each file becomes a module.

### Package vs Module

```
# Module = single .py file
ui/setup_tab.py  ← This is a module

# Package = folder with __init__.py
ui/               ← This is a package
├── __init__.py   ← Makes it a package
├── setup_tab.py
├── matrix_tab.py
└── deploy_tab.py
```

### The `__init__.py` File

The `__init__.py` file serves two purposes:

1. **Marks the folder as a Python package** (required in Python < 3.3)
2. **Controls what gets exported** when someone imports the package

```python
# ui/__init__.py

# =============================================================================
# LESSON: Package Exports
# =============================================================================
# This file controls what's available when someone does:
#   from ui import render_setup_tab
#
# Without this file, they'd have to write:
#   from ui.setup_tab import render_setup_tab

from .setup_tab import render_setup_tab
from .matrix_tab import render_matrix_tab
from .deploy_tab import render_deploy_tab
from .reference_tab import render_reference_tab

# __all__ defines what's exported with "from ui import *"
# (Though "import *" is generally discouraged)
__all__ = [
    "render_setup_tab",
    "render_matrix_tab",
    "render_deploy_tab",
    "render_reference_tab",
]
```

### Relative vs Absolute Imports

```python
# =============================================================================
# LESSON: Import Styles
# =============================================================================

# RELATIVE IMPORT (within the same package)
# The dot (.) means "current package"
from .setup_tab import render_setup_tab      # Same package
from ..models import Team                     # Parent package

# ABSOLUTE IMPORT (full path from project root)
from ui.setup_tab import render_setup_tab
from models import Team

# BEST PRACTICE:
# - Use relative imports within a package (ui/__init__.py)
# - Use absolute imports in app.py and tests
```

### Import Patterns

```python
# Pattern 1: Import specific functions (PREFERRED)
from ui import render_setup_tab, render_matrix_tab

# Pattern 2: Import module and use dot notation
from ui import setup_tab
setup_tab.render_setup_tab()

# Pattern 3: Import everything (AVOID)
from ui import *  # Don't do this - unclear what's imported

# Pattern 4: Alias for long names
from ui.reference_tab import render_reference_tab as render_ref
```

---

## 2. Streamlit Session State

### The Problem: Script Reruns

```python
# =============================================================================
# LESSON: Why Session State Exists
# =============================================================================

# PROBLEM: Streamlit reruns the ENTIRE script on every interaction
# Without session state, variables reset every time!

# BAD: This resets to 0 on every button click
counter = 0
if st.button("Increment"):
    counter += 1  # Always goes 0 → 1
st.write(f"Count: {counter}")  # Always shows 1

# GOOD: Session state persists across reruns
if "counter" not in st.session_state:
    st.session_state.counter = 0

if st.button("Increment"):
    st.session_state.counter += 1  # Actually increments!

st.write(f"Count: {st.session_state.counter}")  # Shows correct count
```

### Accessing Session State

```python
# =============================================================================
# LESSON: Session State Access Patterns
# =============================================================================

# Two equivalent syntaxes:
st.session_state.customer_name = "Acme"      # Attribute style
st.session_state["customer_name"] = "Acme"   # Dictionary style

# Reading values
name = st.session_state.customer_name
name = st.session_state["customer_name"]
name = st.session_state.get("customer_name", "default")  # With default

# Checking if key exists
if "customer_name" in st.session_state:
    # Key exists
    pass

# Safe initialization pattern
if "customer_name" not in st.session_state:
    st.session_state.customer_name = ""
```

### Session State with Widgets

```python
# =============================================================================
# LESSON: Widget Keys and Session State
# =============================================================================

# Widgets can have a "key" parameter that links to session state
customer_name = st.text_input(
    "Customer Name",
    key="customer_name"  # Automatically synced with session_state
)

# Now st.session_state.customer_name is automatically updated!
# No need for manual assignment

# GOTCHA: You can't set session_state for a key that a widget uses
# This will ERROR:
st.session_state.customer_name = "Test"  # Error if widget has key="customer_name"
st.text_input("Name", key="customer_name")

# SOLUTION: Set default BEFORE creating widget, or use on_change callback
```

### Session State Across Tabs

```python
# =============================================================================
# LESSON: Cross-Tab Communication
# =============================================================================

# Session state is SHARED across all tabs!
# This is how tabs communicate

# In setup_tab.py:
def render_setup_tab():
    teams = st.data_editor(st.session_state.teams_df)
    st.session_state.teams_df = teams  # Save for other tabs

# In matrix_tab.py:
def render_matrix_tab():
    teams = st.session_state.teams_df  # Read from setup tab
    # Use teams to build matrix...
```

---

## 3. Streamlit Callbacks

### What are Callbacks?

Callbacks are functions that run when a widget changes, BEFORE the script reruns.

```python
# =============================================================================
# LESSON: Callback Basics
# =============================================================================

# WITHOUT callback: Value updates on NEXT rerun
name = st.text_input("Name", key="name")
st.write(f"Hello, {name}")  # Shows previous value on first interaction

# WITH callback: Function runs IMMEDIATELY when value changes
def on_name_change():
    # This runs BEFORE the script reruns
    st.session_state.greeting = f"Hello, {st.session_state.name}!"

st.text_input("Name", key="name", on_change=on_name_change)
st.write(st.session_state.get("greeting", ""))
```

### Callback Timing

```
┌──────────────────────────────────────────────────────────────────┐
│                    STREAMLIT EXECUTION FLOW                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  User clicks button                                               │
│         │                                                         │
│         ▼                                                         │
│  ┌─────────────────┐                                              │
│  │ Callback runs   │  ◄── Runs FIRST (if defined)                │
│  │ on_click=func   │                                              │
│  └────────┬────────┘                                              │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                              │
│  │ Script reruns   │  ◄── Entire app.py runs from top            │
│  │ from the top    │                                              │
│  └────────┬────────┘                                              │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────┐                                              │
│  │ UI updates      │  ◄── New state reflected in UI              │
│  └─────────────────┘                                              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Callback with Arguments

```python
# =============================================================================
# LESSON: Passing Arguments to Callbacks
# =============================================================================

# Using args parameter
def handle_click(team_name, action):
    st.session_state.message = f"{action}: {team_name}"

st.button(
    "Delete",
    on_click=handle_click,
    args=("Developer", "delete")  # Positional args as tuple
)

# Using kwargs parameter
st.button(
    "Delete",
    on_click=handle_click,
    kwargs={"team_name": "Developer", "action": "delete"}
)

# Using lambda (less preferred but works)
st.button(
    "Delete",
    on_click=lambda: handle_click("Developer", "delete")
)
```

### Common Callback Patterns

```python
# =============================================================================
# LESSON: Callback Patterns
# =============================================================================

# Pattern 1: Toggle boolean
def toggle_advanced():
    st.session_state.show_advanced = not st.session_state.get("show_advanced", False)

st.button("Toggle Advanced", on_click=toggle_advanced)

# Pattern 2: Reset form
def reset_form():
    st.session_state.customer_name = ""
    st.session_state.project_key = ""
    st.session_state.teams_df = DEFAULT_TEAMS.copy()

st.button("Reset", on_click=reset_form)

# Pattern 3: Validate on change
def validate_project_key():
    key = st.session_state.project_key
    if " " in key:
        st.session_state.project_key_error = "No spaces allowed"
    else:
        st.session_state.project_key_error = None

st.text_input("Project Key", key="project_key", on_change=validate_project_key)
```

---

## 4. Function Composition for UI

### Breaking Down Large UI Functions

```python
# =============================================================================
# LESSON: Function Composition
# =============================================================================

# BAD: One giant function with everything
def render_setup_tab():
    st.header("Setup")
    # 200 lines of customer info...
    # 200 lines of teams editor...
    # 200 lines of env groups editor...
    # Hard to read, hard to maintain!

# GOOD: Composed of smaller functions
def render_setup_tab():
    """Main entry point for Setup tab."""
    st.header("Step 1: Setup")

    _render_customer_info()
    _render_teams_editor()
    _render_env_groups_editor()


def _render_customer_info():
    """Render customer name and project key inputs."""
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Customer Name", key="customer_name")
    with col2:
        st.text_input("Project Key", key="project_key")


def _render_teams_editor():
    """Render the teams DataFrame editor."""
    st.subheader("Teams")
    # ... teams logic


def _render_env_groups_editor():
    """Render the environment groups editor."""
    st.subheader("Environment Groups")
    # ... env groups logic
```

### Private vs Public Functions

```python
# =============================================================================
# LESSON: Naming Conventions
# =============================================================================

# PUBLIC function (no underscore) - meant to be imported
def render_setup_tab():
    """This is the public API of this module."""
    pass

# PRIVATE function (single underscore) - internal use only
def _render_customer_info():
    """Helper function, not meant to be imported directly."""
    pass

# In __init__.py, only export public functions:
from .setup_tab import render_setup_tab  # Public only
# Don't export: _render_customer_info
```

### When to Extract a Function

```python
# =============================================================================
# LESSON: Function Extraction Rules
# =============================================================================

# Extract when:
# 1. Code block has a clear, single purpose
# 2. Code is reused in multiple places
# 3. Code block is > 20-30 lines
# 4. You can give it a meaningful name

# DON'T extract when:
# 1. It's only 3-5 lines
# 2. Extraction would need too many parameters
# 3. The logic is tightly coupled to surrounding code
```

---

## 5. Type Hints for Streamlit

### Why Type Hints?

```python
# =============================================================================
# LESSON: Type Hints Benefits
# =============================================================================

# WITHOUT type hints - what does this return?
def render_matrix_tab():
    pass

# WITH type hints - clear expectations
def render_matrix_tab() -> None:
    """Render the matrix tab. Returns nothing (side effects only)."""
    pass

# Type hints help:
# 1. Documentation - what types are expected
# 2. IDE autocomplete - better suggestions
# 3. Error catching - Pyright/mypy find bugs
```

### Common Streamlit Type Patterns

```python
# =============================================================================
# LESSON: Type Hints for Streamlit
# =============================================================================

from typing import Optional, List, Dict, Any
import pandas as pd

# Render functions return None (they have side effects)
def render_setup_tab() -> None:
    """Side effect: renders UI to the page."""
    pass

# Functions that create data
def create_default_matrix(teams: List[str]) -> pd.DataFrame:
    """Pure function: returns new DataFrame."""
    pass

# Functions that may return None
def get_validation_result() -> Optional[ValidationResult]:
    """Returns None if not yet validated."""
    return st.session_state.get("validation_result")

# Session state helper with type hint
def get_teams_df() -> pd.DataFrame:
    """Get teams DataFrame from session state."""
    return st.session_state.teams_df
```

### Type Hints for DataFrames

```python
# =============================================================================
# LESSON: DataFrame Type Hints
# =============================================================================

import pandas as pd
from typing import TypedDict

# Basic DataFrame type hint
def process_teams(df: pd.DataFrame) -> pd.DataFrame:
    pass

# More specific with TypedDict (optional, for documentation)
class TeamRow(TypedDict):
    Key: str
    Name: str
    Description: str

# Note: Pandas doesn't enforce these at runtime
# They're for documentation and IDE support
```

---

## 6. Context Managers in Streamlit

### What is a Context Manager?

```python
# =============================================================================
# LESSON: Context Managers
# =============================================================================

# Context managers use the "with" statement
# They handle setup and teardown automatically

# File example (classic Python)
with open("file.txt", "r") as f:
    content = f.read()
# File is automatically closed when exiting the "with" block

# Streamlit uses context managers for layout
with st.sidebar:
    st.write("This appears in sidebar")

with st.expander("Click to expand"):
    st.write("This is hidden until clicked")

with st.container():
    st.write("This is in a container")
```

### Streamlit Layout Context Managers

```python
# =============================================================================
# LESSON: Streamlit Layout
# =============================================================================

# Columns
col1, col2, col3 = st.columns(3)
with col1:
    st.write("Column 1")
with col2:
    st.write("Column 2")

# Tabs
tab1, tab2 = st.tabs(["First", "Second"])
with tab1:
    st.write("Tab 1 content")
with tab2:
    st.write("Tab 2 content")

# Expander (collapsible section)
with st.expander("Advanced Options", expanded=False):
    st.write("Hidden by default")

# Container (logical grouping)
with st.container():
    st.write("Grouped content")

# Sidebar
with st.sidebar:
    st.write("Sidebar content")

# Form (batch submissions)
with st.form("my_form"):
    name = st.text_input("Name")
    submitted = st.form_submit_button("Submit")
```

### Nesting Context Managers

```python
# =============================================================================
# LESSON: Nested Context Managers
# =============================================================================

# You can nest context managers
with st.expander("Settings"):
    col1, col2 = st.columns(2)
    with col1:
        st.checkbox("Option 1")
    with col2:
        st.checkbox("Option 2")

# Complex layout example
with st.container():
    st.header("Section")
    with st.expander("Details"):
        tab1, tab2 = st.tabs(["Info", "Settings"])
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                st.write("Left")
            with col2:
                st.write("Right")
```

---

## 7. Testing Streamlit Apps

### The Challenge

```python
# =============================================================================
# LESSON: Streamlit Testing Challenges
# =============================================================================

# Streamlit apps are tricky to test because:
# 1. They rely on session state (global state)
# 2. They render to a browser (side effects)
# 3. Widget interactions trigger full reruns

# Solutions:
# 1. Extract pure logic into separate functions (testable)
# 2. Use Streamlit's testing framework (AppTest)
# 3. Mock session state for unit tests
```

### Strategy 1: Extract Pure Functions

```python
# =============================================================================
# LESSON: Testable Code Extraction
# =============================================================================

# BAD: Logic mixed with UI (hard to test)
def render_matrix_tab():
    teams = st.session_state.teams_df["Name"].tolist()
    matrix = pd.DataFrame({"Team": teams})
    for perm in PERMISSIONS:
        matrix[perm] = False
    st.data_editor(matrix)

# GOOD: Pure function extracted (easy to test)
def create_default_matrix(teams: List[str], permissions: List[str]) -> pd.DataFrame:
    """Pure function - no Streamlit dependencies."""
    matrix = pd.DataFrame({"Team": teams})
    for perm in permissions:
        matrix[perm] = False
    return matrix

def render_matrix_tab():
    teams = st.session_state.teams_df["Name"].tolist()
    matrix = create_default_matrix(teams, PERMISSIONS)
    st.data_editor(matrix)

# Now you can test create_default_matrix without Streamlit!
def test_create_default_matrix():
    result = create_default_matrix(["Dev", "QA"], ["Read", "Write"])
    assert len(result) == 2
    assert "Read" in result.columns
```

### Strategy 2: Streamlit AppTest

```python
# =============================================================================
# LESSON: Streamlit AppTest
# =============================================================================

from streamlit.testing.v1 import AppTest

def test_setup_tab():
    """Test using Streamlit's testing framework."""
    # Load the app
    at = AppTest.from_file("app.py")
    at.run()

    # Check that elements exist
    assert len(at.text_input) >= 2  # Customer name, project key

    # Simulate user interaction
    at.text_input[0].set_value("Test Corp").run()

    # Check session state
    assert at.session_state.customer_name == "Test Corp"
```

### Strategy 3: Mock Session State

```python
# =============================================================================
# LESSON: Mocking Session State
# =============================================================================

import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_session_state():
    """Create a mock session state."""
    mock = MagicMock()
    mock.customer_name = "Test Corp"
    mock.project_key = "test-project"
    mock.teams_df = pd.DataFrame({
        "Key": ["dev"],
        "Name": ["Developer"],
        "Description": [""]
    })
    return mock

def test_with_mock_session_state(mock_session_state):
    """Test using mocked session state."""
    with patch("streamlit.session_state", mock_session_state):
        # Now st.session_state is mocked
        from ui.matrix_tab import create_matrix_from_session
        result = create_matrix_from_session()
        assert len(result) == 1
```

---

## 8. Quick Reference Card

### Module System

```python
# Package structure
ui/
├── __init__.py      # from .module import func
├── setup_tab.py
└── matrix_tab.py

# Import styles
from ui import render_setup_tab        # From package
from ui.setup_tab import some_helper   # Direct import
```

### Session State

```python
# Initialize
if "key" not in st.session_state:
    st.session_state.key = default_value

# Read
value = st.session_state.key
value = st.session_state.get("key", default)

# Write
st.session_state.key = new_value

# Widget auto-sync
st.text_input("Label", key="key")  # Syncs to session_state.key
```

### Callbacks

```python
# Basic callback
def on_click():
    st.session_state.clicked = True

st.button("Click", on_click=on_click)

# With arguments
st.button("Click", on_click=handler, args=(arg1,), kwargs={"key": val})
```

### Layout Context Managers

```python
with st.sidebar:        # Sidebar content
with st.expander(""):   # Collapsible
with st.container():    # Grouping
with st.form(""):       # Batch input

col1, col2 = st.columns(2)
tab1, tab2 = st.tabs(["A", "B"])
```

### Function Patterns

```python
# Public (exported)
def render_tab() -> None:
    _helper()

# Private (internal)
def _helper() -> None:
    pass

# Type hints
def func(df: pd.DataFrame) -> Optional[Result]:
    pass
```

### Testing

```python
# Extract pure functions for easy testing
def pure_logic(input: X) -> Y:  # No st.* calls
    return result

# Test pure functions
def test_pure_logic():
    assert pure_logic(x) == expected

# Use AppTest for integration
at = AppTest.from_file("app.py")
at.run()
```

---

## Next Steps

Now that you understand the concepts, proceed to [DESIGN.md](./DESIGN.md) to see how these are applied in Phase 5 implementation.
