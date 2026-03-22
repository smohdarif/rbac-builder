# Phase 16: Python Concepts

Concepts introduced when generating Terraform HCL from Python.

---

## Table of Contents

1. [String Escaping — When Output Has Special Characters](#1-string-escaping--when-output-has-special-characters)
2. [Building Multi-Line Strings with List + join()](#2-building-multi-line-strings-with-list--join)
3. [set() for Fast Membership Lookup](#3-set-for-fast-membership-lookup)
4. [Code Generation — The Same Pattern as deploy.py](#4-code-generation--the-same-pattern-as-deploypy)
5. [Quick Reference Card](#quick-reference-card)

---

## 1. String Escaping — When Output Has Special Characters

### The problem

Our JSON payload has role attribute placeholders:
```
proj/${roleAttribute/projects}:env/*:flag/*
```

HCL (Terraform's language) uses `${...}` as its own interpolation syntax. If you put `${roleAttribute/projects}` inside a Terraform string, Terraform tries to evaluate it as a variable reference — and fails.

**The fix: double the `$` → `$${`**

```python
resource_string = "proj/${roleAttribute/projects}:env/*:flag/*"

# In HCL, this would cause an interpolation error:
# "proj/${roleAttribute/projects}:env/*:flag/*"
#       ^^^ Terraform tries to interpolate this!

# Correct: escape the $ by doubling it
hcl_string = resource_string.replace("${", "$${")
# Result: "proj/$${roleAttribute/projects}:env/*:flag/*"
# HCL sees $${ → outputs literal ${ in the final string
```

### The pattern in code

```python
def hcl_list_escaped(resources: list) -> str:
    """Format a list of resources for HCL, escaping ${ placeholders."""
    escaped = [r.replace("${", "$${") for r in resources]
    items   = ", ".join(f'"{e}"' for e in escaped)
    return f"[{items}]"

# Example:
hcl_list_escaped(["proj/${roleAttribute/projects}:env/*:flag/*"])
# → '["proj/$${roleAttribute/projects}:env/*:flag/*"]'
```

### Same issue in Phase 13's deploy.py generator

We saw this same pattern in Phase 13 when generating `deploy.py` inside an f-string — `{{` and `}}` produced literal `{` and `}`. The principle is the same: **escape special characters when generating code that has its own syntax**.

---

## 2. Building Multi-Line Strings with List + join()

### The concept

HCL blocks have structured indentation. Building them by concatenating strings (`+=`) is error-prone. The cleaner pattern: collect lines in a list, join at the end.

```python
# BAD — string concatenation (hard to read, error-prone)
hcl = f'resource "launchdarkly_custom_role" "{name}" {{\n'
hcl += f'  key = "{key}"\n'
hcl += f'  name = "{display_name}"\n'
hcl += '}\n'

# GOOD — list of lines, joined at the end
lines = [
    f'resource "launchdarkly_custom_role" "{name}" {{',
    f'  key              = "{key}"',
    f'  name             = "{display_name}"',
    f'  base_permissions = "no_access"',
    "}",
]
hcl = "\n".join(lines)
```

### For nested blocks (policy_statements)

```python
def _policy_statement_hcl(stmt: dict) -> list:
    """Returns lines for one policy_statements block."""
    return [
        "  policy_statements {",
        f'    effect    = "{stmt["effect"]}"',
        f'    actions   = {hcl_list(stmt["actions"])}',
        f'    resources = {hcl_list_escaped(stmt["resources"])}',
        "  }",
    ]

# Build all lines for a role
lines = [f'resource "launchdarkly_custom_role" "{name}" {{', ...]
for stmt in role["policy"]:
    lines.extend(_policy_statement_hcl(stmt))
    lines.append("")   # blank line between statements
lines.append("}")
```

### Joining sections with blank lines

```python
sections = [
    header_comment,
    roles_section,
    teams_section,
]
main_tf = "\n\n".join(sections)  # blank line between each section
```

---

## 3. set() for Fast Membership Lookup

### The problem

A team's `customRoleKeys` might reference role keys that aren't in the payload (e.g., global roles like `view_teams` that we don't generate). If we generate TF references to those non-existent resources, `terraform plan` will fail.

### The solution: filter by what's in the payload

```python
# Collect all role keys we're generating
role_keys = {role["key"] for role in payload.roles}  # set comprehension
#                                                      ↑ {} creates a set, not a dict

# Only reference roles we generated
role_refs = [
    f"launchdarkly_custom_role.{tf_resource_name(k)}.key"
    for k in team["customRoleKeys"]
    if k in role_keys   # O(1) lookup — set is much faster than list for 'in'
]
```

### set() vs list() for 'in' checks

```python
my_list = ["a", "b", "c", "d", "e"]   # O(n) for 'in' check
my_set  = {"a", "b", "c", "d", "e"}   # O(1) for 'in' check

# For small collections the difference doesn't matter
# But it's good practice to use set when you only need membership testing

"a" in my_list   # scans list linearly
"a" in my_set    # hash lookup, instant
```

### set comprehension vs list comprehension

```python
# List comprehension: [ ]
names_list = [r["key"] for r in roles]

# Set comprehension: { }  — removes duplicates automatically
names_set  = {r["key"] for r in roles}

# Dict comprehension: {k: v}
names_dict = {r["key"]: r["name"] for r in roles}
```

---

## 4. Code Generation — The Same Pattern as deploy.py

### The concept

In Phase 13, we generated `deploy.py` (Python code) as a string. In Phase 16, we generate `main.tf` (HCL code) as a string. Same pattern, different target language.

```
Phase 13: Python string → deploy.py (Python code)
Phase 16: Python string → main.tf  (HCL code)
```

### Key differences between the two

| | Phase 13: deploy.py | Phase 16: main.tf |
|-|---------------------|-------------------|
| Language of output | Python | HCL (Terraform) |
| Special char to escape | `{` in f-strings → `{{` | `${` in HCL strings → `$${` |
| Method | Big template string + `.replace()` | Line-by-line list + `.join()` |
| Why different method? | deploy.py has complex Python logic (classes, methods) | main.tf is structured data blocks — line building is cleaner |

### Why line-by-line for HCL (not a big template)?

HCL has a regular, predictable structure. Every block looks the same. It's easier to loop over the payload data and emit lines than to have a huge template with placeholders.

```python
# For deploy.py (complex Python logic) → template + replace is cleaner
template = """
class LDClient:
    def __init__(self, api_key):
        self.api_key = api_key
    ...
""".replace("__CUSTOMER__", customer_name)

# For main.tf (repetitive HCL blocks) → line building is cleaner
for role in payload.roles:
    lines.extend(_role_to_hcl(role))
```

---

## Quick Reference Card

```python
# Escape ${ in strings for HCL
hcl_safe = resource_string.replace("${", "$${")

# Format a Python list as HCL list
def hcl_list(values):
    return "[" + ", ".join(f'"{v}"' for v in values) + "]"

# Build HCL block as list of lines, join at end
lines = [
    f'resource "launchdarkly_custom_role" "{name}" {{',
    f'  key = "{key}"',
    "}",
]
hcl_block = "\n".join(lines)

# Join multiple blocks with blank line between
main_tf = "\n\n".join([block1, block2, block3])

# set comprehension for fast lookup
role_keys = {role["key"] for role in payload.roles}
if key in role_keys: ...   # O(1)

# Filter list using set membership
valid_refs = [k for k in keys if k in role_keys]
```
