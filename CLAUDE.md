# CLAUDE.md - RBAC Builder Project

## Project Overview

This is the RBAC Builder for LaunchDarkly - a Python/Streamlit application that allows Solution Architects to design RBAC policies through a UI matrix interface.

## Source of Truth for LaunchDarkly Actions

**CRITICAL:** When making ANY changes to roles, teams, actions, or permission mappings, ALWAYS reference these two authoritative sources:

### 1. ps-terraform-private Repository
Location: `/Users/arifshaikh/Documents/GitHub/RBAC/ps-terraform-private/`

This repository contains the official Terraform modules for LaunchDarkly roles:
- `roles/flag-lifecycle/per-project/` - Project-level role modules
- `roles/flag-lifecycle/per-environment/` - Environment-level role modules
- `CLAUDE.md` - Contains all available role toggles and patterns

Use this to verify:
- Which actions belong to which permission
- Project vs environment scope for each action
- Role naming conventions and patterns

### 2. Gonfalon Repository
Location: `/Users/arifshaikh/Documents/GitHub/RBAC/gonfalon/`

This is LaunchDarkly's internal codebase containing official action definitions:
- `internal/roles/action.go` - Contains ALL official LaunchDarkly action identifiers

Use this to verify:
- Exact action names (e.g., `createFlag`, `updateAIConfigTargeting`)
- Valid actions for each resource type
- New actions added to LaunchDarkly

### Verification Checklist

Before modifying `core/ld_actions.py` or `ui/matrix_tab.py`:
- [ ] Check ps-terraform-private for the correct action groupings
- [ ] Verify action names against Gonfalon's `action.go`
- [ ] Ensure project vs environment scope matches Terraform modules
- [ ] Run tests after changes: `pytest tests/ -v`

## Code Navigation

- Prefer using LSP tools over grep/search for code navigation when available
- Use LSP for: jump to definition, find references, get type information, list symbols
- LSP provides more accurate results than text-based search for understanding code structure
- Pyright is configured for type checking

## Python Development

- Python 3.10+ required
- Use Pyright for type checking and code intelligence
- All Python code should have type hints where practical
- Use dataclasses for data models
- Follow PEP 8 style guidelines

## Educational Coding Style

**IMPORTANT:** The user is learning Python and Streamlit. When writing code:

1. **Add lesson comments** - Mark key concepts with clear headers like:
   ```python
   # =============================================================================
   # LESSON: Data Classes
   # =============================================================================
   # Dataclasses automatically generate __init__, __repr__, etc.
   ```

2. **Explain "why" not just "what"** - Add comments that teach:
   ```python
   # We use @dataclass to avoid writing boilerplate __init__ methods
   # The frozen=True makes instances immutable (can't change after creation)
   @dataclass(frozen=True)
   class Permission:
       ...
   ```

3. **Highlight Python patterns** - Point out idioms and best practices:
   ```python
   # List comprehension - Pythonic way to transform lists
   keys = [item.key for item in items]

   # Dictionary unpacking - common pattern for merging dicts
   merged = {**defaults, **overrides}
   ```

4. **Mark Streamlit-specific concepts** - Explain UI framework features:
   ```python
   # st.session_state persists data across reruns (widget interactions)
   # Without this, variables reset every time the user clicks something
   ```

5. **Note common gotchas** - Warn about tricky parts:
   ```python
   # GOTCHA: Streamlit reruns the entire script on every interaction
   # That's why we use session_state to preserve data
   ```

This helps the user learn while building the project together.

## Project Structure

```
rbac-builder/
├── app.py                    # Main entry point
├── models/                   # Data models (dataclasses)
├── core/                     # Constants and permission mappings
├── services/                 # Business logic
│   ├── ld_client.py         # LaunchDarkly API client
│   ├── storage.py           # Config persistence
│   ├── payload_builder.py   # Matrix → JSON transformation
│   ├── validation.py        # Config validation
│   └── deployer.py          # Deployment execution
├── ui/                       # Streamlit UI
│   ├── setup_tab.py         # Stage 1: Setup
│   ├── matrix_tab.py        # Stage 2: Matrix
│   └── deploy_tab.py        # Stage 3: Deploy
├── configs/                  # Saved customer configurations
└── templates/                # Starter templates
```

