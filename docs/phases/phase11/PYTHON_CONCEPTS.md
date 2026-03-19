# Phase 11: Python Concepts

Concepts introduced in the role attribute pattern implementation.

---

## Table of Contents

1. [Escaped Braces in f-strings](#1-escaped-braces-in-f-strings)
2. [Dict as a Configuration Table](#2-dict-as-a-configuration-table)
3. [Optional with Three States](#3-optional-with-three-states)
4. [The Builder Pattern](#4-the-builder-pattern)
5. [List Comprehension for Filtering](#5-list-comprehension-for-filtering)
6. [Quick Reference Card](#quick-reference-card)

---

## 1. Escaped Braces in f-strings

### The Problem

`${roleAttribute/projects}` contains curly braces. In Python f-strings, `{...}` means "evaluate this expression". So how do you put a literal `{` in an f-string?

### The Solution: Double the braces

```python
# WRONG — Python tries to evaluate roleAttribute/projects as a variable
resource = f"proj/${roleAttribute/projects}:env/*:flag/*"
#                  ^ SyntaxError!

# CORRECT — {{ and }} produce literal { and } in the output
resource = f"proj/${{roleAttribute/projects}}:env/*:flag/*"
#                  ^^                       ^^
#                  literal {                literal }

# Result string: "proj/${roleAttribute/projects}:env/*:flag/*"
```

### Real usage in ld_actions.py

```python
def build_project_only_role_attribute_resource(project_attr: str = "projects") -> str:
    # {{ → literal {    }} → literal }
    return f"proj/${{roleAttribute/{project_attr}}}"
    # Output: "proj/${roleAttribute/projects}"

def build_env_role_attribute_resource(project_attr: str, env_attr: str, resource_type: str) -> str:
    return f"proj/${{roleAttribute/{project_attr}}}:env/${{roleAttribute/{env_attr}}}:{resource_type}/*"
    # Output: "proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*"
```

### When to use
Any time you need literal `{` or `}` characters in an f-string output — common in template strings, JSON templates, or resource specifiers.

---

## 2. Dict as a Configuration Table

### The concept

Instead of a long `if/elif` chain, use a dictionary to map inputs to outputs. This is called a **lookup table** or **dispatch table**.

### Before: if/elif chain (hard to maintain)

```python
def get_attribute_name(permission_name: str) -> str:
    if permission_name == "Update Targeting":
        return "update-targeting-environments"
    elif permission_name == "Apply Changes":
        return "apply-changes-environments"
    elif permission_name == "Review Changes":
        return "review-changes-environments"
    # ...10 more elif branches
```

### After: dict lookup (easy to extend)

```python
# In ld_actions.py
PERMISSION_ATTRIBUTE_MAP: Dict[str, str] = {
    "Update Targeting":  "update-targeting-environments",
    "Apply Changes":     "apply-changes-environments",
    "Review Changes":    "review-changes-environments",
    # Add new permission = add one line here
}

def get_attribute_name(permission_name: str) -> str:
    return PERMISSION_ATTRIBUTE_MAP.get(permission_name, "projects")
    #                                                     ^ default value
```

### Why this matters
- Adding a new permission = one line in the dict, zero code changes
- The dict IS the documentation — you can see all mappings at a glance
- `.get(key, default)` safely returns a fallback if key not found

---

## 3. Optional with Three States

### The concept

`Optional[bool]` can be `True`, `False`, or `None` — giving you **three states** instead of two.

Used in `_build_env_template_role(permission_name, critical=None)`:

```python
def _build_env_template_role(
    self,
    permission_name: str,
    critical: Optional[bool] = None   # Three states!
) -> Optional[Dict[str, Any]]:

    if critical is True:
        # Critical mode — was: *;{critical:true} pattern
        role_key = f"critical-{base_key}"
    elif critical is False:
        # Non-critical mode
        role_key = f"non-critical-{base_key}"
    else:
        # Standard mode (None) — role attribute env scoping
        role_key = base_key
```

### Why `is True` not `== True`

```python
# GOTCHA: In Python, 1 == True is True, 0 == False is True
# Always use `is True` / `is False` / `is None` for explicit boolean checks

if critical == True:   # BAD — 1 would also pass this check
if critical is True:   # GOOD — only actual True passes
```

### Real-world analogy
Like a traffic light: `True` = green, `False` = red, `None` = no light (default behaviour).

---

## 4. The Builder Pattern

### The concept

Instead of one giant function that does everything, split work into small, focused methods that each build one piece. The `build()` method orchestrates them.

```python
class RoleAttributePayloadBuilder:

    def build(self) -> DeployPayload:
        """Orchestrates all the building steps."""
        roles = self._build_template_roles()    # Step 1
        teams = self._build_teams_with_attributes(roles)  # Step 2
        return DeployPayload(roles=roles, teams=teams)

    def _build_template_roles(self) -> List[Dict]:
        """Only responsible for role generation."""
        roles = []
        for perm in self._get_used_project_permissions():
            role = self._build_project_template_role(perm)
            if role:
                roles.append(role)
        return roles

    def _build_project_template_role(self, permission: str) -> Optional[Dict]:
        """Only responsible for ONE project role."""
        actions = get_project_actions(permission)
        # ...build and return one role dict
```

### Why this is good
- Each method is **testable in isolation**
- Easy to change one step without breaking others
- Each method has a **single responsibility** (SRP principle)
- Methods starting with `_` are private conventions in Python (not enforced, just convention)

---

## 5. List Comprehension for Filtering

### The concept

Build a new list by filtering or transforming an existing one — in one readable line.

```python
# LESSON: List comprehension syntax
# [expression for item in iterable if condition]

# Get only the used project permissions
used = [col for col in PROJECT_PERMISSION_MAP.keys()
        if col in self.project_matrix_df.columns
        and self.project_matrix_df[col].any()]

# Equivalent for-loop (more verbose):
used = []
for col in PROJECT_PERMISSION_MAP.keys():
    if col in self.project_matrix_df.columns:
        if self.project_matrix_df[col].any():
            used.append(col)
```

### set() to remove duplicates

```python
# After collecting role keys, a team might appear twice
# (once for critical env, once for non-critical)
# set() removes duplicates, list() converts back

return list(set(roles))   # deduplicate
```

---

## Quick Reference Card

```python
# Literal braces in f-strings
f"${{placeholder}}"          → "${placeholder}"

# Dict lookup with default
MAPPING.get(key, "default")  → value or "default"

# Three-state Optional
critical: Optional[bool] = None
# None = standard, True = critical, False = non-critical

# Private method convention
def _private_helper(self): ...   # _ prefix = internal use

# List comprehension with filter
[x for x in items if condition]

# Remove duplicates
list(set(my_list))
```
