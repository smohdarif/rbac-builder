# Phase 1: Data Models Design Document

> **Phase:** 1 of 10
> **Status:** ✅ Complete
> **Goal:** Create type-safe data models for RBAC configuration

---

## Related Documents

| Document | Description |
|----------|-------------|
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Deep dive into Python concepts (dataclasses, type hints, etc.) |
| [README.md](./README.md) | Phase 1 overview and quick reference |
| [../../RBAC_CONCEPTS.md](../../RBAC_CONCEPTS.md) | RBAC terminology and LaunchDarkly concepts |

---

## Table of Contents
1. [High-Level Design (HLD)](#high-level-design-hld)
2. [Detailed Low-Level Design (DLD)](#detailed-low-level-design-dld)
3. [Pseudo Logic](#pseudo-logic)
4. [Implementation Plan](#implementation-plan)
5. [Learning Resources](#learning-resources)

---

## High-Level Design (HLD)

### What Are We Building?

**Data Models** are Python classes that define the **structure** of our data. Think of them as blueprints or templates that describe:
- What information we need to store
- What type each piece of information should be (string, number, boolean, etc.)
- How different pieces of information relate to each other

### Why Do We Need Data Models?

```
WITHOUT Data Models:                 WITH Data Models:
─────────────────────               ─────────────────────
data = {                            @dataclass
    "name": "Dev Team",             class Team:
    "key": "dev",                       name: str
    "desc": "Developers"                key: str
}                                       description: str

# Problems:                         # Benefits:
# - No autocomplete in IDE          # - IDE autocomplete works
# - Typos cause bugs                # - Typos caught immediately
# - No type checking                # - Type checking enabled
# - Hard to understand structure    # - Self-documenting code
```

### Where Do Models Fit in Our Architecture?

```
┌─────────────────────────────────────────────────────────────────────┐
│                           RBAC BUILDER                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   UI Layer   │    │   Services   │    │   Storage    │          │
│  │   (app.py)   │    │  (business)  │    │   (files)    │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│         │                   │                   │                   │
│         └───────────────────┼───────────────────┘                   │
│                             │                                        │
│                             ▼                                        │
│                    ┌────────────────┐                               │
│                    │  DATA MODELS   │  ◄── WE ARE HERE              │
│                    │   (models/)    │                               │
│                    │                │                               │
│                    │  • Team        │                               │
│                    │  • Project     │                               │
│                    │  • EnvGroup    │                               │
│                    │  • Permission  │                               │
│                    │  • RBACConfig  │                               │
│                    └────────────────┘                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Models We Need to Create

| Model | Purpose | Example |
|-------|---------|---------|
| `Team` | Represents a functional role/persona | Developer, QA, Admin |
| `EnvironmentGroup` | Category of environments | "critical" (prod), "non-critical" (dev) |
| `ProjectPermission` | Project-level permissions for a team | Can create flags, manage metrics |
| `EnvironmentPermission` | Environment-level permissions | Can update targeting in "dev" |
| `RBACConfig` | Complete configuration for a customer | All teams + all permissions |

### Data Flow

```
USER INPUT (UI)          DATA MODELS              OUTPUT
─────────────────       ─────────────            ──────────────

┌─────────────┐         ┌─────────────┐          ┌─────────────┐
│ User fills  │         │ Convert to  │          │ Save as     │
│ form in UI  │ ──────► │ Team object │ ───────► │ JSON file   │
│             │         │             │          │             │
│ name: "Dev" │         │ Team(       │          │ {"name":    │
│ key: "dev"  │         │   name="Dev"│          │   "Dev",    │
│             │         │   key="dev" │          │   "key":    │
└─────────────┘         │ )           │          │   "dev"}    │
                        └─────────────┘          └─────────────┘

                              │
                              ▼

                        ┌─────────────┐          ┌─────────────┐
                        │ Convert to  │          │ Send to     │
                        │ LD Policy   │ ───────► │ LaunchDarkly│
                        │ JSON        │          │ API         │
                        └─────────────┘          └─────────────┘
```

---

## Detailed Low-Level Design (DLD)

### File Structure

```
models/
├── __init__.py           # Export all models
├── team.py               # Team dataclass
├── environment.py        # EnvironmentGroup dataclass
├── permissions.py        # Permission dataclasses
└── config.py             # RBACConfig (main container)
```

### Model 1: Team

**Purpose:** Represents a functional role or persona in the organization.

```
┌─────────────────────────────────────────────────────────────┐
│                         TEAM                                 │
├─────────────────────────────────────────────────────────────┤
│  Fields:                                                     │
│  ┌─────────────┬─────────┬──────────────────────────────┐  │
│  │ Field       │ Type    │ Description                   │  │
│  ├─────────────┼─────────┼──────────────────────────────┤  │
│  │ key         │ str     │ Unique ID (e.g., "dev")      │  │
│  │ name        │ str     │ Display name ("Developer")    │  │
│  │ description │ str     │ What this team does          │  │
│  └─────────────┴─────────┴──────────────────────────────┘  │
│                                                              │
│  Validation Rules:                                           │
│  • key must be lowercase, no spaces (use hyphens)           │
│  • key must be unique across all teams                      │
│  • name is required                                          │
└─────────────────────────────────────────────────────────────┘
```

### Model 2: EnvironmentGroup

**Purpose:** Represents a category of environments (e.g., critical vs non-critical).

```
┌─────────────────────────────────────────────────────────────┐
│                    ENVIRONMENT GROUP                         │
├─────────────────────────────────────────────────────────────┤
│  Fields:                                                     │
│  ┌──────────────────┬─────────┬─────────────────────────┐  │
│  │ Field            │ Type    │ Description              │  │
│  ├──────────────────┼─────────┼─────────────────────────┤  │
│  │ key              │ str     │ Unique ID ("critical")   │  │
│  │ requires_approval│ bool    │ Need approval workflow?  │  │
│  │ is_critical      │ bool    │ Is this critical env?    │  │
│  │ notes            │ str     │ Which envs belong here   │  │
│  └──────────────────┴─────────┴─────────────────────────┘  │
│                                                              │
│  Example:                                                    │
│  • key="production", requires_approval=True, is_critical=True│
│  • key="development", requires_approval=False, is_critical=False│
└─────────────────────────────────────────────────────────────┘
```

### Model 3: ProjectPermission

**Purpose:** Defines what a team can do at the PROJECT level (affects all environments).

```
┌─────────────────────────────────────────────────────────────┐
│                   PROJECT PERMISSION                         │
├─────────────────────────────────────────────────────────────┤
│  Fields:                                                     │
│  ┌─────────────────────────────┬─────────┬──────────────┐  │
│  │ Field                       │ Type    │ Default      │  │
│  ├─────────────────────────────┼─────────┼──────────────┤  │
│  │ team_key                    │ str     │ (required)   │  │
│  │ create_flags                │ bool    │ False        │  │
│  │ update_flags                │ bool    │ False        │  │
│  │ archive_flags               │ bool    │ False        │  │
│  │ update_client_side_availability │ bool │ False       │  │
│  │ manage_metrics              │ bool    │ False        │  │
│  │ manage_release_pipelines    │ bool    │ False        │  │
│  │ view_project                │ bool    │ True         │  │
│  │ create_ai_configs           │ bool    │ False        │  │
│  │ update_ai_configs           │ bool    │ False        │  │
│  │ delete_ai_configs           │ bool    │ False        │  │
│  └─────────────────────────────┴─────────┴──────────────┘  │
│                                                              │
│  Relationship: One ProjectPermission per Team               │
└─────────────────────────────────────────────────────────────┘
```

### Model 4: EnvironmentPermission

**Purpose:** Defines what a team can do in a SPECIFIC environment group.

```
┌─────────────────────────────────────────────────────────────┐
│                  ENVIRONMENT PERMISSION                      │
├─────────────────────────────────────────────────────────────┤
│  Fields:                                                     │
│  ┌─────────────────────────────┬─────────┬──────────────┐  │
│  │ Field                       │ Type    │ Default      │  │
│  ├─────────────────────────────┼─────────┼──────────────┤  │
│  │ team_key                    │ str     │ (required)   │  │
│  │ environment_key             │ str     │ (required)   │  │
│  │ update_targeting            │ bool    │ False        │  │
│  │ review_changes              │ bool    │ False        │  │
│  │ apply_changes               │ bool    │ False        │  │
│  │ manage_segments             │ bool    │ False        │  │
│  │ manage_experiments          │ bool    │ False        │  │
│  │ view_sdk_key                │ bool    │ False        │  │
│  │ update_ai_config_targeting  │ bool    │ False        │  │
│  └─────────────────────────────┴─────────┴──────────────┘  │
│                                                              │
│  Relationship: One per Team + EnvironmentGroup combination  │
│  Example: Developer + production = limited permissions      │
│           Developer + development = full permissions        │
└─────────────────────────────────────────────────────────────┘
```

### Model 5: RBACConfig (Main Container)

**Purpose:** The top-level container that holds the ENTIRE configuration for a customer.

```
┌─────────────────────────────────────────────────────────────┐
│                       RBAC CONFIG                            │
├─────────────────────────────────────────────────────────────┤
│  This is the "root" model that contains everything          │
│                                                              │
│  Fields:                                                     │
│  ┌─────────────────────┬────────────────────┬────────────┐ │
│  │ Field               │ Type               │ Description│ │
│  ├─────────────────────┼────────────────────┼────────────┤ │
│  │ customer_name       │ str                │ "Acme Inc" │ │
│  │ project_key         │ str                │ "mobile"   │ │
│  │ mode                │ str                │ "Manual"   │ │
│  │ created_at          │ datetime           │ When made  │ │
│  │ updated_at          │ datetime           │ Last edit  │ │
│  │ teams               │ list[Team]         │ All teams  │ │
│  │ env_groups          │ list[EnvGroup]     │ All env grp│ │
│  │ project_permissions │ list[ProjectPerm]  │ Proj perms │ │
│  │ env_permissions     │ list[EnvPerm]      │ Env perms  │ │
│  └─────────────────────┴────────────────────┴────────────┘ │
│                                                              │
│  Relationships:                                              │
│                                                              │
│  RBACConfig                                                  │
│  ├── teams: [Team, Team, Team, ...]                         │
│  ├── env_groups: [EnvGroup, EnvGroup, ...]                  │
│  ├── project_permissions: [ProjectPerm, ...]                │
│  └── env_permissions: [EnvPerm, EnvPerm, ...]               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Entity Relationship Diagram

```
┌─────────────┐         ┌─────────────────────┐
│    Team     │         │   EnvironmentGroup  │
├─────────────┤         ├─────────────────────┤
│ key (PK)    │         │ key (PK)            │
│ name        │         │ requires_approval   │
│ description │         │ is_critical         │
└──────┬──────┘         │ notes               │
       │                └──────────┬──────────┘
       │                           │
       │    ┌──────────────────────┘
       │    │
       ▼    ▼
┌──────────────────────┐    ┌──────────────────────┐
│  ProjectPermission   │    │ EnvironmentPermission│
├──────────────────────┤    ├──────────────────────┤
│ team_key (FK)────────┼───►│ team_key (FK)        │
│ create_flags         │    │ environment_key (FK)─┼───► EnvGroup
│ update_flags         │    │ update_targeting     │
│ archive_flags        │    │ review_changes       │
│ ...                  │    │ apply_changes        │
└──────────────────────┘    │ ...                  │
                            └──────────────────────┘

                    ┌─────────────────┐
                    │   RBACConfig    │
                    ├─────────────────┤
                    │ customer_name   │
                    │ project_key     │
                    │ mode            │
                    │ teams[]─────────┼───► List of Team
                    │ env_groups[]────┼───► List of EnvGroup
                    │ project_perms[] ┼───► List of ProjectPerm
                    │ env_perms[]─────┼───► List of EnvPerm
                    └─────────────────┘

Legend:
  PK = Primary Key (unique identifier)
  FK = Foreign Key (reference to another model)
  [] = List/Collection
```

---

## Pseudo Logic

### How Models Will Be Used

#### 1. Creating a Team (from UI input)

```
PSEUDO CODE:

FUNCTION create_team_from_ui(key, name, description):
    # Validate input
    IF key is empty:
        RAISE error "Key is required"

    IF key contains spaces or uppercase:
        key = convert_to_slug(key)  # "My Team" → "my-team"

    # Create the model
    team = Team(
        key = key,
        name = name,
        description = description
    )

    RETURN team
```

#### 2. Converting UI DataFrame to Models

```
PSEUDO CODE:

FUNCTION dataframe_to_teams(df):
    teams = empty list

    FOR each row IN df:
        team = Team(
            key = row["Key"],
            name = row["Name"],
            description = row["Description"]
        )
        ADD team TO teams

    RETURN teams


FUNCTION dataframe_to_project_permissions(df):
    permissions = empty list

    FOR each row IN df:
        perm = ProjectPermission(
            team_key = row["Team"],
            create_flags = row["Create Flags"],
            update_flags = row["Update Flags"],
            archive_flags = row["Archive Flags"],
            # ... other fields
        )
        ADD perm TO permissions

    RETURN permissions
```

#### 3. Building Complete RBACConfig

```
PSEUDO CODE:

FUNCTION build_config_from_session_state():
    # Get data from Streamlit session state
    teams_df = session_state.teams
    env_groups_df = session_state.env_groups
    project_matrix_df = session_state.project_matrix
    env_matrix_df = session_state.env_matrix

    # Convert DataFrames to Models
    teams = dataframe_to_teams(teams_df)
    env_groups = dataframe_to_env_groups(env_groups_df)
    project_perms = dataframe_to_project_permissions(project_matrix_df)
    env_perms = dataframe_to_env_permissions(env_matrix_df)

    # Build the complete config
    config = RBACConfig(
        customer_name = session_state.customer_name,
        project_key = session_state.project_key,
        mode = session_state.mode,
        created_at = current_time(),
        updated_at = current_time(),
        teams = teams,
        env_groups = env_groups,
        project_permissions = project_perms,
        env_permissions = env_perms
    )

    RETURN config
```

#### 4. Converting Model to JSON (for saving)

```
PSEUDO CODE:

FUNCTION config_to_json(config):
    # Python dataclasses can convert to dict easily
    data = {
        "customer_name": config.customer_name,
        "project_key": config.project_key,
        "mode": config.mode,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
        "teams": [team_to_dict(t) FOR t IN config.teams],
        "env_groups": [env_group_to_dict(e) FOR e IN config.env_groups],
        "project_permissions": [perm_to_dict(p) FOR p IN config.project_permissions],
        "env_permissions": [perm_to_dict(p) FOR p IN config.env_permissions]
    }

    RETURN json.dumps(data, indent=2)
```

#### 5. Loading Config from JSON (for restoring)

```
PSEUDO CODE:

FUNCTION json_to_config(json_string):
    data = json.loads(json_string)

    # Reconstruct models from dict
    teams = [Team(**t) FOR t IN data["teams"]]
    env_groups = [EnvironmentGroup(**e) FOR e IN data["env_groups"]]
    project_perms = [ProjectPermission(**p) FOR p IN data["project_permissions"]]
    env_perms = [EnvironmentPermission(**p) FOR p IN data["env_permissions"]]

    config = RBACConfig(
        customer_name = data["customer_name"],
        project_key = data["project_key"],
        mode = data["mode"],
        created_at = parse_datetime(data["created_at"]),
        updated_at = parse_datetime(data["updated_at"]),
        teams = teams,
        env_groups = env_groups,
        project_permissions = project_perms,
        env_permissions = env_perms
    )

    RETURN config
```

### Integration with Existing app.py

```
CURRENT STATE (app.py):                 FUTURE STATE (with models):
────────────────────────               ────────────────────────────

# Data as DataFrames                   # Data as Models
st.session_state.teams = df            teams = [Team(...), Team(...)]
                                       config = RBACConfig(teams=teams)

# Save button                          # Save button
if st.button("Save"):                  if st.button("Save"):
    # Currently does nothing               config = build_config()
    st.success("Saved!")                   storage.save(config)
                                           st.success("Saved!")

# Load - not implemented               # Load from file
                                       config = storage.load("customer.json")
                                       populate_session_state(config)
```

---

## Implementation Plan

### Step-by-Step Implementation

```
STEP 1: Create models/__init__.py
        └── Empty file to make it a Python package

STEP 2: Create models/team.py
        └── Team dataclass with validation

STEP 3: Create models/environment.py
        └── EnvironmentGroup dataclass

STEP 4: Create models/permissions.py
        └── ProjectPermission + EnvironmentPermission dataclasses

STEP 5: Create models/config.py
        └── RBACConfig dataclass (imports all others)

STEP 6: Update models/__init__.py
        └── Export all models for easy importing

STEP 7: Create tests/test_models.py
        └── Unit tests to verify models work correctly
```

### Python Concepts You'll Learn

| Concept | What It Does | Example |
|---------|--------------|---------|
| `@dataclass` | Auto-generates `__init__`, `__repr__`, etc. | `@dataclass class Team:` |
| Type hints | Declares expected types | `name: str` |
| Default values | Sets defaults for optional fields | `is_critical: bool = False` |
| `field()` | Configures field behavior | `field(default_factory=list)` |
| `__post_init__` | Runs validation after creation | Validate key format |
| `asdict()` | Converts dataclass to dictionary | For JSON serialization |

### Estimated Learning Topics

```
┌─────────────────────────────────────────────────────────────┐
│                  PYTHON LESSONS IN PHASE 1                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LESSON 15: Python Dataclasses                              │
│  ├── What are dataclasses and why use them                  │
│  ├── The @dataclass decorator                               │
│  └── Auto-generated methods (__init__, __repr__, __eq__)    │
│                                                              │
│  LESSON 16: Type Hints                                      │
│  ├── Basic types: str, int, bool, float                     │
│  ├── Collection types: list[T], dict[K, V]                  │
│  └── Optional types: Optional[str], str | None              │
│                                                              │
│  LESSON 17: Default Values and field()                      │
│  ├── Simple defaults: name: str = "default"                 │
│  ├── Mutable defaults: field(default_factory=list)          │
│  └── Why mutable defaults are dangerous                     │
│                                                              │
│  LESSON 18: Validation with __post_init__                   │
│  ├── When __post_init__ runs                                │
│  ├── Validating field values                                │
│  └── Raising ValueError for invalid data                    │
│                                                              │
│  LESSON 19: Serialization (to/from JSON)                    │
│  ├── asdict() for converting to dict                        │
│  ├── Custom to_dict() methods                               │
│  └── Factory methods: from_dict()                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Summary

### What We're Building

- **5 dataclass models** that define the structure of our RBAC configuration
- **Type-safe** code that catches errors early
- **Serializable** models that can be saved to JSON and loaded back
- **Foundation** for storage, validation, and deployment services

### Why This Matters

```
Without Models:                      With Models:
─────────────────                   ─────────────
• Dictionaries everywhere           • Clear structure
• Runtime errors from typos         • IDE autocomplete
• No validation                     • Validation built-in
• Hard to understand                • Self-documenting
• Difficult to maintain             • Easy to extend
```

### Ready to Implement?

When you're ready, we'll create these files:
1. `models/__init__.py`
2. `models/team.py`
3. `models/environment.py`
4. `models/permissions.py`
5. `models/config.py`

Each file will include **lesson comments** to explain the Python concepts as we code.

---

## Learning Resources

### Deep Dive Documents

For detailed explanations of Python concepts used in this phase:

| Topic | Document | Description |
|-------|----------|-------------|
| **All Python Concepts** | [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Comprehensive guide covering all concepts below |
| Dataclasses | [Section 2](./PYTHON_CONCEPTS.md#2-dataclasses---the-modern-way) | @dataclass decorator, auto-generated methods |
| Type Hints | [Section 3](./PYTHON_CONCEPTS.md#3-type-hints---declaring-types) | str, int, list[T], Optional |
| Default Values | [Section 4](./PYTHON_CONCEPTS.md#4-default-values-and-field) | field(), default_factory |
| Validation | [Section 5](./PYTHON_CONCEPTS.md#5-validation-with-__post_init__) | __post_init__ method |
| Serialization | [Section 6](./PYTHON_CONCEPTS.md#6-serialization---to-and-from-json) | asdict(), to/from JSON |
| Packages | [Section 7](./PYTHON_CONCEPTS.md#7-python-packages-and-__init__py) | __init__.py, imports |

### External Resources

| Resource | Link |
|----------|------|
| Python Dataclasses Docs | https://docs.python.org/3/library/dataclasses.html |
| Type Hints Cheat Sheet | https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html |
| Real Python - Dataclasses | https://realpython.com/python-data-classes/ |

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| - | **Phase 1: Data Models** | Phase 2: Storage |

[← Back to Project README](../../../CLAUDE.md) | [View Python Concepts →](./PYTHON_CONCEPTS.md)
