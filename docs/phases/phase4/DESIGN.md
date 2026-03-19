# Phase 4: Validation Service Design Document

> **Phase:** 4 of 10
> **Status:** ✅ Complete
> **Goal:** Validate RBAC configurations before deployment to catch errors early
> **Depends On:** Phase 1 (Data Models), Phase 2 (Storage), Phase 3 (Payload Builder)

---

## Related Documents

| Document | Description |
|----------|-------------|
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Deep dive into validation patterns, dataclasses, enums |
| [README.md](./README.md) | Phase 4 overview and quick reference |
| [../phase3/](../phase3/) | Phase 3 - Payload Builder (dependency) |
| [../phase2/](../phase2/) | Phase 2 - Storage Service (dependency) |
| [../phase1/](../phase1/) | Phase 1 - Data Models (dependency) |

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

A **Validation Service** that checks RBAC configurations for errors and warnings before deployment. This prevents failed API calls and helps users fix issues early.

### Why Do We Need Validation?

```
WITHOUT VALIDATION:                    WITH VALIDATION:
──────────────────                    ─────────────────

User designs matrix                   User designs matrix
        │                                     │
        ▼                                     ▼
Generate payloads                     ┌───────────────────┐
        │                             │  VALIDATION       │
        ▼                             │  ✓ Check fields   │
Deploy to LD API                      │  ✓ Check formats  │
        │                             │  ✓ Check refs     │
        ▼                             └─────────┬─────────┘
❌ API ERROR!                                   │
"Invalid key format"                  ┌─────────▼─────────┐
                                      │  Errors found?    │
User confused...                      │  Show them NOW    │
                                      └─────────┬─────────┘
                                                │
                                      User fixes issues
                                                │
                                                ▼
                                      Generate payloads
                                                │
                                                ▼
                                      ✅ Deploy succeeds!
```

### Where Does Validation Fit?

```
┌─────────────────────────────────────────────────────────────────────┐
│                           RBAC BUILDER                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐         ┌──────────────────────────────────────┐ │
│  │   UI Layer   │         │         SERVICES LAYER               │ │
│  │   (app.py)   │         │                                      │ │
│  │              │         │  ┌──────────────┐  ┌──────────────┐ │ │
│  │  Deploy Tab  │ ──────► │  │  VALIDATION  │  │  PAYLOAD     │ │ │
│  │              │         │  │  ◄── HERE    │  │  BUILDER     │ │ │
│  │  "Generate"  │         │  │              │──►│  (Phase 3)   │ │ │
│  │              │         │  │  Errors? ────┘  └──────────────┘ │ │
│  └──────────────┘         │  │  Block!       │                   │ │
│                           │  └──────────────┘                    │ │
│                           └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Features

| Feature | Description |
|---------|-------------|
| **Required Field Checks** | Ensure customer_name, project_key, teams exist |
| **Format Validation** | Keys match LD constraints (no spaces, max length) |
| **Duplicate Detection** | Find duplicate team/environment keys |
| **Reference Validation** | Teams in matrix exist in Teams list |
| **Permission Coverage** | Warn if teams have no permissions |
| **Severity Levels** | ERROR (blocks), WARNING (review), INFO (fyi) |

### Data Flow

```
VALIDATION FLOW:
────────────────

    Session State Data
    (teams, env_groups, matrices)
           │
           ▼
    ┌─────────────────┐
    │ ConfigValidator │
    │                 │
    │ 1. Required     │
    │    fields       │
    │                 │
    │ 2. Key formats  │
    │                 │
    │ 3. Duplicates   │
    │                 │
    │ 4. References   │
    │                 │
    │ 5. Coverage     │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ValidationResult │
    │                 │
    │ - is_valid      │
    │ - errors: []    │
    │ - warnings: []  │
    └────────┬────────┘
             │
             ├───────────────┐
             │               │
             ▼               ▼
    ┌─────────────┐   ┌─────────────┐
    │  is_valid   │   │  !is_valid  │
    │  = True     │   │  = False    │
    │             │   │             │
    │  Generate   │   │  Show       │
    │  Payloads   │   │  Errors     │
    │  ✅         │   │  ❌         │
    └─────────────┘   └─────────────┘
