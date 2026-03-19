# Phase 1: Data Models

> **Goal:** Create type-safe Python dataclasses to represent RBAC configuration data

---

## Quick Links

| Document | Purpose |
|----------|---------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Deep dive into Python concepts used |

---

## Overview

### What We're Building

```
models/
├── __init__.py           # Package exports
├── team.py               # Team dataclass
├── environment.py        # EnvironmentGroup dataclass
├── permissions.py        # ProjectPermission, EnvironmentPermission
└── config.py             # RBACConfig (main container)
```

### The 5 Models

| Model | Purpose | Fields |
|-------|---------|--------|
| `Team` | Functional role/persona | key, name, description |
| `EnvironmentGroup` | Category of environments | key, requires_approval, is_critical, notes |
| `ProjectPermission` | Project-level permissions | team_key, create_flags, update_flags, ... |
| `EnvironmentPermission` | Environment-level permissions | team_key, env_key, update_targeting, ... |
| `RBACConfig` | Complete configuration | customer_name, teams[], env_groups[], permissions[] |

### Relationships

```
RBACConfig (root)
├── teams: [Team, Team, ...]
├── env_groups: [EnvironmentGroup, ...]
├── project_permissions: [ProjectPermission, ...]
└── env_permissions: [EnvironmentPermission, ...]
```

---

## Python Concepts Used

| Concept | What It Does | Learn More |
|---------|--------------|------------|
| `@dataclass` | Auto-generates boilerplate | [Section 2](./PYTHON_CONCEPTS.md#2-dataclasses---the-modern-way) |
| Type hints | Declares expected types | [Section 3](./PYTHON_CONCEPTS.md#3-type-hints---declaring-types) |
| `field()` | Configures field behavior | [Section 4](./PYTHON_CONCEPTS.md#4-default-values-and-field) |
| `__post_init__` | Validation after creation | [Section 5](./PYTHON_CONCEPTS.md#5-validation-with-__post_init__) |
| `asdict()` | Convert to dictionary | [Section 6](./PYTHON_CONCEPTS.md#6-serialization---to-and-from-json) |

---

## Example Usage

```python
from models import Team, RBACConfig

# Create a team
dev_team = Team(
    key="dev",
    name="Developer",
    description="Development team"
)

# Create config
config = RBACConfig(
    customer_name="Acme Inc",
    project_key="mobile-app",
    teams=[dev_team]
)

# Save to JSON
config.to_json()  # → JSON string

# Load from JSON
config = RBACConfig.from_json(json_string)
```

---

## Implementation Checklist

- [x] `models/__init__.py` - Package setup
- [x] `models/team.py` - Team dataclass
- [x] `models/environment.py` - EnvironmentGroup dataclass
- [x] `models/permissions.py` - Permission dataclasses
- [x] `models/config.py` - RBACConfig dataclass
- [ ] `tests/test_models.py` - Unit tests (optional)

---

## Status

| Item | Status |
|------|--------|
| HLD | ✅ Complete |
| DLD | ✅ Complete |
| Pseudo Logic | ✅ Complete |
| Python Concepts Doc | ✅ Complete |
| Implementation | ✅ Complete |

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| - | **Phase 1: Data Models** | Phase 2: Storage |

[← Back to Project](../../../CLAUDE.md)
