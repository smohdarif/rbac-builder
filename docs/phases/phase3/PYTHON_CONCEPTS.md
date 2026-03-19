# Phase 3: Python Concepts Deep Dive

> **Purpose:** This document explains the Python concepts used in Phase 3 (Payload Builder) in detail. Read this if you want to understand the "why" behind the code.

---

## Table of Contents

1. [Python Enums](#1-python-enums)
2. [Dictionary Mappings](#2-dictionary-mappings)
3. [Advanced List Comprehensions](#3-advanced-list-comprehensions)
4. [String Formatting and Building](#4-string-formatting-and-building)
5. [Data Transformation Patterns](#5-data-transformation-patterns)
6. [The Builder Pattern](#6-the-builder-pattern)
7. [Working with Nested Data](#7-working-with-nested-data)

---

## 1. Python Enums

### What is an Enum?

An **Enum** (enumeration) is a set of named constants. Instead of using plain strings that can be misspelled, enums provide type-safe, IDE-friendly constants.

```python
# WITHOUT enums (error-prone)
level = "project"  # Typo: "porject" would be a silent bug
if level == "project":
    do_something()

# WITH enums (type-safe)
from enum import Enum

class PermissionLevel(Enum):
    PROJECT = "project"
    ENVIRONMENT = "environment"

level = PermissionLevel.PROJECT
if level == PermissionLevel.PROJECT:
    do_something()
```

### Creating Enums

```python
from enum import Enum

class PermissionLevel(Enum):
    """Defines the scope of a permission."""
    PROJECT = "project"
    ENVIRONMENT = "environment"


class DeploymentStatus(Enum):
    """Status of a deployment operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Using Enums

```python
# Accessing values
level = PermissionLevel.PROJECT
print(level)        # PermissionLevel.PROJECT
print(level.value)  # "project"
print(level.name)   # "PROJECT"

# Comparing enums
if level == PermissionLevel.PROJECT:
    print("Project level!")

# Iterating over all values
for level in PermissionLevel:
    print(level.value)
# Output: "project", "environment"

# Using in function parameters
def get_actions(permission: str, level: PermissionLevel) -> list[str]:
    if level == PermissionLevel.PROJECT:
        return PROJECT_ACTIONS.get(permission, [])
    else:
        return ENV_ACTIONS.get(permission, [])
```

### Why Use Enums?

| Without Enums | With Enums |
|---------------|------------|
| `if level == "project"` | `if level == PermissionLevel.PROJECT` |
| Typos cause silent bugs | Typos cause immediate errors |
| No autocomplete | IDE autocomplete works |
| No type checking | Type checkers can validate |
| Magic strings everywhere | Self-documenting code |

---

## 2. Dictionary Mappings

### Using Dicts as Lookup Tables

Dictionaries are perfect for mapping one value to another. In Phase 3, we map permission names to LaunchDarkly action codes.

```python
# Simple mapping: permission name → list of LD actions
PROJECT_ACTIONS: dict[str, list[str]] = {
    "create_flags": ["createFlag"],
    "update_flags": [
        "updateName",
        "updateDescription",
        "updateTags",
        "updateFlagVariations",
    ],
    "archive_flags": ["deleteFlag"],
    "manage_webhooks": ["*"],
}

# Usage
actions = PROJECT_ACTIONS["create_flags"]
# Result: ["createFlag"]

actions = PROJECT_ACTIONS["update_flags"]
# Result: ["updateName", "updateDescription", "updateTags", "updateFlagVariations"]
```

### Safe Access with .get()

```python
# DANGEROUS: KeyError if key doesn't exist
actions = PROJECT_ACTIONS["nonexistent"]  # KeyError!

# SAFE: .get() returns None or default value
actions = PROJECT_ACTIONS.get("nonexistent")  # None
actions = PROJECT_ACTIONS.get("nonexistent", [])  # Empty list

# Using in real code
def get_actions(permission: str) -> list[str]:
    """Get LD actions for a permission, or empty list if unknown."""
    return PROJECT_ACTIONS.get(permission, [])
```

### Type Hints for Complex Dicts

```python
from typing import Dict, List

# Simple type hint
permissions: dict[str, bool] = {
    "create_flags": True,
    "update_flags": False,
}

# Nested type hint
ACTION_MAPPINGS: dict[str, dict[str, list[str]]] = {
    "project": {
        "create_flags": ["createFlag"],
        "update_flags": ["updateName", "updateDescription"],
    },
    "environment": {
        "update_targeting": ["updateOn", "updateTargets"],
    },
}
```

### Iterating Over Dictionaries

```python
permission_map = {
    "create_flags": True,
    "update_flags": True,
    "archive_flags": False,
}

# Iterate over keys
for permission in permission_map:
    print(permission)

# Iterate over values
for is_enabled in permission_map.values():
    print(is_enabled)

# Iterate over key-value pairs (most common)
for permission, is_enabled in permission_map.items():
    if is_enabled:
        actions = get_actions(permission)
        print(f"{permission}: {actions}")
```

---

## 3. Advanced List Comprehensions

### Basic Recap

```python
# Traditional loop
result = []
for item in items:
    result.append(item.key)

# List comprehension (same result)
result = [item.key for item in items]
```

### Filtering with Conditions

```python
# Only include items that match a condition
enabled_permissions = [
    perm for perm, enabled in permission_map.items()
    if enabled
]

# Multiple conditions
critical_envs = [
    env for env in environments
    if env.is_critical and env.requires_approval
]
```

### Transforming and Filtering Together

```python
# Get action lists for enabled permissions, flattened
all_actions = [
    action
    for perm, enabled in permission_map.items()
    if enabled
    for action in get_actions(perm)
]

# Explanation:
# 1. for perm, enabled in permission_map.items()  <- outer loop
# 2. if enabled                                    <- filter
# 3. for action in get_actions(perm)              <- inner loop
# 4. action                                        <- what to collect
```

### Nested Comprehensions

```python
# Build role keys for all team/env combinations
role_keys = [
    f"{team.key}-{env.key}"
    for team in config.teams
    for env in config.env_groups
]

# Equivalent to:
role_keys = []
for team in config.teams:
    for env in config.env_groups:
        role_keys.append(f"{team.key}-{env.key}")
```

### Dict Comprehensions

```python
# Create a dict from a list
teams_by_key = {team.key: team for team in config.teams}

# Usage
dev_team = teams_by_key["dev"]

# With filtering
critical_envs = {
    env.key: env
    for env in config.env_groups
    if env.is_critical
}
```

### When NOT to Use Comprehensions

```python
# TOO COMPLEX - use a regular loop
# Bad:
result = [
    process(item)
    for sublist in nested_list
    if sublist
    for item in sublist
    if item.is_valid
    and item.value > 0
]

# Better: Use a function or regular loop
def process_items(nested_list):
    result = []
    for sublist in nested_list:
        if not sublist:
            continue
        for item in sublist:
            if item.is_valid and item.value > 0:
                result.append(process(item))
    return result
```

---

## 4. String Formatting and Building

### f-strings (Formatted String Literals)

```python
project = "mobile-app"
env = "production"

# Basic f-string
resource = f"proj/{project}"
# Result: "proj/mobile-app"

# With expressions
resource = f"proj/{project}:env/{env}"
# Result: "proj/mobile-app:env/production"

# With method calls
resource = f"proj/{project.upper()}"
# Result: "proj/MOBILE-APP"

# With conditionals (ternary)
scope = "project"
resource = f"proj/{project}" + (f":env/{env}" if scope == "env" else "")
```

### Building LaunchDarkly Resource Strings

```python
def build_resource(project_key: str, env_key: str | None = None) -> str:
    """
    Build a LaunchDarkly resource string.

    Examples:
        >>> build_resource("mobile-app")
        'proj/mobile-app'
        >>> build_resource("mobile-app", "production")
        'proj/mobile-app:env/production'
    """
    resource = f"proj/{project_key}"

    if env_key:
        resource = f"{resource}:env/{env_key}"

    return resource
```

### Joining Lists into Strings

```python
actions = ["updateOn", "updateTargets", "updateRules"]

# Join with comma
actions_str = ", ".join(actions)
# Result: "updateOn, updateTargets, updateRules"

# Join with newlines
actions_str = "\n".join(actions)
# Result: "updateOn\nupdateTargets\nupdateRules"

# Building role names
team_key = "dev"
env_key = "production"
role_key = "-".join([team_key, env_key])
# Result: "dev-production"
```

### String Methods for Normalization

```python
name = "Dev Team"

# Convert to lowercase
name.lower()  # "dev team"

# Replace characters
name.replace(" ", "-")  # "Dev-Team"

# Chain methods
slug = name.lower().replace(" ", "-")  # "dev-team"

# Title case
env = "production"
env.title()  # "Production"

# For display names
role_name = f"{team.name} - {env.key.title()}"
# Result: "Dev Team - Production"
```

---

## 5. Data Transformation Patterns

### From Config to Payload

The main job of Phase 3 is **transforming** our data structure into LaunchDarkly's format.

```python
# Our format (input)
project_permission = ProjectPermission(
    team_key="dev",
    create_flags=True,
    update_flags=True,
    archive_flags=False,
)

# LaunchDarkly format (output)
policy_statement = {
    "effect": "allow",
    "actions": ["createFlag", "updateName", "updateDescription", ...],
    "resources": ["proj/mobile-app"]
}
```

### The Transformation Process

```python
def transform_permission_to_policy(
    perm: ProjectPermission,
    project_key: str
) -> dict:
    """Transform our permission to LD policy statement."""

    # Step 1: Collect enabled permissions
    enabled = []
    if perm.create_flags:
        enabled.append("create_flags")
    if perm.update_flags:
        enabled.append("update_flags")
    # ... etc

    # Step 2: Map to LD actions
    all_actions = []
    for permission_name in enabled:
        actions = PROJECT_ACTIONS.get(permission_name, [])
        all_actions.extend(actions)

    # Step 3: Build policy statement
    return {
        "effect": "allow",
        "actions": all_actions,
        "resources": [f"proj/{project_key}"]
    }
```

### Using getattr for Dynamic Attribute Access

```python
# Instead of many if statements...
if perm.create_flags:
    enabled.append("create_flags")
if perm.update_flags:
    enabled.append("update_flags")
# ... 10 more

# Use getattr to check attributes dynamically
PERMISSION_NAMES = [
    "create_flags",
    "update_flags",
    "archive_flags",
    "manage_webhooks",
    # ...
]

enabled = [
    name for name in PERMISSION_NAMES
    if getattr(perm, name, False)
]
```

### Extending Lists

```python
# Adding one item
actions = ["createFlag"]
actions.append("deleteFlag")
# Result: ["createFlag", "deleteFlag"]

# Adding multiple items
actions = ["createFlag"]
actions.extend(["updateName", "updateTags"])
# Result: ["createFlag", "updateName", "updateTags"]

# Common pattern: collect actions from multiple sources
all_actions = []
for permission in enabled_permissions:
    permission_actions = get_actions(permission)
    all_actions.extend(permission_actions)
```

---

## 6. The Builder Pattern

### What is the Builder Pattern?

The **Builder pattern** separates the construction of a complex object from its representation. Instead of one giant constructor, you build the object step by step.

```python
# WITHOUT Builder (one big function)
def create_role(team, env, project_perms, env_perms):
    # 100 lines of code...
    return role

# WITH Builder (step by step)
class PayloadBuilder:
    def __init__(self, config):
        self.config = config

    def build(self):
        roles = self.build_custom_roles()
        teams = self.build_teams()
        return DeployPayload(roles=roles, teams=teams)

    def build_custom_roles(self):
        # Build roles step by step
        pass

    def build_teams(self):
        # Build teams step by step
        pass
```

### Why Use Builder?

| Benefit | Description |
|---------|-------------|
| **Separation of concerns** | Each method does one thing |
| **Testability** | Can test each step independently |
| **Readability** | Easy to follow the build process |
| **Flexibility** | Can add/modify steps without changing others |

### Builder in Phase 3

```python
class PayloadBuilder:
    """Builds LaunchDarkly payloads from RBACConfig."""

    def __init__(self, config: RBACConfig):
        self.config = config
        self.project_key = config.project_key

    def build(self) -> DeployPayload:
        """Main build method - orchestrates the process."""
        roles = self.build_custom_roles()
        teams = self.build_teams()

        return DeployPayload(
            customer_name=self.config.customer_name,
            project_key=self.project_key,
            roles=roles,
            teams=teams,
        )

    def build_custom_roles(self) -> list[dict]:
        """Build all custom role payloads."""
        roles = []
        for team in self.config.teams:
            for env in self.config.env_groups:
                role = self._build_role_for_team_env(team, env)
                if role["policy"]:  # Only add if has permissions
                    roles.append(role)
        return roles

    def build_teams(self) -> list[dict]:
        """Build all team payloads."""
        # ... implementation
        pass
```

---

## 7. Working with Nested Data

### Accessing Nested Structures

```python
# Our config has nested relationships
config = RBACConfig(
    teams=[Team(key="dev"), Team(key="qa")],
    env_groups=[EnvironmentGroup(key="prod")],
    project_permissions=[
        ProjectPermission(team_key="dev", create_flags=True),
    ],
    env_permissions=[
        EnvironmentPermission(team_key="dev", environment_key="prod", ...),
    ],
)

# Finding related data requires lookups
def get_project_permission(config, team_key):
    """Find project permission for a team."""
    for perm in config.project_permissions:
        if perm.team_key == team_key:
            return perm
    return None

def get_env_permission(config, team_key, env_key):
    """Find environment permission for a team+env combo."""
    for perm in config.env_permissions:
        if perm.team_key == team_key and perm.environment_key == env_key:
            return perm
    return None
```

### Building Lookup Dictionaries

```python
# For faster lookups, build dictionaries once
class PayloadBuilder:
    def __init__(self, config: RBACConfig):
        self.config = config

        # Build lookup dictionaries for O(1) access
        self._project_perms_by_team = {
            p.team_key: p for p in config.project_permissions
        }
        self._env_perms = {
            (p.team_key, p.environment_key): p
            for p in config.env_permissions
        }

    def _get_project_perm(self, team_key: str) -> ProjectPermission | None:
        return self._project_perms_by_team.get(team_key)

    def _get_env_perm(self, team_key: str, env_key: str) -> EnvironmentPermission | None:
        return self._env_perms.get((team_key, env_key))
```

### Tuple Keys in Dictionaries

```python
# You can use tuples as dictionary keys!
# This is useful for multi-key lookups

env_permissions_lookup = {
    ("dev", "production"): EnvironmentPermission(...),
    ("dev", "staging"): EnvironmentPermission(...),
    ("qa", "production"): EnvironmentPermission(...),
}

# Lookup
perm = env_permissions_lookup.get(("dev", "production"))

# This works because tuples are hashable (immutable)
# Lists would NOT work as keys because they're mutable
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│              DATA TRANSFORMATION CHEAT SHEET (PHASE 3)              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ENUMS                                                               │
│  ─────                                                               │
│  from enum import Enum                                              │
│                                                                      │
│  class Level(Enum):                                                 │
│      PROJECT = "project"                                            │
│      ENV = "environment"                                            │
│                                                                      │
│  level = Level.PROJECT                                              │
│  level.value  # "project"                                           │
│  level.name   # "PROJECT"                                           │
│                                                                      │
│  DICTIONARY MAPPINGS                                                 │
│  ────────────────────                                                │
│  mapping = {"a": [1, 2], "b": [3, 4]}                               │
│  mapping.get("a")         # [1, 2]                                  │
│  mapping.get("x", [])     # [] (default)                            │
│  mapping.items()          # [("a", [1,2]), ("b", [3,4])]           │
│                                                                      │
│  LIST COMPREHENSIONS                                                 │
│  ────────────────────                                                │
│  [x.key for x in items]                     # Transform             │
│  [x for x in items if x.active]             # Filter                │
│  [x for row in matrix for x in row]         # Flatten               │
│                                                                      │
│  STRING BUILDING                                                     │
│  ────────────────                                                    │
│  f"proj/{project}"                          # f-string              │
│  f"proj/{project}:env/{env}"                # Nested                │
│  "-".join(["dev", "prod"])                  # "dev-prod"            │
│  "HELLO".lower()                            # "hello"               │
│  "hello".title()                            # "Hello"               │
│                                                                      │
│  DYNAMIC ATTRIBUTE ACCESS                                            │
│  ─────────────────────────                                           │
│  getattr(obj, "attr_name")                  # Get attribute         │
│  getattr(obj, "attr_name", default)         # With default          │
│                                                                      │
│  LIST OPERATIONS                                                     │
│  ────────────────                                                    │
│  list.append(item)                          # Add one               │
│  list.extend([items])                       # Add many              │
│                                                                      │
│  TUPLE DICT KEYS                                                     │
│  ────────────────                                                    │
│  lookup = {("a", "b"): value}               # Composite key         │
│  lookup.get(("a", "b"))                     # Lookup                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

After understanding these concepts, you're ready to implement the payload builder:

1. **[DESIGN.md](./DESIGN.md)** - Review the HLD, DLD, and pseudo logic
2. **Implementation** - Create the payload builder files

Each file will include lesson comments referencing this document.