```

---

## Detailed Low-Level Design (DLD)

### File Structure

```
services/
└── validation.py          # ConfigValidator, ValidationResult, ValidationIssue
```

### Class Design: Severity (Enum)

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Severity                                  │
├─────────────────────────────────────────────────────────────────────┤
│  An enumeration of validation severity levels                        │
│                                                                      │
│  Values:                                                             │
│  ┌─────────────────┬──────────────────────────────────────────────┐│
│  │ Value           │ Description                                   ││
│  ├─────────────────┼──────────────────────────────────────────────┤│
│  │ ERROR           │ Blocks deployment - must be fixed             ││
│  │ WARNING         │ Should review - won't block                   ││
│  │ INFO            │ Informational only                            ││
│  └─────────────────┴──────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Class Design: ValidationIssue

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ValidationIssue                               │
├─────────────────────────────────────────────────────────────────────┤
│  A single validation issue (error, warning, or info)                 │
│                                                                      │
│  Attributes:                                                         │
│  ┌─────────────────┬──────────────┬─────────────────────────────┐  │
│  │ Attribute       │ Type         │ Description                  │  │
│  ├─────────────────┼──────────────┼─────────────────────────────┤  │
│  │ severity        │ Severity     │ ERROR, WARNING, or INFO      │  │
│  │ code            │ str          │ Machine-readable code        │  │
│  │ message         │ str          │ Human-readable description   │  │
│  │ field           │ str | None   │ Which field has the issue    │  │
│  │ suggestion      │ str | None   │ How to fix it                │  │
│  └─────────────────┴──────────────┴─────────────────────────────┘  │
│                                                                      │
│  Methods:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ to_dict() -> dict                                               ││
│  │   Convert to dictionary for JSON serialization                  ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Class Design: ValidationResult

```
┌─────────────────────────────────────────────────────────────────────┐
│                       ValidationResult                               │
├─────────────────────────────────────────────────────────────────────┤
│  Container for all validation issues                                 │
│                                                                      │
│  Attributes:                                                         │
│  ┌─────────────────┬────────────────────┬───────────────────────┐  │
│  │ Attribute       │ Type               │ Description            │  │
│  ├─────────────────┼────────────────────┼───────────────────────┤  │
│  │ issues          │ List[Issue]        │ All issues found       │  │
│  └─────────────────┴────────────────────┴───────────────────────┘  │
│                                                                      │
│  Properties:                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ is_valid: bool       - True if no ERROR-level issues            ││
│  │ errors: List[Issue]  - All ERROR issues                         ││
│  │ warnings: List[Issue]- All WARNING issues                       ││
│  │ error_count: int     - Number of errors                         ││
│  │ warning_count: int   - Number of warnings                       ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  Methods:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ add_error(code, message, field?, suggestion?)                   ││
│  │   Add an ERROR-level issue                                      ││
│  │                                                                  ││
│  │ add_warning(code, message, field?, suggestion?)                 ││
│  │   Add a WARNING-level issue                                     ││
│  │                                                                  ││
│  │ add_info(code, message, field?, suggestion?)                    ││
│  │   Add an INFO-level issue                                       ││
│  │                                                                  ││
│  │ to_dict() -> dict                                               ││
│  │   Convert to dictionary for JSON serialization                  ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Class Design: ConfigValidator

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ConfigValidator                               │
├─────────────────────────────────────────────────────────────────────┤
│  Main validation class - runs all validation checks                  │
│                                                                      │
│  Attributes:                                                         │
│  ┌─────────────────┬──────────────┬─────────────────────────────┐  │
│  │ Attribute       │ Type         │ Description                  │  │
│  ├─────────────────┼──────────────┼─────────────────────────────┤  │
│  │ customer_name   │ str          │ Customer identifier          │  │
│  │ project_key     │ str          │ LD project key               │  │
│  │ teams_df        │ DataFrame    │ Teams data                   │  │
│  │ env_groups_df   │ DataFrame    │ Environment groups           │  │
│  │ project_matrix  │ DataFrame    │ Project permissions          │  │
│  │ env_matrix_df   │ DataFrame    │ Env permissions              │  │
│  └─────────────────┴──────────────┴─────────────────────────────┘  │
│                                                                      │
│  Class Constants:                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ KEY_PATTERN = r'^[a-zA-Z0-9._-]+$'  # Valid key characters      ││
│  │ KEY_MAX_LENGTH = 256                 # Max key length           ││
│  │ NAME_MAX_LENGTH = 256                # Max name length          ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  Methods:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ MAIN METHOD                                                      ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ validate() -> ValidationResult                                  ││
│  │   Run all validation checks and return result                   ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ VALIDATION METHODS                                               ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ _validate_required_fields(result)                               ││
│  │   Check customer_name, project_key, teams, env_groups exist     ││
│  │                                                                  ││
│  │ _validate_key_formats(result)                                   ││
│  │   Check keys match LD format (no spaces, valid chars)           ││
│  │                                                                  ││
│  │ _validate_teams(result)                                         ││
│  │   Check team keys unique, valid format                          ││
│  │                                                                  ││
│  │ _validate_env_groups(result)                                    ││
│  │   Check env keys unique, valid format                           ││
│  │                                                                  ││
│  │ _validate_project_matrix(result)                                ││
│  │   Check teams in matrix exist                                   ││
│  │                                                                  ││
│  │ _validate_env_matrix(result)                                    ││
│  │   Check teams and envs in matrix exist                          ││
│  │                                                                  ││
│  │ _validate_permission_coverage(result)                           ││
│  │   Warn if teams have no permissions                             ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Validation Rules Table

