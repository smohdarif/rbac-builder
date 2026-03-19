# Phase 14: Python Concepts

Concepts introduced when adding Observability Permissions.

---

## Table of Contents

1. [Extending an Enum](#1-extending-an-enum)
2. [Dict Presence as a Feature Flag](#2-dict-presence-as-a-feature-flag)
3. [Union Types in Type Hints](#3-union-types-in-type-hints)
4. [Branching on Type — isinstance vs dict lookup](#4-branching-on-type--isinstance-vs-dict-lookup)
5. [Quick Reference Card](#quick-reference-card)
6. [Next Steps](#next-steps)

---

## 1. Extending an Enum

### The concept

In Phase 11 we created `ProjectAction` and `EnvironmentAction` enums. This phase adds a third: `ObservabilityAction`. Python enums can't be subclassed to add values, so we create a separate enum following the same pattern.

```python
# Existing (Phase 11)
class ProjectAction(Enum):
    CREATE_FLAGS = ["cloneFlag", "createFlag"]
    UPDATE_FLAGS = ["updateName", "updateDescription", ...]

# New (Phase 14) — same pattern, different domain
class ObservabilityAction(Enum):
    VIEW_SESSIONS = ["viewSession"]
    VIEW_ERRORS   = ["viewError", "updateErrorStatus"]
    VIEW_LOGS     = ["viewLog"]
    VIEW_TRACES   = ["viewTrace"]
    MANAGE_ALERTS = ["viewAlert", "createAlert", "deleteAlert", ...]
```

### Why not add to ProjectAction?

```python
# BAD — mixing flag actions with observability actions in one enum
class ProjectAction(Enum):
    CREATE_FLAGS  = ["cloneFlag", "createFlag"]    # flag action
    VIEW_SESSIONS = ["viewSession"]                 # observability action — confusing!

# GOOD — separate enums, clear domain separation
class ProjectAction(Enum):
    CREATE_FLAGS = ["cloneFlag", "createFlag"]

class ObservabilityAction(Enum):
    VIEW_SESSIONS = ["viewSession"]
```

Separate enums keep each domain self-contained and easy to find.

### Python gotcha: can't inherit from an Enum with values

```python
# WRONG — Python doesn't allow this
class ExtendedAction(ProjectAction):   # TypeError!
    NEW_ACTION = ["newAction"]

# RIGHT — create a new enum
class ObservabilityAction(Enum):
    NEW_ACTION = ["newAction"]
```

---

## 2. Dict Presence as a Feature Flag

### The concept

`OBSERVABILITY_RESOURCE_MAP` serves two purposes at once:
1. **Lookup:** maps permission name → resource type string
2. **Detection:** presence in the dict = this is an observability permission

```python
OBSERVABILITY_RESOURCE_MAP: Dict[str, str] = {
    "View Sessions": "session",
    "View Errors":   "error",
    "View Logs":     "log",
    "View Traces":   "trace",
    # ... etc
}

# Usage: both lookup AND detection in one call
def is_observability_permission(permission_name: str) -> bool:
    return permission_name in OBSERVABILITY_RESOURCE_MAP   # in = presence check

def get_observability_resource_type(permission_name: str) -> str:
    return OBSERVABILITY_RESOURCE_MAP.get(permission_name, "")
```

### Why not a separate set for detection?

```python
# BAD — two structures to keep in sync
OBSERVABILITY_PERMISSIONS = {"View Sessions", "View Errors", ...}  # set for detection
OBSERVABILITY_RESOURCE_MAP = {"View Sessions": "session", ...}     # dict for lookup
# Danger: if you add to one but forget the other, bugs!

# GOOD — one dict does both jobs
OBSERVABILITY_RESOURCE_MAP = {"View Sessions": "session", ...}
# Detection: "View Sessions" in OBSERVABILITY_RESOURCE_MAP → True
# Lookup:    OBSERVABILITY_RESOURCE_MAP["View Sessions"]    → "session"
```

### The `in` operator on dicts

```python
my_dict = {"a": 1, "b": 2}

"a" in my_dict       # → True  (checks keys, not values)
"c" in my_dict       # → False
1   in my_dict       # → False (1 is a value, not a key)
1   in my_dict.values() # → True  (explicit values check)
```

---

## 3. Union Types in Type Hints

### The concept

`PROJECT_PERMISSION_MAP` now maps to EITHER a `ProjectAction` OR an `ObservabilityAction`. In Python 3.10+ you can use `|` for union types:

```python
# Python 3.10+ syntax
PROJECT_PERMISSION_MAP: Dict[str, ProjectAction | ObservabilityAction] = {
    "Create Flags": ProjectAction.CREATE_FLAGS,       # ProjectAction
    "View Sessions": ObservabilityAction.VIEW_SESSIONS, # ObservabilityAction
}

# Python 3.9 and below — use Union from typing
from typing import Union
PROJECT_PERMISSION_MAP: Dict[str, Union[ProjectAction, ObservabilityAction]] = { ... }
```

### Why type hints matter here

Without the type hint, a reader might assume all values are `ProjectAction`. The union type documents that the dict is intentionally polymorphic.

```python
def get_project_actions(permission_name: str) -> List[str]:
    if permission_name in PROJECT_PERMISSION_MAP:
        enum_value = PROJECT_PERMISSION_MAP[permission_name]
        # enum_value could be ProjectAction OR ObservabilityAction
        # but BOTH have .value → list of strings
        return enum_value.value   # works for both!
    return []
```

This works because both enums follow the same structure (each value is a list of strings). This is called **duck typing** — if it walks like a duck and quacks like a duck, it's a duck.

---

## 4. Branching on Type — isinstance vs dict lookup

### The concept

In `_build_project_template_role()` we need to choose a different resource builder for observability permissions vs regular permissions. Two approaches:

### Option A: isinstance (type-based branching)

```python
enum_value = PROJECT_PERMISSION_MAP[permission_name]

if isinstance(enum_value, ObservabilityAction):
    # use observability resource builder
else:
    # use standard resource builder
```

### Option B: dict lookup (data-driven branching) ← CHOSEN

```python
if is_observability_permission(permission_name):
    # i.e.: permission_name in OBSERVABILITY_RESOURCE_MAP
    resource = build_project_type_resource("projects", OBSERVABILITY_RESOURCE_MAP[permission_name])
else:
    resource = build_role_attribute_resource("projects", resource_type)
```

### Why Option B is better

```python
# Option A — isinstance couples the builder to the enum type
# Adding a new enum type = change this if/elif chain

# Option B — dict lookup is data-driven
# Adding a new resource type = add one entry to OBSERVABILITY_RESOURCE_MAP
# No code changes in the builder!
```

This is the **Open/Closed Principle**: open for extension (add to dict), closed for modification (don't change builder logic).

### When to use isinstance

```python
# isinstance is appropriate when you TRULY need type-specific behaviour
# that can't be captured in a data structure:
if isinstance(obj, list):
    for item in obj: process(item)
elif isinstance(obj, dict):
    for k, v in obj.items(): process(k, v)
```

Use `isinstance` for type dispatch on built-in types. Use dict lookup for domain-specific dispatch.

---

## Quick Reference Card

```python
# New enum (same pattern as existing)
class ObservabilityAction(Enum):
    VIEW_SESSIONS = ["viewSession"]

# Dict as both lookup and detector
RESOURCE_MAP = {"View Sessions": "session", ...}
"View Sessions" in RESOURCE_MAP   # True (detection)
RESOURCE_MAP["View Sessions"]     # "session" (lookup)
RESOURCE_MAP.get("Unknown", "")   # "" (safe default)

# Union type hint
Dict[str, ProjectAction | ObservabilityAction]

# Duck typing — both enums have .value
enum_value = PROJECT_PERMISSION_MAP[name]
actions = enum_value.value   # works for any enum in the map

# Data-driven branching (preferred over isinstance)
if name in OBSERVABILITY_RESOURCE_MAP:
    resource = build_project_type_resource("projects", RESOURCE_MAP[name])
else:
    resource = build_role_attribute_resource("projects", resource_type)
```

---

## Next Steps

→ [DESIGN.md](./DESIGN.md) — Full implementation plan and test cases