## Key Files

- `RBAC_BUILDER_DESIGN.md` - Complete design document with architecture details
- `docs/RBAC_CONCEPTS.md` - RBAC terminology and concepts reference
- `docs/phases/` - Implementation phase documentation (HLD, DLD, concepts)
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project configuration

## Documentation Maintenance

**IMPORTANT:** When making significant design or architectural changes:

1. **Update `RBAC_BUILDER_DESIGN.md`** - Document any changes to:
   - UI structure (tabs, sections, workflows)
   - Data flow (session state, cross-tab communication)
   - New features or components
   - Architecture decisions

2. **Update `docs/RBAC_CONCEPTS.md`** - If adding new RBAC terminology or concepts

3. **Keep diagrams current** - Update ASCII diagrams when UI structure changes

4. **Add implementation notes** - Document the "how" and "why" of implementation choices

This ensures the design document stays in sync with the actual implementation.

## Phase Documentation Requirements

**IMPORTANT:** Before starting implementation of ANY phase, create the following documentation in `docs/phases/phase{N}/`:

### Required Documents for Each Phase

```
docs/phases/phase{N}/
├── README.md              # Quick overview, checklist, status
├── DESIGN.md              # HLD, DLD, pseudo logic, implementation plan
└── PYTHON_CONCEPTS.md     # Deep dive into Python concepts used
```

### DESIGN.md Structure

Each DESIGN.md must include:

1. **Header** with phase number, status, goal, dependencies
2. **Related Documents** table linking to other docs
3. **High-Level Design (HLD)**
   - What are we building and why?
   - Architecture diagram showing where it fits
   - Data flow diagrams
   - Core features table
4. **Detailed Low-Level Design (DLD)**
   - File structure
   - Class/function designs with attribute tables
   - Method signatures
   - Error handling approach
   - Data formats (JSON schema, etc.)
5. **Pseudo Logic**
   - Step-by-step pseudo code for each major function
   - Integration examples with other components
6. **Test Cases**
   - Grouped by feature area (e.g., Group 1: Core Logic, Group 2: Edge Cases)
   - Each test case must have: ID (e.g., TC-XX-01), GIVEN/WHEN/THEN format
   - Cover: happy path, edge cases, error handling, integration
   - Specify the test file name (e.g., `tests/test_feature.py`)
7. **Implementation Plan**
   - Step-by-step implementation order
   - Python concepts table
   - Estimated lessons list
8. **Learning Resources** section with links
9. **Navigation** footer

### PYTHON_CONCEPTS.md Structure

Each concepts doc must include:

1. **Table of Contents** with numbered sections
2. **Each concept section** with:
   - Clear explanation
   - Code examples (before/after, good/bad)
   - When to use / when not to use
   - Common pitfalls
3. **Quick Reference Card** at the end
4. **Next Steps** linking to DESIGN.md

### Why This Matters

- User is learning Python - documentation helps understanding
- Planning before coding prevents rework
- Consistent structure makes it easy to navigate
- Pseudo logic validates approach before implementation

## Test Requirements for Each Phase

**CRITICAL:** Every phase MUST have corresponding test cases. Tests are NOT optional.

### Required Test File Structure

```
tests/
├── test_models.py           # Phase 1: Data Models
├── test_storage.py          # Phase 2: Storage Service
├── test_payload_builder.py  # Phase 3: Payload Builder
├── test_validation.py       # Phase 4: Validation Service
├── test_ui_modules.py       # Phase 5: UI Modules
└── conftest.py              # Shared fixtures
```

### Test Requirements

Each phase test file must include:

