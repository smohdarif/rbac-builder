# Phase 12: Design Document — Role Attribute Env Scoping + Role Correctness

**Status:** ✅ Complete
**Related:** [README](./README.md) | [PYTHON_CONCEPTS](./PYTHON_CONCEPTS.md)

---

## High-Level Design

### Problem 1: Environment scoping was unverified

The original plan used `*;{critical:true}` to match all LD environments with the `critical` property set.
This was never tested and requires LD admin setup outside our control.

### Problem 2: Generated roles didn't match existing LD accounts

Comparing the builder output against an existing LD account (Voya) revealed two gaps:
- Missing `createContextKind` / `updateContextKind` statements (ps-terraform includes these by default)
- Missing `base_permissions: "no_access"` (required LD API field)

### Solution

**For env scoping:** Use `${roleAttribute/<perm>-environments}` placeholders (sa-demo pattern).
Each team specifies exact env keys — no LD-side property setup needed.

**For role correctness:** Match ps-terraform's default `manage-flags/main.tf` behaviour exactly.

---

## Detailed Low-Level Design

### Change 1: Attribute key format

```python
# Before (camelCase — not matching sa-demo)
PERMISSION_ATTRIBUTE_MAP = {
    "Update Targeting": "updateTargetingEnvironments",
    "Apply Changes":    "applyChangesEnvironments",
    ...
}

# After (kebab-case — matches sa-demo exactly)
PERMISSION_ATTRIBUTE_MAP = {
    "Update Targeting": "update-targeting-environments",
    "Apply Changes":    "apply-changes-environments",
    ...
}
```

**Why kebab-case:** The sa-demo `teams/default/main.tf` uses:
```hcl
role_attributes { key = "update-targeting-environments" }
```
The attribute key in the role placeholder and the team `roleAttributes` block **must match exactly**. Case matters.

---

### Change 2: Remove criticality branching

**Before** (3 code paths):
```python
use_criticality = self._uses_criticality_pattern()
if use_criticality:
    # → generate critical-* and non-critical-* roles
    # → teams get only "projects" attribute (no env attrs)
else:
    # → generate single role with env attribute placeholder
    # → teams get per-permission env attributes
```

**After** (1 code path — always role attribute):
```python
# Always: one role per permission, env scoped via roleAttribute
for permission in used_env_perms:
    role = self._build_env_template_role(permission)
    if role:
        roles.append(role)
```

The helper methods `_is_env_critical()`, `_get_critical_envs()`, `_get_non_critical_envs()`, `_uses_criticality_pattern()` remain available for env group inspection but no longer drive role generation.

---

### Change 3: Context kind statements

**Source:** `ps-terraform/roles/flag-lifecycle/per-project/manage-flags/main.tf`

```hcl
# ps-terraform default behaviour when manage_context_kinds = false (default):
create_context_kind = coalesce(var.manage_context_kinds_in_flag_roles, !var.manage_context_kinds)
# = coalesce(null, !false) = coalesce(null, true) = true
```

**Implementation:**

```python
# New constant in ld_actions.py
CONTEXT_KIND_ACTIONS_FOR_PERMISSION: Dict[str, List[str]] = {
    "Create Flags": ["createContextKind"],
    "Update Flags": ["updateContextKind", "updateAvailabilityForExperiments"],
}

# New resource builder
def build_context_kind_role_attribute_resource(project_attr: str = "projects") -> str:
    return f"proj/${{roleAttribute/{project_attr}}}:context-kind/*"
```

**In `_build_project_template_role()`:**
```python
context_kind_actions = CONTEXT_KIND_ACTIONS_FOR_PERMISSION.get(permission_name)
if context_kind_actions:
    policy.append({
        "effect": "allow",
        "actions": context_kind_actions,
        "resources": [build_context_kind_role_attribute_resource("projects")]
    })
```

---

### Change 4: base_permissions field

**Problem:** The LD API `POST /api/v2/roles` requires `base_permissions`. Without it the role is rejected or defaults to `reader`.

```python
# Added to BOTH _build_project_template_role() and _build_env_template_role()
return {
    "key": role_key,
    "name": role_name,
    "description": description,
    "base_permissions": "no_access",   # ← added
    "policy": policy
}
```

---

## Output Comparison

### Before Phase 12 — create-flags role

```json
{
  "key": "create-flags",
  "name": "Create Flags",
  "policy": [
    { "effect": "allow", "actions": ["cloneFlag", "createFlag"],
      "resources": ["proj/${roleAttribute/projects}:env/*:flag/*"] },
    { "effect": "allow", "actions": ["viewProject"],
      "resources": ["proj/${roleAttribute/projects}"] }
  ]
}
```

### After Phase 12 — create-flags role (matches LD account)

```json
{
  "key": "create-flags",
  "name": "Create Flags",
  "base_permissions": "no_access",
  "policy": [
    { "effect": "allow", "actions": ["cloneFlag", "createFlag"],
      "resources": ["proj/${roleAttribute/projects}:env/*:flag/*"] },
    { "effect": "allow", "actions": ["createContextKind"],
      "resources": ["proj/${roleAttribute/projects}:context-kind/*"] },
    { "effect": "allow", "actions": ["viewProject"],
      "resources": ["proj/${roleAttribute/projects}"] }
  ]
}
```

### Before Phase 12 — team roleAttributes (criticality mode)

```json
"roleAttributes": [
  { "key": "projects", "values": ["voya-web"] }
]
```

### After Phase 12 — team roleAttributes (role attribute env scoping)

```json
"roleAttributes": [
  { "key": "projects", "values": ["voya-web"] },
  { "key": "update-targeting-environments", "values": ["production", "staging"] },
  { "key": "apply-changes-environments", "values": ["production"] },
  { "key": "review-changes-environments", "values": ["production", "staging"] }
]
```

---

## Test Strategy

All tests in `tests/test_critical_environments.py` were rewritten:

| Test Group | What it verifies |
|------------|-----------------|
| `TestEnvGroupHelpers` | Helper methods still work for env group inspection |
| `TestRoleGeneration` | Single role per permission, no critical/non-critical split |
| `TestTeamRoleAssignment` | Team gets one role key per permission |
| `TestTeamRoleAttributes` | Per-permission env attributes with correct env values |
