# Phase 12: Python Concepts

Concepts introduced in the role attribute env scoping and role correctness implementation.

---

## Table of Contents

1. [Dict-Driven Behaviour](#1-dict-driven-behaviour)
2. [String Naming Conventions: kebab-case vs camelCase](#2-string-naming-conventions-kebab-case-vs-camelcase)
3. [The Coalesce Pattern](#3-the-coalesce-pattern)
4. [Removing Dead Code Paths](#4-removing-dead-code-paths)
5. [Constant Dicts as Feature Flags](#5-constant-dicts-as-feature-flags)
6. [Quick Reference Card](#quick-reference-card)

---

## 1. Dict-Driven Behaviour

### The concept

A constant dict can act as a **feature configuration table** — it decides what behaviour applies to which inputs, without any if/elif logic.

### In this phase: CONTEXT_KIND_ACTIONS_FOR_PERMISSION

```python
# In ld_actions.py
CONTEXT_KIND_ACTIONS_FOR_PERMISSION: Dict[str, List[str]] = {
    "Create Flags": ["createContextKind"],
    "Update Flags": ["updateContextKind", "updateAvailabilityForExperiments"],
}
```

Usage in payload_builder.py:
```python
# dict.get() returns None if permission isn't in the dict
context_kind_actions = CONTEXT_KIND_ACTIONS_FOR_PERMISSION.get(permission_name)

if context_kind_actions:   # None is falsy — skips if not in dict
    policy.append({
        "effect": "allow",
        "actions": context_kind_actions,
        "resources": [build_context_kind_role_attribute_resource("projects")]
    })
```

**Result:** `create-flags` gets a context-kind statement. `archive-flags` doesn't. Zero if/elif needed.

### Why this is powerful

Adding context kind support to a NEW permission in the future = **one line in the dict**:
```python
CONTEXT_KIND_ACTIONS_FOR_PERMISSION = {
    "Create Flags": ["createContextKind"],
    "Update Flags": ["updateContextKind", "updateAvailabilityForExperiments"],
    "New Permission": ["someContextKindAction"],  # ← one line, done
}
```

---

## 2. String Naming Conventions: kebab-case vs camelCase

### The problem

Strings used as keys in external systems must match **exactly**. The wrong case = no match = silently broken.

```python
# WRONG — camelCase (our original code)
PERMISSION_ATTRIBUTE_MAP = {
    "Update Targeting": "updateTargetingEnvironments",
}
# Generates role resource: ...${roleAttribute/updateTargetingEnvironments}...
# Team attribute key:       "updateTargetingEnvironments"
# → These match ✅ but DON'T match sa-demo ❌

# CORRECT — kebab-case (sa-demo pattern)
PERMISSION_ATTRIBUTE_MAP = {
    "Update Targeting": "update-targeting-environments",
}
# Generates role resource: ...${roleAttribute/update-targeting-environments}...
# Team attribute key:       "update-targeting-environments"
# → These match ✅ AND match sa-demo ✅
```

### Python string methods for case conversion

```python
# From permission name to attribute key
permission = "Update Targeting"

# Manual kebab: lower() + replace spaces with hyphens
attr_key = permission.lower().replace(" ", "-") + "-environments"
# → "update-targeting-environments"

# Check convention in tests
assert attr_key == attr_key.lower()          # no uppercase
assert "_" not in attr_key                    # no underscores
assert attr_key.endswith("-environments")     # correct suffix
```

### Why kebab-case for this project

Terraform and the sa-demo use kebab-case for role attribute keys. Since the JSON we generate is consumed directly by LD (which also follows this convention), we match it exactly to avoid mismatches between Terraform-managed and rbac-builder-managed accounts.

---

## 3. The Coalesce Pattern

### From Terraform to Python

Terraform's `coalesce(a, b)` returns the first non-null value. Python doesn't have coalesce but `or` works similarly for boolean expressions:

```hcl
# Terraform: coalesce(null, !false) = true
create_context_kind = coalesce(var.manage_context_kinds_in_flag_roles, !var.manage_context_kinds)
```

Equivalent in Python:
```python
# Python: the `or` operator short-circuits
manage_context_kinds_in_flag_roles = None
manage_context_kinds = False

create_context_kind = manage_context_kinds_in_flag_roles or (not manage_context_kinds)
# = None or (not False)
# = None or True
# = True   ← because None is falsy, so `or` evaluates the right side
```

### Gotcha: `or` vs `is not None`

```python
# CAREFUL — False or x evaluates x (False is falsy)
False or "default"    # → "default"  (might not be what you want!)

# Use explicit None check when False is a valid value
value = None
result = value if value is not None else default
```

In our case the values are always lists (never False), so `or` is safe.

---

## 4. Removing Dead Code Paths

### What we did

The `_uses_criticality_pattern()` method was previously used in 3 places to branch behaviour. After the decision to always use role attribute scoping, all 3 branches were simplified to one path.

```python
# Before — 3 places had this pattern:
use_criticality = self._uses_criticality_pattern()
if use_criticality:
    # ... critical path
else:
    # ... standard path

# After — removed all branches, only standard path remains
```

### Why keep the helper methods?

`_is_env_critical()`, `_get_critical_envs()`, etc. were kept even though they no longer drive role generation. Why?
- They still provide useful information (which envs the SA marked as critical)
- Tests still cover them
- Future features might use the critical flag for other purposes (e.g. warnings, documentation)
- Removing tested code has a cost — only remove if actively harmful

### Python lesson: dead code vs unused code

```python
# Dead code = code that can NEVER be reached
def foo():
    return "early"
    print("unreachable")   # ← dead code, always remove

# Unused code = code that EXISTS but isn't called right now
def _get_critical_envs(self):   # not called in main path
    ...                          # ← keep if might be useful later
```

---

## 5. Constant Dicts as Feature Flags

### The concept

A constant dict where **presence in the dict = feature enabled** is a clean alternative to feature flags scattered through the code.

```python
# Dict presence = this permission gets context kind statement
CONTEXT_KIND_ACTIONS_FOR_PERMISSION = {
    "Create Flags": [...],   # ← present = enabled
    "Update Flags": [...],   # ← present = enabled
    # "Archive Flags" not here = disabled
}

# Usage — no if/elif, no boolean flags
actions = CONTEXT_KIND_ACTIONS_FOR_PERMISSION.get(permission_name)
if actions:
    # feature is enabled for this permission
```

### vs boolean flags (harder to maintain)

```python
# BAD — boolean flags scattered through the code
CREATE_FLAGS_HAS_CONTEXT_KIND = True
UPDATE_FLAGS_HAS_CONTEXT_KIND = True
ARCHIVE_FLAGS_HAS_CONTEXT_KIND = False

if permission == "Create Flags" and CREATE_FLAGS_HAS_CONTEXT_KIND:
    ...
elif permission == "Update Flags" and UPDATE_FLAGS_HAS_CONTEXT_KIND:
    ...
```

The dict approach puts all configuration in one place and uses Python's natural truthiness.

---

## Quick Reference Card

```python
# Dict-driven behaviour — no if/elif
result = MY_DICT.get(key)       # None if not found
if result: do_something(result) # None is falsy → skips

# kebab-case from title case
"Update Targeting".lower().replace(" ", "-")  → "update-targeting"

# Coalesce pattern
a or b          # returns b if a is falsy (None, False, 0, "")
a if a is not None else b  # returns b ONLY if a is None

# Keep vs remove dead code
# Dead = unreachable → always remove
# Unused = not called but accessible → keep if useful

# Dict as feature flag
"Key" in MY_DICT   # → True means feature enabled
MY_DICT.get("Key") # → None means feature disabled
```