1. **Fixtures** - Reusable test data setup
2. **Unit Tests** - Test individual functions/methods
3. **Edge Cases** - Test boundary conditions and error handling
4. **Integration Tests** - Test how components work together
5. **Docstrings** - Explain what each test verifies

### Test Naming Convention

```python
# Pattern: test_{what}_{condition}_{expected}
def test_create_team_with_empty_key_raises_error():
    """Test that Team creation fails with empty key."""
    pass

def test_validation_with_duplicate_keys_returns_error():
    """Test that duplicate keys are detected as errors."""
    pass
```

### Before Marking Phase Complete

A phase is NOT complete until:
- [ ] All documentation created (README.md, DESIGN.md, PYTHON_CONCEPTS.md)
- [ ] All code implemented
- [ ] All test cases written
- [ ] All tests passing (`pytest tests/test_{phase}.py -v`)
- [ ] Integration verified with previous phases

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific phase tests
pytest tests/test_models.py -v        # Phase 1
pytest tests/test_storage.py -v       # Phase 2
pytest tests/test_payload_builder.py -v  # Phase 3
pytest tests/test_validation.py -v    # Phase 4
pytest tests/test_ui_modules.py -v    # Phase 5

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## Implementation Phases

> **Detailed documentation:** See `docs/phases/` for HLD, DLD, and concept guides for each phase.

| Phase | Module | Description | Docs | Tests |
|-------|--------|-------------|------|-------|
| 1 | `models/` | Data Models (dataclasses) | [📄 Phase 1](docs/phases/phase1/) | ✅ `test_models.py` |
| 2 | `services/storage.py` | File persistence | [📄 Phase 2](docs/phases/phase2/) | ✅ `test_storage.py` |
| 3 | `services/payload_builder.py` | Matrix → JSON transformation | [📄 Phase 3](docs/phases/phase3/) | ✅ `test_payload_builder.py` |
| 4 | `services/validation.py` | Config validation | [📄 Phase 4](docs/phases/phase4/) | ✅ `test_validation.py` |
| 5 | `ui/*.py` | UI modules (split from app.py) | [📄 Phase 5](docs/phases/phase5/) | ✅ `test_ui_modules.py` |
| 6 | `services/ld_client.py` | LaunchDarkly API integration | [📄 Phase 6](docs/phases/phase6/) | ✅ `test_ld_client.py` |
| 7 | `services/deployer.py` | Deployment execution | [📄 Phase 7](docs/phases/phase7/) | ✅ `test_deployer.py` |
| 8 | `ui/deploy_tab.py` | Complete deploy UI | [📄 Phase 8](docs/phases/phase8/) | ✅ `test_deploy_ui.py` |
| 9 | `app.py` | Wire everything together | 📋 Planned | 📋 Planned |
| 10 | `tests/` | Testing & Polish | 📋 Planned | 📋 Planned |
| 11 | `core/ld_actions.py` | Role Attribute Pattern | [📄 Phase 11](docs/phases/phase11/) | ✅ |
| 12 | `core/ld_actions.py` | Resource Builders | [📄 Phase 12](docs/phases/phase12/) | ✅ |
| 13 | `services/package_generator.py` | Delivery ZIP | [📄 Phase 13](docs/phases/phase13/) | ✅ |
| 14 | `core/ld_actions.py` | Observability Permissions | [📄 Phase 14](docs/phases/phase14/) | 📋 Planned |
| 15 | `ui/matrix_tab.py` | Tabbed Permission Groups | [📄 Phase 15](docs/phases/phase15/) | 📋 Planned |
| 16 | `services/terraform_generator.py` | Terraform Export | [📄 Phase 16](docs/phases/phase16/) | ✅ `test_terraform_generator.py` |
| 17 | `core/ld_actions.py` | Global Account Roles | [📄 Phase 17](docs/phases/phase17/) | 📋 Planned |
| 18 | `core/ld_actions.py` | Views Permissions | [📄 Phase 18](docs/phases/phase18/) | 📋 Planned |
| 19 | `ui/matrix_tab.py` | Manage Context Kinds | [📄 Phase 19](docs/phases/phase19/) | 📋 Planned |
| 20 | `services/payload_builder.py` | Deny Lists & Exclusions | [📄 Phase 20](docs/phases/phase20/) | 📋 Planned |
| 21 | `services/payload_builder.py` | Visible Teams Attribute | [📄 Phase 21](docs/phases/phase21/) | 📋 Planned |
| 22 | `ui/matrix_tab.py` | Admin/Destructive Actions | [📄 Phase 22](docs/phases/phase22/) | 📋 Planned |
| 23 | `services/payload_builder.py` | Tag-Based Env Filtering | [📄 Phase 23](docs/phases/phase23/) | 📋 Planned |
| 24 | `services/payload_builder.py` | Flag/Segment Subset Scoping | [📄 Phase 24](docs/phases/phase24/) | 📋 Planned |
| 25 | `core/ld_actions.py` | Account-Level Admin Roles | [📄 Phase 25](docs/phases/phase25/) | 📋 Planned |
| 26 | `core/session_tracker.py` | Active User Counter | [📄 Phase 26](docs/phases/phase26/) | ✅ `test_session_tracker.py` |
| 27 | `ui/advisor_tab.py` | Role Designer AI (Gemini Chat) | [📄 Phase 27](docs/phases/phase27/) | ✅ `test_ai_advisor.py` |

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Deployment Compatibility

