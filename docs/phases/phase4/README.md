# Phase 4: Validation Service

> **Status:** ✅ Complete
> **Goal:** Validate RBAC configurations before deployment

---

## Quick Links

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Deep dive into Enum, dataclasses, regex, sets |

---

## Overview

The **Validation Service** checks RBAC configurations for errors and warnings before deployment. This prevents failed API calls and helps users fix issues early.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User Config   │ ──► │   Validation    │ ──► │   Payload Gen   │
│   (matrices)    │     │   (Phase 4)     │     │   (Phase 3)     │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │  ValidationResult│
                        │  - errors: []   │
                        │  - warnings: [] │
                        │  - is_valid     │
                        └─────────────────┘
```

---

## Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `services/validation.py` | ConfigValidator, ValidationResult, ValidationIssue | ~450 |

---

## Classes

### Severity (Enum)

```python
class Severity(Enum):
    ERROR = "error"      # Blocks deployment
    WARNING = "warning"  # Should review
    INFO = "info"        # Informational
```

### ValidationIssue

```python
@dataclass
class ValidationIssue:
    severity: Severity           # ERROR, WARNING, INFO
    code: str                    # "EMPTY_CUSTOMER_NAME"
    message: str                 # "Customer name is required"
    field: Optional[str]         # "customer_name"
    suggestion: Optional[str]    # "Enter a name in sidebar"
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    issues: List[ValidationIssue]

    @property
    def is_valid(self) -> bool      # True if no errors
    @property
    def errors(self) -> List        # All ERROR issues
    @property
    def warnings(self) -> List      # All WARNING issues

    def add_error(code, message, ...)
    def add_warning(code, message, ...)
```

### ConfigValidator

```python
class ConfigValidator:
    def __init__(self, customer_name, project_key,
                 teams_df, env_groups_df,
                 project_matrix_df, env_matrix_df)

    def validate(self) -> ValidationResult
```

---

## Validation Rules

### Errors (Block Deployment)

| Code | Description |
|------|-------------|
| `EMPTY_CUSTOMER_NAME` | Customer name is required |
| `EMPTY_PROJECT_KEY` | Project key is required |
| `INVALID_PROJECT_KEY_FORMAT` | Key has invalid characters |
| `NO_TEAMS` | At least one team required |
| `NO_ENV_GROUPS` | At least one environment required |
| `EMPTY_TEAM_KEY` | Team has no key |
| `INVALID_TEAM_KEY_FORMAT` | Team key has invalid characters |
| `DUPLICATE_TEAM_KEY` | Same team key used twice |
| `DUPLICATE_ENV_KEY` | Same environment key used twice |

### Warnings (Review Recommended)

| Code | Description |
|------|-------------|
| `DUPLICATE_TEAM_NAME` | Same team name used twice |
| `EMPTY_PROJECT_MATRIX` | No project permissions defined |
| `EMPTY_ENV_MATRIX` | No environment permissions defined |
| `UNKNOWN_TEAM_IN_MATRIX` | Team in matrix not found in Teams list |
| `UNKNOWN_ENV_IN_MATRIX` | Environment in matrix not found |
| `TEAM_NO_PERMISSIONS` | Team has no permissions assigned |

---

## Usage

### Basic Usage

```python
from services import ConfigValidator, ValidationResult

validator = ConfigValidator(
    customer_name="Acme Corp",
    project_key="mobile-app",
    teams_df=teams_df,
    env_groups_df=env_groups_df,
    project_matrix_df=project_matrix_df,
    env_matrix_df=env_matrix_df
)

result = validator.validate()

if result.is_valid:
    print("Configuration is valid!")
else:
    for error in result.errors:
        print(f"ERROR: {error.message}")
```

### From Streamlit Session State

```python
from services import validate_from_session

result = validate_from_session(
    customer_name=customer_name,
    project_key=project_key,
    session_state=st.session_state
)
```

### In Deploy Tab UI

```python
# Validation runs automatically
validation_result = validate_from_session(...)

# Show status
if validation_result.is_valid:
    st.success("Configuration is valid!")
else:
    st.error(f"{validation_result.error_count} errors found")

# Disable generate button if invalid
st.button(
    "Generate Payloads",
    disabled=not validation_result.is_valid
)
```

---

## Key Concepts

| Concept | Purpose | Example |
|---------|---------|---------|
| Enum | Type-safe severity levels | `Severity.ERROR` |
| Dataclass | Clean data containers | `ValidationIssue` |
| Properties | Computed attributes | `result.is_valid` |
| Regex | Format validation | `^[a-zA-Z0-9._-]+$` |
| Set | O(1) duplicate detection | `seen_keys = set()` |

---

## Checklist

- [x] Create `Severity` enum
- [x] Create `ValidationIssue` dataclass
- [x] Create `ValidationResult` dataclass
- [x] Create `ConfigValidator` class
- [x] Implement required field validation
- [x] Implement key format validation
- [x] Implement duplicate detection
- [x] Implement reference validation
- [x] Implement permission coverage check
- [x] Add convenience function `validate_from_session`
- [x] Export from `services/__init__.py`
- [x] Integrate with Deploy tab UI
- [x] Add validation-gated generate button

---

## Navigation

| Previous | Up | Next |
|----------|------|------|
| [Phase 3: Payload Builder](../phase3/) | [All Phases](../) | [Phase 5: UI Modules](../phase5/) |