| Code | Severity | Condition | Message |
|------|----------|-----------|---------|
| `EMPTY_CUSTOMER_NAME` | ERROR | customer_name is empty | Customer name is required |
| `EMPTY_PROJECT_KEY` | ERROR | project_key is empty | Project key is required |
| `INVALID_PROJECT_KEY_FORMAT` | ERROR | Key has invalid chars | Key contains invalid characters |
| `PROJECT_KEY_TOO_LONG` | ERROR | Key > 256 chars | Key exceeds max length |
| `NO_TEAMS` | ERROR | teams_df is empty | At least one team required |
| `NO_ENV_GROUPS` | ERROR | env_groups is empty | At least one env required |
| `EMPTY_TEAM_KEY` | ERROR | Team has no key | Team has no key |
| `INVALID_TEAM_KEY_FORMAT` | ERROR | Key has invalid chars | Team key invalid |
| `DUPLICATE_TEAM_KEY` | ERROR | Same key twice | Duplicate team key |
| `DUPLICATE_TEAM_NAME` | WARNING | Same name twice | Duplicate team name |
| `EMPTY_ENV_KEY` | ERROR | Env has no key | Env has no key |
| `DUPLICATE_ENV_KEY` | ERROR | Same key twice | Duplicate env key |
| `EMPTY_PROJECT_MATRIX` | WARNING | No project perms | No project permissions |
| `EMPTY_ENV_MATRIX` | WARNING | No env perms | No env permissions |
| `UNKNOWN_TEAM_IN_MATRIX` | WARNING | Team not in list | Team not found |
| `UNKNOWN_ENV_IN_MATRIX` | WARNING | Env not in list | Env not found |
| `TEAM_NO_PERMISSIONS` | WARNING | Team has 0 perms | Team has no permissions |

---

## Pseudo Logic

### Main Validation Flow

```python
def validate() -> ValidationResult:
    """
    Run all validation checks.

    PSEUDO LOGIC:
    1. Create empty ValidationResult
    2. Run each validation method (each adds issues to result)
       a. _validate_required_fields(result)
       b. _validate_key_formats(result)
       c. _validate_teams(result)
       d. _validate_env_groups(result)
       e. _validate_project_matrix(result)
       f. _validate_env_matrix(result)
       g. _validate_permission_coverage(result)
    3. Return result

    Result contains:
    - All issues found
    - is_valid = True if no ERROR issues
    """
    result = ValidationResult()

    self._validate_required_fields(result)
    self._validate_key_formats(result)
    self._validate_teams(result)
    self._validate_env_groups(result)
    self._validate_project_matrix(result)
    self._validate_env_matrix(result)
    self._validate_permission_coverage(result)

    return result
```

### Required Fields Validation

```python
def _validate_required_fields(result: ValidationResult):
    """
    Check required fields exist and are non-empty.

    PSEUDO LOGIC:
    1. Check customer_name:
       - If empty or whitespace only → ERROR

    2. Check project_key:
       - If empty or whitespace only → ERROR

    3. Check teams_df:
       - If None or empty → ERROR

    4. Check env_groups_df:
       - If None or empty → ERROR
    """
    IF customer_name is empty:
        result.add_error("EMPTY_CUSTOMER_NAME", ...)

    IF project_key is empty:
        result.add_error("EMPTY_PROJECT_KEY", ...)

    IF teams_df is None or empty:
        result.add_error("NO_TEAMS", ...)

    IF env_groups_df is None or empty:
        result.add_error("NO_ENV_GROUPS", ...)
```

### Key Format Validation

```python
def _validate_key_formats(result: ValidationResult):
    """
    Validate keys match LaunchDarkly format requirements.

    PSEUDO LOGIC:
    1. Check project_key if present:
       - Must match pattern: ^[a-zA-Z0-9._-]+$
       - Must be <= 256 characters

    LD Key Rules:
    - Allowed: letters, numbers, dots, underscores, hyphens
    - NOT allowed: spaces, special chars (!@#$%^&*), unicode
    """
    IF project_key exists:
        IF NOT regex.match(KEY_PATTERN, project_key):
            result.add_error("INVALID_PROJECT_KEY_FORMAT", ...)

        IF len(project_key) > 256:
            result.add_error("PROJECT_KEY_TOO_LONG", ...)
```