**IMPORTANT:** This app is designed to work on both **localhost** and **Streamlit Cloud**.

### Localhost (Development)

```bash
streamlit run app.py
```

- Full functionality with persistent storage
- Configs saved to `configs/customers/` folder
- History and backups preserved
- Templates available from `configs/templates/`

### Streamlit Cloud (Production)

Deploy via GitHub integration to Streamlit Cloud.

- **Ephemeral Storage:** Files saved during runtime are lost on app restart
- **Templates:** Available (committed to git repo)
- **User Configs:** Must use Download/Upload workflow
- **Warning Banner:** Automatically shown to users

### Writing Cloud-Compatible Code

When writing code for this project, follow these guidelines:

1. **Always Use Environment Detection:**
   ```python
   from core import is_streamlit_cloud, get_storage_warning

   if is_streamlit_cloud():
       # Show download button prominently
       # Don't rely on server-side persistence
   ```

2. **Provide Download/Upload Options:**
   ```python
   # Always offer export functionality
   st.download_button("Download Config", config_json, "config.json")

   # Always offer import functionality
   uploaded = st.file_uploader("Upload Config", type=["json"])
   ```

3. **Use Session State for Temporary Data:**
   ```python
   # Session state persists during the session (both environments)
   if "config" not in st.session_state:
       st.session_state.config = None
   ```

4. **Don't Assume File Persistence:**
   ```python
   # BAD: Assumes file will exist later
   storage.save(config)
   # ... later ...
   config = storage.load("customer")  # May fail on cloud restart!

   # GOOD: Always have fallback
   if storage.exists("customer"):
       config = storage.load("customer")
   else:
       st.info("No saved config found. Start fresh or upload a config.")
   ```

5. **Use Templates for Defaults:**
   ```python
   # Templates are in git repo, always available
   templates = storage.list_templates()  # Always works
   config = storage.load_template("standard-4-env")  # Always works
   ```

### Feature Compatibility Matrix

| Feature | Localhost | Streamlit Cloud |
|---------|-----------|-----------------|
| Load Templates | ✅ | ✅ |
| Design Matrix | ✅ | ✅ |
| Session State | ✅ | ✅ |
| Download Config | ✅ | ✅ |
| Upload Config | ✅ | ✅ |
| Save to Server | ✅ | ⚠️ Temporary |
| Load from Server | ✅ | ⚠️ Lost on restart |
| History/Backups | ✅ | ⚠️ Lost on restart |

## Testing

```bash
pytest tests/
```
