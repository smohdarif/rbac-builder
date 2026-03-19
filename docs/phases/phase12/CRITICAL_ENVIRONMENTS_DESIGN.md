# Phase 12: Critical vs Non-Critical Environments

## Overview

| Field | Value |
|-------|-------|
| Phase | 12 |
| Status | ✅ Implemented — via role attribute pattern (see decision note below) |
| Goal | Different permissions for production vs development environments |
| Reference | ps-terraform-private sa-demo, Excel Template |

---

## ⚠️ Implementation Decision

> **We did NOT implement the `{critical:true}` wildcard approach described below.**
>
> After analysis of the sa-demo (`ps-terraform-private-customer-sa-demo`), we chose the
> **role attribute pattern** instead:
> - Each env role uses `${roleAttribute/<perm>-environments}` as a placeholder
> - Teams specify exact environment keys via `roleAttributes`
> - No LD-side `critical` property setup required
> - Explicit, testable, and proven in production (sa-demo)
>
> **See:** `docs/role-attribute-pattern/` for the full HLD, DLD, and test cases.
>
> The rest of this document is preserved as a **design artifact** showing the
> alternative approach that was considered and why it was not chosen.

---

---

## Key Discovery: Column-Based Detection (Approach B)

> **Source:** Excel Template + Current RBAC Builder UI

### The Pattern

The RBAC Builder UI already captures a **Critical column** for each environment group. We use this column value (not the key name) to determine how to generate roles.

### Real-World Environment Groups (Multiple Environments)
```
┌────────────┬────────────────────┬──────────┬─────────────────────────┐
│ Key        │ Requires Approvals │ Critical │ Notes                   │
├────────────┼────────────────────┼──────────┼─────────────────────────┤
│ Dev        │ ☐                  │ ☐        │ Development             │
│ QA         │ ☐                  │ ☐        │ Quality Assurance       │
│ Staging    │ ☐                  │ ☐        │ Pre-production testing  │
│ INT        │ ☐                  │ ☐        │ Integration testing     │
│ Production │ ☑                  │ ☑        │ Live production         │
│ DR         │ ☑                  │ ☑        │ Disaster Recovery       │
└────────────┴────────────────────┴──────────┴─────────────────────────┘
```

### How It Works

1. **Payload builder checks Critical column** for each environment group
2. **Groups environments** into critical vs non-critical based on column value
3. **Generates TWO role sets** if both types exist:
   - `non-critical-*` roles with `*;{critical:false}` resource specifier
   - `critical-*` roles with `*;{critical:true}` resource specifier
4. **LaunchDarkly wildcard matching**: The `*;{critical:true}` specifier matches ALL environments in LD that have their `critical` flag set to true (Production, DR in example above)

### Key Insight

**No UI changes needed!** The Critical column already exists:
1. User marks each environment as Critical or not (checkbox)
2. Environment matrix has rows per team×environment (as before)
3. Payload builder groups by Critical column value and generates appropriate roles

---

## Problem Statement

Currently, RBAC Builder treats all environments the same. A team with "Update Targeting" permission gets it for ALL environments (Test, Production, etc.).

**Enterprise Need:** Different access levels based on environment criticality:
- **Non-Critical** (dev, test, staging): Direct access, no approvals needed
- **Critical** (production): Restricted access, approvals required

---

## Solution from ps-terraform-private

### LaunchDarkly Environment Property

LaunchDarkly environments have a built-in `critical` boolean property:
- `critical: true` → Production environments
- `critical: false` → Development/staging environments

### Resource Specifier Syntax

```hcl
# Match ALL critical environments
environments = ["*;{critical:true}"]

# Match ALL non-critical environments
environments = ["*;{critical:false}"]
```

### Two Sets of Roles

ps-terraform-private creates **TWO separate role modules**:

```hcl
module "non_critical_roles" {
  source       = "./roles/flag-lifecycle/per-environment"
  key_format   = "non-critical-%s"
  name_format  = "Non-Critical Environments: %s"
  environments = ["*;{critical:false}"]

  apply_changes    = true
  update_targeting = true
  # ...
}

module "critical_roles" {
  source       = "./roles/flag-lifecycle/per-environment"
  key_format   = "critical-%s"
  name_format  = "Critical Environments: %s"
  environments = ["*;{critical:true}"]

  apply_changes    = true
  update_targeting = true
  # ...
}
```