### Duplicate Detection

```python
def _validate_teams(result: ValidationResult):
    """
    Validate team definitions.

    PSEUDO LOGIC:
    1. Create empty set: seen_keys
    2. For each team row:
       a. Check key is not empty → ERROR if empty
       b. Check key format is valid → ERROR if invalid
       c. Check key not in seen_keys → ERROR if duplicate
       d. Add key to seen_keys
    """
    seen_keys = set()

    FOR each team in teams_df:
        key = team["Key"]

        IF key is empty:
            result.add_error("EMPTY_TEAM_KEY", ...)
            CONTINUE

        IF NOT valid_format(key):
            result.add_error("INVALID_TEAM_KEY_FORMAT", ...)

        IF key IN seen_keys:
            result.add_error("DUPLICATE_TEAM_KEY", ...)

        seen_keys.add(key)
```

### Reference Validation

```python
def _validate_project_matrix(result: ValidationResult):
    """
    Validate teams in matrix exist in Teams list.

    PSEUDO LOGIC:
    1. Get set of valid team names from teams_df
    2. For each row in project_matrix:
       a. Get team name
       b. If not in valid_team_names → WARNING
    """
    valid_team_names = set(teams_df["Name"])

    FOR each row in project_matrix_df:
        team_name = row["Team"]

        IF team_name NOT IN valid_team_names:
            result.add_warning("UNKNOWN_TEAM_IN_MATRIX", ...)
```

### Permission Coverage Check

```python
def _validate_permission_coverage(result: ValidationResult):
    """
    Check that teams have at least some permissions.

    PSEUDO LOGIC:
    1. For each team in teams_df:
       a. Check if team has project-level permissions
       b. Check if team has env-level permissions
       c. If neither → WARNING
    """
    FOR each team in teams_df:
        team_name = team["Name"]

        has_project = _team_has_project_permissions(team_name)
        has_env = _team_has_env_permissions(team_name)

        IF NOT has_project AND NOT has_env:
            result.add_warning("TEAM_NO_PERMISSIONS", ...)


def _team_has_project_permissions(team_name: str) -> bool:
    """
    Check if team has any project permissions set to True.
    """
    team_rows = project_matrix[project_matrix["Team"] == team_name]

    FOR each column (except "Team"):
        IF any value is True:
            RETURN True

    RETURN False
```

---

## Implementation Plan

### Step-by-Step Implementation

| Step | Task | Files |
|------|------|-------|
| 1 | Create Severity enum | `services/validation.py` |
| 2 | Create ValidationIssue dataclass | `services/validation.py` |
| 3 | Create ValidationResult dataclass | `services/validation.py` |
| 4 | Create ConfigValidator class | `services/validation.py` |
| 5 | Implement required fields validation | `services/validation.py` |
| 6 | Implement key format validation | `services/validation.py` |
| 7 | Implement teams validation | `services/validation.py` |
| 8 | Implement env groups validation | `services/validation.py` |
| 9 | Implement matrix validation | `services/validation.py` |
| 10 | Implement permission coverage | `services/validation.py` |
| 11 | Add convenience function | `services/validation.py` |
| 12 | Export from services | `services/__init__.py` |
| 13 | Integrate with Deploy tab | `app.py` |
| 14 | Add validation-gated actions | `app.py` |

### Python Concepts Used

| Concept | Where Used | Purpose |
|---------|------------|---------|
| Enum | `Severity` | Type-safe severity levels |
| Dataclass | `ValidationIssue`, `ValidationResult` | Clean data containers |
| Properties | `ValidationResult.is_valid` | Computed attributes |
| List comprehensions | `errors`, `warnings` properties | Filter issues by severity |
| Set | `seen_keys` | O(1) duplicate detection |
| Regular expressions | `KEY_PATTERN` | Format validation |
| Optional types | `field`, `suggestion` | Nullable attributes |

---

## Learning Resources

### Python Documentation

- [Enum](https://docs.python.org/3/library/enum.html) - Enumerations
- [dataclasses](https://docs.python.org/3/library/dataclasses.html) - Data Classes
- [re](https://docs.python.org/3/library/re.html) - Regular Expressions
- [typing](https://docs.python.org/3/library/typing.html) - Type Hints

### LaunchDarkly Documentation

- [Custom Roles](https://docs.launchdarkly.com/home/account/roles) - Role constraints
- [API Reference](https://apidocs.launchdarkly.com/) - API validation rules

---

## Navigation

| Previous | Up | Next |
|----------|------|------|
| [Phase 3: Payload Builder](../phase3/) | [All Phases](../) | [Phase 5: UI Modules](../phase5/) |
