# Pseudo Logic & Test Cases: Role Attribute Pattern

**Status:** Reference Document — Updated to reflect rbac-builder implementation
**Related:** [HLD](./HLD.md) | [DLD](./DLD.md)

> **Implementation note:** `services/payload_builder.py` (`RoleAttributePayloadBuilder`) and
> `core/ld_actions.py` (`PERMISSION_ATTRIBUTE_MAP`) implement this pattern.
> Env attribute keys use kebab-case (e.g., `update-targeting-environments`) matching
> the sa-demo/ps-terraform convention.

---

## Table of Contents

1. [Pseudo Logic](#pseudo-logic)
   - [Building Role Templates](#1-building-role-templates)
   - [Building a Team](#2-building-a-team)
   - [LD Policy Evaluation at Runtime](#3-ld-policy-evaluation-at-runtime)
2. [Test Cases](#test-cases)
   - [Role Template Tests](#group-1-role-template-tests)
   - [Team Role Attribute Tests](#group-2-team-role-attribute-tests)
   - [Policy Evaluation Tests](#group-3-policy-evaluation-tests)
   - [Edge Case Tests](#group-4-edge-case-tests)
   - [Integration Tests](#group-5-integration-tests)

---

## Pseudo Logic

### 1. Building Role Templates

This runs once per LD account (or per customer deployment).
Implemented in: `RoleAttributePayloadBuilder._build_template_roles()`

```
FUNCTION build_role_templates(config):

  # --- Project-level roles ---
  # Resource uses env/* wildcard (project roles apply across all environments)
  FOR each per_project_role in config.project_roles:
    role = {
      key:              per_project_role.key,
      name:             per_project_role.name,
      base_permissions: "no_access",
      policy: [
        {
          effect:    "allow",
          actions:   per_project_role.actions,
          resources: ["proj/${roleAttribute/projects}:env/*:flag/*"]
        },
        {
          effect:    "allow",
          actions:   ["viewProject"],
          resources: ["proj/${roleAttribute/projects}"]
        }
      ]
    }
    CREATE role in LD

  # --- Environment-level roles ---
  # ONE role per permission — always.
  # No critical/non-critical split. Environment scoping is done via roleAttributes on teams.
  # env_attr_key uses kebab-case: "update-targeting-environments", "apply-changes-environments", etc.
  FOR each per_env_role in config.env_roles:
    env_attr_key = per_env_role.key + "-environments"
    # e.g., "update-targeting" + "-environments" → "update-targeting-environments"

    role = {
      key:              per_env_role.key,
      name:             per_env_role.name,
      base_permissions: "no_access",
      policy: [
        {
          effect:    "allow",
          actions:   per_env_role.actions,
          resources: [
            "proj/${roleAttribute/projects}:env/${roleAttribute/" + env_attr_key + "}:flag/*"
          ]
        },
        {
          effect:    "allow",
          actions:   ["viewProject"],
          resources: ["proj/${roleAttribute/projects}"]
        }
      ]
    }
    CREATE role in LD

END FUNCTION
```

---

### 2. Building a Team

This runs once per team (per customer, per project group).
Implemented in: `RoleAttributePayloadBuilder._build_teams_with_attributes()`

```
FUNCTION build_team(team_config, available_roles):

  # Step 1: Collect role keys the team needs
  role_keys = []

  FOR each project_permission in team_config.project_permissions:
    IF project_permission.enabled == true:
      role_keys.APPEND(available_roles.project[project_permission.name].key)

  FOR each env_permission in team_config.env_permissions:
    IF env_permission.environments is not empty:
      role_keys.APPEND(available_roles.environment[env_permission.name].key)

  # Step 2: Build role_attributes
  role_attributes = []

  # Always add project attribute — fills ${roleAttribute/projects} in all roles
  role_attributes.APPEND({
    key:    "projects",
    values: team_config.projects   # e.g., ["voya-web"]
  })

  # Add per-role env attributes for EVERY env permission the team has enabled.
  # attr_key uses kebab-case matching the role's ${roleAttribute/...} placeholder.
  # e.g., "Update Targeting" → attr_key = "update-targeting-environments"
  # The values are the exact LD environment keys the team can access for that permission.
  FOR each env_permission in team_config.env_permissions:
    IF env_permission.environments is not empty:
      attr_key = slugify(env_permission.name) + "-environments"
      role_attributes.APPEND({
        key:    attr_key,
        values: env_permission.environments  # e.g., ["production", "staging"]
      })

  # Step 3: Create team in LD
  team = {
    key:             team_config.key,
    name:            team_config.name,
    customRoleKeys:  role_keys,
    roleAttributes:  role_attributes
  }
  CREATE team in LD

END FUNCTION
```

---

### 3. LD Policy Evaluation at Runtime

This runs inside LaunchDarkly every time a user performs an action.

```
FUNCTION evaluate_permission(user, action, target_resource):

  # Step 1: Find all teams the user belongs to
  user_teams = GET teams for user

  # Step 2: For each team, collect all roles
  FOR each team in user_teams:

    FOR each role_key in team.customRoleKeys:
      role = GET role by role_key

      FOR each policy_statement in role.policy:

        # Step 3: Resolve role attributes in resource strings
        resolved_resources = resolve_attributes(
          policy_statement.resources,
          team.roleAttributes
        )

        # Step 4: Check if target resource matches any resolved resource
        FOR each resolved_resource in resolved_resources:
          IF target_resource MATCHES resolved_resource:
            IF policy_statement.effect == "allow":
              RETURN ALLOWED ✅
            IF policy_statement.effect == "deny":
              RETURN DENIED ❌

  # Default: no matching policy found
  RETURN DENIED ❌ (base_permissions = no_access)

END FUNCTION


FUNCTION resolve_attributes(resource_templates, role_attributes):

  resolved = []

  FOR each template in resource_templates:

    # Find all ${roleAttribute/...} placeholders in the template
    placeholders = EXTRACT placeholders from template

    # Build value sets for each placeholder
    value_sets = []
    FOR each placeholder in placeholders:
      attr_key = placeholder.attribute_name
      attr_values = role_attributes[attr_key]

      IF attr_values is empty:
        SKIP this template (placeholder unresolvable → no access)
        CONTINUE

      value_sets.APPEND(attr_values)

    # Generate cartesian product of all value combinations
    combinations = CARTESIAN_PRODUCT(value_sets)

    FOR each combination in combinations:
      resolved_string = SUBSTITUTE placeholders in template with combination values
      resolved.APPEND(resolved_string)

  RETURN resolved

END FUNCTION
```

---

## Test Cases

### Group 1: Role Template Tests

These tests verify that role templates are structured correctly.

---

#### TC-RT-01: Per-environment role has correct resource pattern

```
GIVEN: role "update-targeting" is created
WHEN:  role policy is inspected
THEN:
  - policy[0].resources[0] == "proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*"
  - policy[0].effect == "allow"
  - policy[0].actions contains "updateOn"
  - policy[0].actions contains "updateRules"
  - policy[0].actions contains "createApprovalRequest"
  - policy[1].resources[0] == "proj/${roleAttribute/projects}"
  - policy[1].actions == ["viewProject"]
```

---

#### TC-RT-02: Per-project role does NOT include env placeholder

```
GIVEN: role "project-create-flags" is created
WHEN:  role policy is inspected
THEN:
  - policy[0].resources[0] does NOT contain "${roleAttribute/create-flags-environments}"
  - policy[0].resources[0] DOES contain "${roleAttribute/projects}"
  - policy[0].resources[0] contains "env/*"    (wildcard, not scoped)
```

---

#### TC-RT-03: Each env role uses its own unique env attribute key

```
GIVEN: roles ["update-targeting", "apply-changes", "review-changes"] are created
WHEN:  resource strings are inspected
THEN:
  - update-targeting resource contains "roleAttribute/update-targeting-environments"
  - apply-changes resource contains "roleAttribute/apply-changes-environments"
  - review-changes resource contains "roleAttribute/review-changes-environments"
  - all three attribute keys are DIFFERENT
```

---

#### TC-RT-04: base_permissions is no_access on all roles

```
GIVEN: all roles in the sa-demo are created
WHEN:  base_permissions is inspected for each role
THEN:
  - every role has base_permissions == "no_access"
  - no role has base_permissions == "reader" or "writer"
```

---

### Group 2: Team Role Attribute Tests

These tests verify that teams have the correct role assignments and attributes.

---

#### TC-TA-01: Team has correct role keys for assigned permissions

```
GIVEN: Developers team config:
  project perms:  [create_flags, update_flags, manage_metrics, view_project]
  env perms:      [update_targeting, review_changes, apply_changes, manage_segments,
                   manage_experiments, view_sdk_key]
WHEN:  team is created in LD
THEN:
  - customRoleKeys contains "project-create-flags"
  - customRoleKeys contains "project-update-flags"
  - customRoleKeys contains "project-manage-metrics"
  - customRoleKeys contains "project-view-project"
  - customRoleKeys contains "update-targeting"
  - customRoleKeys contains "review-changes"
  - customRoleKeys contains "apply-changes"
  - customRoleKeys contains "manage-segments"
  - customRoleKeys contains "manage-experiments"
  - customRoleKeys contains "view-sdk-key"
```

---

#### TC-TA-02: Team has role_attributes for every env role assigned

```
GIVEN: Developers team uses env roles:
  [update_targeting, review_changes, apply_changes, manage_segments,
   manage_experiments, view_sdk_key]
WHEN:  team roleAttributes are inspected
THEN:
  - roleAttributes has key "projects"
  - roleAttributes has key "update-targeting-environments"
  - roleAttributes has key "review-changes-environments"
  - roleAttributes has key "apply-changes-environments"
  - roleAttributes has key "manage-segments-environments"
  - roleAttributes has key "manage-experiments-environments"
  - roleAttributes has key "view-sdk-key-environments"
  - roleAttributes has NO key "bypass-required-approvals-environments"
    (SRE has this, not Developers)
```

---

#### TC-TA-03: Team does NOT have role_attributes for roles it doesn't use

```
GIVEN: Product Managers team uses ONLY project roles (no env roles)
WHEN:  team roleAttributes are inspected
THEN:
  - roleAttributes has key "projects"
  - roleAttributes does NOT have any "*-environments" keys
  - customRoleKeys does NOT contain any env role keys
```

---

#### TC-TA-04: Different teams can have different envs for same role

```
GIVEN:
  Developers team:     apply-changes-environments = ["production"]
  SRE team:           bypass-required-approvals-environments = ["production", "staging", "test"]
WHEN:  both teams' roleAttributes are compared
THEN:
  - Developers apply-changes scopes to 1 environment
  - SRE bypass-required-approvals scopes to 3 environments
  - These are independent — changing one does not affect the other
```

---

#### TC-TA-05: Team key follows naming convention

```
GIVEN: key_format = "default-%s" and team base key = "developers"
WHEN:  team is created
THEN:
  - team.key == "default-developers"
  - team.name == "Default: Developers"
```

---

### Group 3: Policy Evaluation Tests

These tests verify LD resolves permissions correctly for a user at runtime.

---

#### TC-PE-01: User can perform action on explicitly listed environment

```
GIVEN:
  User is member of Developers team
  Developers team has:
    role: update-targeting
    role_attributes: update-targeting-environments = ["production", "staging"]
WHEN:  user tries to updateOn a flag in project "default", env "production"
THEN:  ALLOWED ✅
```

---

#### TC-PE-02: User CANNOT perform action on environment NOT in their list

```
GIVEN:
  User is member of Developers team
  Developers team has:
    role: update-targeting
    role_attributes: update-targeting-environments = ["production", "staging"]
WHEN:  user tries to updateOn a flag in project "default", env "test"
THEN:  DENIED ❌
```

---

#### TC-PE-03: User with apply-changes CAN apply in listed env

```
GIVEN:
  User is member of Developers team
  Developers team has:
    role: apply-changes
    role_attributes: apply-changes-environments = ["production"]
WHEN:  user tries to applyApprovalRequest in project "default", env "production"
THEN:  ALLOWED ✅
```

---

#### TC-PE-04: User with apply-changes CANNOT apply in staging (not listed)

```
GIVEN:
  User is member of Developers team
  Developers team has:
    role: apply-changes
    role_attributes: apply-changes-environments = ["production"]
    (note: update-targeting-environments = ["production", "staging"])
WHEN:  user tries to applyApprovalRequest in project "default", env "staging"
THEN:  DENIED ❌
  (apply-changes only resolves to production, even though user can update-targeting in staging)
```

---

#### TC-PE-05: User CANNOT access a different project

```
GIVEN:
  User is member of "default" Developers team
  Developers team has:
    role_attributes: projects = ["default"]
WHEN:  user tries to updateOn a flag in project "other-project", env "production"
THEN:  DENIED ❌
  (role resolves to proj/default:env/production:flag/*, not proj/other-project:...)
```

---

#### TC-PE-06: User with project-level role can act on all environments for that action

```
GIVEN:
  User is member of Developers team
  Developers team has:
    role: project-update-flags
    role_attributes: projects = ["default"]
WHEN:  user tries to updateName on a flag in project "default", env "test"
THEN:  ALLOWED ✅
  (project-update-flags resource is proj/${projects}:env/*:flag/* — env wildcard)
```

---

### Group 4: Edge Case Tests

---

#### TC-EC-01: Missing role_attribute → no access (fails closed)

```
GIVEN:
  Team has role "update-targeting" assigned
  Team has role_attributes: projects = ["default"]
  Team is MISSING: update-targeting-environments attribute
WHEN:  LD tries to resolve the role for a user action
THEN:
  - placeholder "${roleAttribute/update-targeting-environments}" cannot be resolved
  - no resources are generated for this policy statement
  - user is DENIED ❌ (not given blanket access)
```

---

#### TC-EC-02: Empty values list → no access

```
GIVEN:
  Team has role_attributes:
    update-targeting-environments = []   ← empty list
WHEN:  LD tries to resolve
THEN:  DENIED ❌ (no values to substitute → no resources generated)
```

---

#### TC-EC-03: Multiple environments in attribute values resolves to multiple resources

```
GIVEN:
  role_attributes: manage-experiments-environments = ["production", "staging", "test"]
WHEN:  role resource is resolved
THEN:
  Resolved resources:
    - "proj/default:env/production:experiment/*"
    - "proj/default:env/staging:experiment/*"
    - "proj/default:env/test:experiment/*"
  All three environments are accessible ✅
```

---

#### TC-EC-04: Role attribute key mismatch → no access

```
GIVEN:
  Role resource uses: "${roleAttribute/apply-changes-environments}"
  Team has attribute: key = "apply_changes_environments"  ← underscore, not hyphen
WHEN:  LD evaluates
THEN:  DENIED ❌
  (key names are case and character sensitive — hyphen ≠ underscore)
```

---

#### TC-EC-05: User in multiple teams gets union of permissions

```
GIVEN:
  User is member of BOTH:
    - Developers team: update-targeting-environments = ["production"]
    - SRE team: bypass-required-approvals-environments = ["production", "staging", "test"]
WHEN:  user tries to updateOn a flag in env "production"
THEN:  ALLOWED ✅  (from Developers team)
WHEN:  user tries to bypassRequiredApproval in env "staging"
THEN:  ALLOWED ✅  (from SRE team)
WHEN:  user tries to updateOn a flag in env "test"
THEN:  DENIED ❌   (Developers can't, SRE can't update-targeting, only bypass)
```

---

### Group 5: Integration Tests

Full end-to-end scenarios that validate the whole setup.

---

#### TC-INT-01: Developers team full permission matrix

```
SETUP:
  Project: "default" with environments: [production, staging, test, dev]
  Team: default-developers
    project roles: [create_flags, update_flags, manage_metrics, view_project]
    env roles + attributes:
      update-targeting:   [production, staging]
      review-changes:     [production, staging]
      apply-changes:      [production]
      manage-segments:    [production]
      manage-experiments: [production, staging, test]
      view-sdk-key:       [production, staging]

TEST MATRIX:
  Action               Env           Expected
  ─────────────────────────────────────────────
  createFlag           production    ALLOWED  ✅ (project role, env wildcard)
  createFlag           dev           ALLOWED  ✅ (project role, env wildcard)
  updateName (flag)    staging       ALLOWED  ✅ (project role, env wildcard)
  updateOn (flag)      production    ALLOWED  ✅ (update-targeting-envs includes production)
  updateOn (flag)      staging       ALLOWED  ✅ (update-targeting-envs includes staging)
  updateOn (flag)      test          DENIED   ❌ (test not in update-targeting-envs)
  updateOn (flag)      dev           DENIED   ❌ (dev not in update-targeting-envs)
  applyApproval        production    ALLOWED  ✅ (apply-changes-envs includes production)
  applyApproval        staging       DENIED   ❌ (staging not in apply-changes-envs)
  viewSdkKey           staging       ALLOWED  ✅ (view-sdk-key-envs includes staging)
  viewSdkKey           test          DENIED   ❌ (test not in view-sdk-key-envs)
  createExperiment     test          ALLOWED  ✅ (manage-experiments-envs includes test)
  createExperiment     dev           DENIED   ❌ (dev not in manage-experiments-envs)
  updateGlobalArchived production    ALLOWED  ✅ (archive-flags is project role, env wildcard)
```

---

#### TC-INT-02: SRE team — bypass approvals across all envs, no flag changes

```
SETUP:
  Team: default-sre
    project roles: [manage_metrics, view_project]
    env roles + attributes:
      bypass-required-approvals: [production, staging, test]

TEST MATRIX:
  Action                  Env           Expected
  ────────────────────────────────────────────────────
  bypassRequiredApproval  production    ALLOWED  ✅
  bypassRequiredApproval  staging       ALLOWED  ✅
  bypassRequiredApproval  test          ALLOWED  ✅
  bypassRequiredApproval  dev           DENIED   ❌ (dev not in attribute)
  updateOn (flag)         production    DENIED   ❌ (SRE has no update-targeting role)
  applyApproval           production    DENIED   ❌ (SRE has no apply-changes role)
  createFlag              any           DENIED   ❌ (SRE has no create-flags role)
```

---

#### TC-INT-03: Two projects, same team pattern

```
SETUP:
  Two team modules instantiated:
    module "default_teams"     → role_attributes: projects = ["default"]
    module "labs_project_teams" → role_attributes: projects = ["labs-project"]

VERIFY:
  - default-developers CAN act in project "default"
  - default-developers CANNOT act in project "labs-project"
  - labs-project-developers CAN act in project "labs-project"
  - labs-project-developers CANNOT act in project "default"
  - Both teams use the SAME shared role templates (e.g., "update-targeting")
  - Role template key is the same: "update-targeting"
  - Scoping is achieved entirely by role_attributes, not by separate roles
```

---

## Summary: What to Validate Before Going Live

| # | Check | How |
|---|-------|-----|
| 1 | All role templates created in LD | LD UI → Roles → verify keys exist |
| 2 | All roles have `no_access` base permissions | LD UI → inspect each role |
| 3 | Resource strings contain `${roleAttribute/...}` placeholders | LD API GET /roles |
| 4 | Each team has correct role keys assigned | LD UI → Teams → inspect |
| 5 | Each team has role_attributes for every env role | LD API GET /teams/{key} |
| 6 | Role attribute key names match placeholder names exactly | Compare role resource vs team attribute key |
| 7 | Test user in Developers can update flag in production | LD UI as test user |
| 8 | Test user in Developers CANNOT update flag in test env | LD UI as test user |
| 9 | Test user in Developers CANNOT apply changes in staging | LD UI as test user |
| 10 | Test user CANNOT access a different project | LD UI as test user |

---

## Navigation

- [← HLD](./HLD.md)
- [← DLD](./DLD.md)