### Teams Get Both Sets

```hcl
resource "launchdarkly_team" "developers" {
  custom_role_keys = setunion(
    # Non-critical roles
    var.roles.environment.noncritical[*].update_targeting,
    var.roles.environment.noncritical[*].apply_changes,

    # Critical roles
    var.roles.environment.critical[*].update_targeting,
    var.roles.environment.critical[*].apply_changes,
  )
}
```

---

## High-Level Design (HLD)

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TEMPLATE ROLES                                       │
│                                                                              │
│  NON-CRITICAL ROLES                    CRITICAL ROLES                        │
│  ───────────────────                   ──────────────                        │
│  • non-critical-update-targeting       • critical-update-targeting           │
│  • non-critical-apply-changes          • critical-apply-changes              │
│  • non-critical-review-changes         • critical-review-changes             │
│  • non-critical-manage-segments        • critical-manage-segments            │
│                                                                              │
│  Resource: proj/${roleAttribute/       Resource: proj/${roleAttribute/       │
│    projects}:env/*;{critical:false}      projects}:env/*;{critical:true}     │
│    :flag/*                               :flag/*                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TEAM                                            │
│  key: voya-web-dev                                                          │
│  name: Voya Web: Developer                                                  │
│                                                                              │
│  customRoleKeys: [                                                          │
│    "non-critical-update-targeting",  ← Has in non-critical                  │
│    "non-critical-apply-changes",                                            │
│    "critical-update-targeting",      ← Also has in critical (maybe subset) │
│    "critical-review-changes",        ← Different permissions per env type  │
│  ]                                                                          │
│                                                                              │
│  roleAttributes: [                                                          │
│    { key: "projects", values: ["voya-web"] }                                │
│  ]                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input (Setup Tab)              Generated Output
─────────────────────               ────────────────

Environment Groups:                 NON-CRITICAL Roles:
┌─────────────────────────┐        • non-critical-update-targeting
│ Key     │ Critical      │        • non-critical-apply-changes
├─────────┼───────────────┤
│ Test    │ ☐ (false)     │        CRITICAL Roles:
│ Staging │ ☐ (false)     │        • critical-update-targeting
│ Prod    │ ☑ (true)      │        • critical-apply-changes
└─────────┴───────────────┘

Permission Matrix:                  Team with BOTH role sets:
┌──────────┬─────────┬──────────┐  customRoleKeys: [
│ Team     │ Non-Crit│ Critical │    "non-critical-update-targeting",
├──────────┼─────────┼──────────┤    "critical-review-changes",
│ Dev      │ ☑ Targ  │ ☐ Targ   │  ]
│          │ ☑ Apply │ ☐ Apply  │
│          │ ☐ Review│ ☑ Review │
└──────────┴─────────┴──────────┘
```

---

## Detailed Low-Level Design (DLD)

### 1. UI Changes - Environment Groups Editor

**✅ NO CHANGES NEEDED** - Already has Critical column!

**Example with Multiple Environments:**
```
┌────────────┬────────────────────┬──────────┬─────────────────────────┐
│ Key        │ Requires Approvals │ Critical │ Notes                   │
├────────────┼────────────────────┼──────────┼─────────────────────────┤
│ Dev        │ ☐                  │ ☐        │ Development             │
│ QA         │ ☐                  │ ☐        │ Quality Assurance       │
│ Staging    │ ☐                  │ ☐        │ Pre-production testing  │
│ INT        │ ☐                  │ ☐        │ Integration testing     │
│ Production │ ☑                  │ ☑        │ Live production         │
│ DR         │ ☑                  │ ☑        │ Disaster Recovery       │
└────────────┴────────────────────┴──────────┴─────────────────────────┘
```

User marks each environment as Critical (☑) or non-critical (☐) using the checkbox.

### 2. UI Changes - Environment Matrix

**✅ NO CHANGES NEEDED** - Current combined matrix works!

**Example with Multiple Environments:**
```
┌─────────────┬─────────────┬──────────────────┬────────────────┬───────────────┐
│ Team        │ Environment │ Update Targeting │ Review Changes │ Apply Changes │
├─────────────┼─────────────┼──────────────────┼────────────────┼───────────────┤
│ Developers  │ Dev         │ ✓                │ ☐              │ ✓             │
│ Developers  │ QA          │ ✓                │ ☐              │ ✓             │
│ Developers  │ Staging     │ ✓                │ ✓              │ ☐             │
│ Developers  │ INT         │ ✓                │ ✓              │ ☐             │
│ Developers  │ Production  │ ☐                │ ✓              │ ☐             │
│ Developers  │ DR          │ ☐                │ ✓              │ ☐             │
└─────────────┴─────────────┴──────────────────┴────────────────┴───────────────┘
```

The payload builder will:
1. Look up each environment's Critical flag from env_groups
2. Group permissions by Critical (true/false)
3. Generate appropriate role assignments

### 3. Payload Builder Changes (ONLY CHANGES NEEDED)

#### New Role Generation Logic

```python
def _build_template_roles(self) -> List[Dict[str, Any]]:
    roles = []

    # Check if we have critical environments defined
    has_critical = self._has_critical_environments()
    has_non_critical = self._has_non_critical_environments()

    if has_critical and has_non_critical:
        # Generate TWO sets of roles
        for permission in used_env_perms:
            # Non-critical role
            non_critical_role = self._build_env_template_role(
                permission,
                critical=False,
                key_prefix="non-critical-",
                name_prefix="Non-Critical: "
            )
            roles.append(non_critical_role)

            # Critical role
            critical_role = self._build_env_template_role(
                permission,
                critical=True,
                key_prefix="critical-",
                name_prefix="Critical: "
            )
            roles.append(critical_role)
    else:
        # Current behavior - single set of roles
        for permission in used_env_perms:
            role = self._build_env_template_role(permission)
            roles.append(role)

    return roles
```

#### New Resource String Format

```python
def _build_critical_env_resource(self, project_attr: str, resource_type: str) -> str:
    """Build resource for critical environments only."""
    return f"proj/${{roleAttribute/{project_attr}}}:env/*;{{critical:true}}:{resource_type}/*"

def _build_non_critical_env_resource(self, project_attr: str, resource_type: str) -> str:
    """Build resource for non-critical environments only."""
    return f"proj/${{roleAttribute/{project_attr}}}:env/*;{{critical:false}}:{resource_type}/*"
```

### 4. Output JSON Format

#### Roles (Two Sets)

```json
{
  "custom_roles": [
    {
      "key": "non-critical-update-targeting",
      "name": "Non-Critical: Update Targeting",
      "policy": [{
        "effect": "allow",
        "actions": ["updateOn", "updateRules", "..."],
        "resources": ["proj/${roleAttribute/projects}:env/*;{critical:false}:flag/*"]
      }]
    },
    {
      "key": "critical-update-targeting",
      "name": "Critical: Update Targeting",
      "policy": [{
        "effect": "allow",
        "actions": ["updateOn", "updateRules", "..."],
        "resources": ["proj/${roleAttribute/projects}:env/*;{critical:true}:flag/*"]
      }]
    }
  ]
}
```

#### Teams (Reference Both Sets)

```json
{
  "teams": [{
    "key": "voya-web-dev",
    "name": "Voya Web: Developer",
    "customRoleKeys": [
      "non-critical-update-targeting",
      "non-critical-apply-changes",
      "non-critical-manage-segments",
      "critical-review-changes"
    ],
    "roleAttributes": [
      {"key": "projects", "values": ["voya-web"]}
    ]
  }]
}
```

---

## Pseudo Logic (Column-Based Detection - Approach B)

### 1. Detect Criticality Pattern (Check Critical Column)

```
FUNCTION get_critical_envs():
    """Get list of environment keys where Critical=True."""
    RETURN env_groups_df[env_groups_df["Critical"] == True]["Key"].tolist()

FUNCTION get_non_critical_envs():
    """Get list of environment keys where Critical=False."""
    RETURN env_groups_df[env_groups_df["Critical"] == False]["Key"].tolist()

FUNCTION is_env_critical(env_key):
    """Check if a specific environment is marked as Critical."""
    row = env_groups_df[env_groups_df["Key"] == env_key]
    IF row.empty:
        RETURN False
    RETURN row.iloc[0]["Critical"] == True

FUNCTION uses_criticality_pattern():
    """Check if env_groups has BOTH critical and non-critical environments."""
    critical_envs = get_critical_envs()
    non_critical_envs = get_non_critical_envs()
    RETURN len(critical_envs) > 0 AND len(non_critical_envs) > 0
```

### 2. Build Environment Template Roles (Column-Based)

```
FUNCTION build_env_template_roles():
    roles = []
    use_criticality = uses_criticality_pattern()

    FOR each permission IN used_env_permissions:
        IF use_criticality:
            # Create TWO roles with wildcard resource specifiers

            # Non-critical role (matches ALL envs where critical=false in LD)
            non_crit_role = {
                key: "non-critical-" + slugify(permission),
                name: "Non-Critical: " + permission,
                policy: [{
                    effect: "allow",
                    actions: get_env_actions(permission),
                    resources: ["proj/${roleAttribute/projects}:env/*;{critical:false}:flag/*"]
                }]
            }
            roles.append(non_crit_role)

            # Critical role (matches ALL envs where critical=true in LD)
            crit_role = {
                key: "critical-" + slugify(permission),
                name: "Critical: " + permission,
                policy: [{
                    effect: "allow",
                    actions: get_env_actions(permission),
                    resources: ["proj/${roleAttribute/projects}:env/*;{critical:true}:flag/*"]
                }]
            }
            roles.append(crit_role)
        ELSE:
            # Current behavior - one role per permission with env attribute placeholder
            role = build_env_template_role(permission)
            roles.append(role)

    RETURN roles
```

### 3. Get Team Role Keys (Column-Based Lookup)

```
FUNCTION get_team_role_keys(team_name, available_role_keys):
    roles = []
    use_criticality = uses_criticality_pattern()

    IF use_criticality:
        # Map environment matrix rows to critical/non-critical roles
        team_rows = env_matrix_df[env_matrix_df["Team"] == team_name]

        FOR each row IN team_rows:
            env_key = row["Environment"]
            env_is_critical = is_env_critical(env_key)  # Lookup Critical column!

            FOR each permission IN ENV_PERMISSIONS:
                IF row[permission] == True:
                    IF env_is_critical:
                        role_key = "critical-" + slugify(permission)
                    ELSE:
                        role_key = "non-critical-" + slugify(permission)

                    IF role_key IN available_role_keys:
                        roles.append(role_key)
    ELSE:
        # Current behavior - use permission-based role keys
        # (existing logic unchanged)

    RETURN deduplicate(roles)
```

### 4. Build Team Role Attributes (Criticality-Aware)

```
FUNCTION build_team_role_attributes(team_name):
    attributes = []
    use_criticality = uses_criticality_pattern()

    # Always add projects attribute
    attributes.append({
        key: "projects",
        values: [project_key]
    })

    IF use_criticality:
        # NO environment attributes needed!
        # The *;{critical:true/false} wildcard matches all environments
        # in LaunchDarkly that have the matching critical flag
        RETURN attributes
    ELSE:
        # Current behavior - add per-permission environment attributes
        FOR each permission IN env_permissions_used_by_team:
            env_attr_name = get_attribute_name(permission)
            allowed_envs = get_allowed_envs_for_permission(team_name, permission)
            attributes.append({
                key: env_attr_name,
                values: allowed_envs
            })

    RETURN attributes
```

### 5. Example Walkthrough

**Input (env_groups):**
```
Dev        → Critical: False
QA         → Critical: False
Staging    → Critical: False
Production → Critical: True
DR         → Critical: True
```

**Input (env_matrix for Developers):**
```
Dev        → Update Targeting: ✓, Apply Changes: ✓
QA         → Update Targeting: ✓, Apply Changes: ✓
Staging    → Update Targeting: ✓, Review Changes: ✓
Production → Review Changes: ✓
DR         → Review Changes: ✓
```

**Generated Roles:**
```
non-critical-update-targeting  → resource: *;{critical:false}
non-critical-apply-changes     → resource: *;{critical:false}
non-critical-review-changes    → resource: *;{critical:false}
critical-review-changes        → resource: *;{critical:true}
```

**Team Assignment:**
```
Developers → customRoleKeys: [
    "non-critical-update-targeting",   # Has in Dev, QA, Staging
    "non-critical-apply-changes",      # Has in Dev, QA
    "non-critical-review-changes",     # Has in Staging
    "critical-review-changes"          # Has in Production, DR
]
```

**Note:** No environment attributes needed - the wildcard `*;{critical:true/false}` in LaunchDarkly automatically matches all environments with the corresponding critical flag!

---

## Test Cases

### 1. Environment Groups Tests

```python
class TestCriticalEnvironments:
    def test_env_groups_has_critical_column(self):
        """Test that env_groups DataFrame has Critical column."""
        assert "Critical" in env_groups_df.columns

    def test_detect_critical_environments(self):
        """Test detection of critical environments."""
        env_groups = pd.DataFrame({
            "Key": ["Test", "Staging", "Production"],
            "Critical": [False, False, True]
        })
        builder = RoleAttributePayloadBuilder(env_groups_df=env_groups, ...)
        assert builder._has_critical_environments() == True
        assert builder._has_non_critical_environments() == True
```

### 2. Role Generation Tests

```python
class TestCriticalRoleGeneration:
    def test_generates_two_role_sets(self):
        """Test that two role sets are generated when critical envs exist."""
        payload = builder.build()

        # Should have both non-critical and critical roles
        role_keys = [r["key"] for r in payload.roles]
        assert "non-critical-update-targeting" in role_keys
        assert "critical-update-targeting" in role_keys

    def test_non_critical_resource_format(self):
        """Test non-critical resource uses correct specifier."""
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "non-critical-update-targeting")
        assert "*;{critical:false}" in role["policy"][0]["resources"][0]

    def test_critical_resource_format(self):
        """Test critical resource uses correct specifier."""
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "critical-update-targeting")
        assert "*;{critical:true}" in role["policy"][0]["resources"][0]
```

### 3. Team Assignment Tests

```python
class TestCriticalTeamAssignment:
    def test_team_gets_correct_non_critical_roles(self):
        """Test team gets non-critical roles based on matrix."""
        # Dev has Update Targeting for non-critical only
        payload = builder.build()
        dev_team = next(t for t in payload.teams if "dev" in t["key"])

        assert "non-critical-update-targeting" in dev_team["customRoleKeys"]
        assert "critical-update-targeting" not in dev_team["customRoleKeys"]

    def test_team_gets_mixed_roles(self):
        """Test team can have different permissions per env type."""
        # Dev has Apply in non-critical, Review in critical
        payload = builder.build()
        dev_team = next(t for t in payload.teams if "dev" in t["key"])

        assert "non-critical-apply-changes" in dev_team["customRoleKeys"]
        assert "critical-review-changes" in dev_team["customRoleKeys"]
```

---

## Implementation Plan (Simplified)

> **Key Insight:** No UI changes needed! Only payload builder logic changes.

### Step 1: Update ld_actions.py ✅ (Already has base functions)
- [ ] Add `build_critical_env_role_attribute_resource()` function
- [ ] Add `build_non_critical_env_role_attribute_resource()` function
- [ ] Add `is_critical_env_key()` helper function

### Step 2: Update Payload Builder (payload_builder.py)
- [ ] Add `_is_critical_env_key(env_key)` method - detects "critical" key
- [ ] Add `_is_non_critical_env_key(env_key)` method - detects "non-critical" key
- [ ] Add `_uses_criticality_pattern()` method - checks if using critical/non-critical keys
- [ ] Update `_build_env_template_role()` to:
  - Generate `non-critical-{permission}` role with `*;{critical:false}` resource
  - Generate `critical-{permission}` role with `*;{critical:true}` resource
- [ ] Update `_get_team_role_keys()` to map team permissions to correct role keys
- [ ] Update `_build_team_role_attributes()` - no environment attributes needed (wildcard `*` matches all)

### Step 3: Write Tests
- [ ] Create `tests/test_critical_environments.py`
- [ ] Test `_is_critical_env_key()` detection
- [ ] Test `_uses_criticality_pattern()` detection
- [ ] Test role generation with criticality pattern
- [ ] Test role generation without criticality pattern (backward compat)
- [ ] Test team role key assignment

### Step 4: Update Documentation
- [ ] Update TERRAFORM_PATTERNS.md (mark as implemented)
- [ ] Add usage examples to Phase 12 README

### What's NOT Needed (Simplified)
- ~~Update Environment Groups DataFrame~~ → Already has Critical column
- ~~Update UI editor~~ → Current UI works as-is
- ~~Update session state~~ → No changes needed
- ~~Update Environment Matrix~~ → Current combined matrix works
- ~~Split into two matrices~~ → Not needed per Excel template

---

## Questions to Resolve ✅ ANSWERED

> **Answers derived from:** Excel Template + User Requirements (Approach B)

### 1. UI Design Choice: Split matrix vs combined matrix?

**Answer: COMBINED MATRIX (Current UI is correct!)**

The current RBAC Builder already has the right structure:
- Environment Groups table with Critical checkbox column
- Environment Matrix with rows per team×environment

```
Current RBAC Builder - Environment Groups:
┌────────────┬────────────────────┬──────────┬───────────────────┐
│ Key        │ Requires Approvals │ Critical │ Notes             │
├────────────┼────────────────────┼──────────┼───────────────────┤
│ Dev        │ ☐                  │ ☐        │ Development       │
│ QA         │ ☐                  │ ☐        │ Quality Assurance │
│ Staging    │ ☐                  │ ☐        │ Pre-production    │
│ Production │ ☑                  │ ☑        │ Live production   │
└────────────┴────────────────────┴──────────┴───────────────────┘

Current RBAC Builder - Environment Matrix:
┌──────────┬─────────────┬──────────────────┬────────────────┐
│ Team     │ Environment │ Update Targeting │ Review Changes │
├──────────┼─────────────┼──────────────────┼────────────────┤
│ Dev      │ Dev         │ ✓                │ ☐              │
│ Dev      │ QA          │ ✓                │ ☐              │
│ Dev      │ Staging     │ ✓                │ ✓              │
│ Dev      │ Production  │ ☐                │ ✓              │
└──────────┴─────────────┴──────────────────┴────────────────┘
```

**No UI changes needed.** Payload builder looks up Critical column to determine role assignment.

### 2. Detection Approach: Key-based vs Column-based?

**Answer: COLUMN-BASED (Approach B) ✅**

- **NOT** based on key names like "non-critical" or "critical"
- **YES** based on the Critical column checkbox value

This is more flexible:
- User can have ANY environment names (Dev, QA, Staging, INT, Production, DR, etc.)
- User simply checks the Critical box for production-like environments
- Payload builder groups by Critical=true vs Critical=false

### 3. Multiple Environments Support?

**Answer: FULLY SUPPORTED**

Users can define any number of environments:
- Dev, QA, Staging, INT, UAT → all marked Critical=false
- Production, DR, Hotfix → all marked Critical=true

The `*;{critical:true/false}` wildcard in LaunchDarkly matches ALL environments with the corresponding critical flag.

### 4. Backward Compatibility?

**Answer: Automatic detection**

The payload builder checks if BOTH critical and non-critical environments exist:
- If YES → Generate split roles (`non-critical-*` and `critical-*`)
- If NO (all same criticality) → Use current behavior (per-permission roles)

This ensures existing configs continue to work.

---

## References

| Source | File |
|--------|------|
| **Excel Template** | `/RBAC/[Template] [S2] LD Custom Roles Planning.xlsx` |
| Role Module | `/ps-terraform-private/roles/flag-lifecycle/per-environment/` |
| Team Template | `/ps-terraform-private/teams/template/main.tf` |
| Examples | `/ps-terraform-private/examples/role-templates-project.tf` |
| Tag Example | `/ps-terraform-private/examples/tags.tf` |

---

## Appendix: Excel Template Structure

The Excel template `[Template] [S2] LD Custom Roles Planning.xlsx` contains:

### Sheet: Default

**Environment Settings (rows 2-9):**
- Describes the criticality pattern
- Default groups: `non-critical` and `critical`

**Per-Project Roles (rows 16-25):**
- Single matrix for project-level permissions
- Columns: Create Flags, Update Flags, Archive Flags, etc.

**Per-Environment Roles (rows 32-46):**
- Combined matrix with Team and Environment columns
- Environment values: `non-critical`, `critical`
- Each team has TWO rows (one per environment type)

### Sheet: Settings

Reference tables for available roles and their defaults.

---

*Last updated: 2026-03-18*
