# Detailed Low-Level Design: Role Attribute Pattern

**Status:** Reference Document
**Related:** [HLD](./HLD.md) | [Pseudo Logic & Tests](./PSEUDOLOGIC_AND_TESTS.md)

---

## Table of Contents

1. [Role Template Structure](#role-template-structure)
2. [Per-Project Roles (Detailed)](#per-project-roles-detailed)
3. [Per-Environment Roles (Detailed)](#per-environment-roles-detailed)
4. [Team Structure (Detailed)](#team-structure-detailed)
5. [Role Attribute Resolution](#role-attribute-resolution)
6. [Resource String Construction](#resource-string-construction)
7. [Complete Example: Developers Team](#complete-example-developers-team)
8. [Edge Cases & Rules](#edge-cases--rules)

---

## Role Template Structure

### How a Role Template is Defined (Terraform → LD API)

```hcl
# Terraform (sa-demo/main.tf)
module "update_targeting" {
  source       = "./roles/flag-lifecycle/per-environment/update-targeting"
  key          = "update-targeting"
  name         = "Update Targeting"
  projects     = ["$${roleAttribute/projects}"]
  environments = ["$${roleAttribute/update-targeting-environments}"]
  flags        = ["*"]
  segments     = ["*"]
}
```

This generates the following LD custom role via the Terraform provider:

```json
{
  "key": "update-targeting",
  "name": "Update Targeting",
  "basePermissions": "no_access",
  "policy": [
    {
      "effect": "allow",
      "actions": [
        "copyFlagConfigFrom", "copyFlagConfigTo", "createApprovalRequest",
        "updateExpiringTargets", "updateFallthrough", "updateFeatureWorkflows",
        "updateOffVariation", "updateOn", "updatePrerequisites", "updateRules",
        "updateScheduledChanges", "updateTargets"
      ],
      "resources": [
        "proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*"
      ]
    },
    {
      "effect": "allow",
      "actions": ["viewProject"],
      "resources": ["proj/${roleAttribute/projects}"]
    }
  ]
}
```

**Key detail:** The Terraform `$${}` escaping becomes `${}` in the actual LD API payload.

---

## Per-Project Roles (Detailed)

These roles scope to the project level. Environment does not matter.

### Resource Pattern
```
proj/${roleAttribute/projects}
proj/${roleAttribute/projects}:flag/*       (for flag metadata actions)
```

### Role Catalogue

| Role Key | Actions | Resource |
|----------|---------|----------|
| `project-create-flags` | `createFlag`, `cloneFlag` | `proj/${roleAttribute/projects}:env/*:flag/*` |
| `project-update-flags` | `updateName`, `updateDescription`, `updateTags`, `updateMaintainer`, ... | `proj/${roleAttribute/projects}:env/*:flag/*` |
| `project-archive-flags` | `updateGlobalArchived` | `proj/${roleAttribute/projects}:env/*:flag/*` |
| `project-update-client-side-availability` | `updateClientSideFlagAvailability` | `proj/${roleAttribute/projects}:env/*:flag/*` |
| `project-manage-metrics` | `createMetric`, `updateName`, `deleteMetric`, ... | `proj/${roleAttribute/projects}:metric/*` |
| `project-manage-release-pipelines` | `createReleasePipeline`, `updateReleasePipeline`, ... | `proj/${roleAttribute/projects}:release-pipeline/*` |
| `project-view-project` | `viewProject` | `proj/${roleAttribute/projects}` |

### Required Role Attribute
Every per-project role requires one attribute on the team:

```hcl
role_attributes {
  key    = "projects"
  values = ["my-project-key"]     # the LD project key
}
```

---

## Per-Environment Roles (Detailed)

These roles scope to specific environments. Each role has its **own** environment attribute key — this is what allows different env lists per permission.

### Resource Pattern
```
proj/${roleAttribute/projects}:env/${roleAttribute/<role-key>-environments}:flag/*
proj/${roleAttribute/projects}:env/${roleAttribute/<role-key>-environments}:segment/*
```

### Role Catalogue

| Role Key | Actions | Env Attribute Key | Resource Type |
|----------|---------|-------------------|---------------|
| `update-targeting` | `updateOn`, `updateRules`, `updateFallthrough`, `updateTargets`, `createApprovalRequest`, ... | `update-targeting-environments` | flag, segment |
| `review-changes` | `reviewApprovalRequest`, `updateApprovalRequest` | `review-changes-environments` | flag, segment |
| `apply-changes` | `applyApprovalRequest`, `updateApprovalRequest` | `apply-changes-environments` | flag, segment |
| `manage-segments` | `createSegment`, `deleteSegment`, `updateIncluded`, `updateExcluded`, `updateRules`, ... | `manage-segments-environments` | segment |
| `manage-experiments` | `createExperiment`, `updateExperiment`, `updateExperimentArchived` | `manage-experiments-environments` | experiment |
| `view-sdk-key` | `viewSdkKey` | `view-sdk-key-environments` | env |
| `bypass-required-approvals` | `bypassRequiredApproval` | `bypass-required-approvals-environments` | flag |

### Required Role Attributes (per role used)

For each environment role assigned to a team, a corresponding `role_attributes` block must exist:

```hcl
# If team uses update-targeting:
role_attributes {
  key    = "update-targeting-environments"
  values = ["production", "staging"]
}

# If team uses apply-changes:
role_attributes {
  key    = "apply-changes-environments"
  values = ["production"]     # narrower than update-targeting
}
```

---

## Team Structure (Detailed)

### Full Team Object (LD API)

```json
{
  "key": "default-developers",
  "name": "Default: Developers",
  "description": "Developers",
  "customRoleKeys": [
    "project-create-flags",
    "project-update-flags",
    "project-manage-metrics",
    "project-view-project",
    "update-targeting",
    "review-changes",
    "manage-experiments",
    "view-sdk-key",
    "apply-changes",
    "manage-segments"
  ],
  "roleAttributes": [
    { "key": "projects",                          "values": ["default"] },
    { "key": "update-targeting-environments",     "values": ["production", "staging"] },
    { "key": "review-changes-environments",       "values": ["production", "staging"] },
    { "key": "manage-experiments-environments",   "values": ["production", "staging", "test"] },
    { "key": "view-sdk-key-environments",         "values": ["production", "staging"] },
    { "key": "apply-changes-environments",        "values": ["production"] },
    { "key": "manage-segments-environments",      "values": ["production"] }
  ]
}
```

### Team Object Schema

```
Team
├── key                (string)       unique identifier, e.g. "default-developers"
├── name               (string)       display name
├── description        (string)
├── customRoleKeys     (string[])     list of role keys assigned to this team
└── roleAttributes     (object[])     substitution values for role placeholders
    ├── key            (string)       matches the roleAttribute name in the role resource
    └── values         (string[])     LD resource keys (project keys, env keys, etc.)
```

---

## Role Attribute Resolution

This is what happens inside LD when a user in a team tries to perform an action:

### Step 1: Collect team's role keys
```
Team "default-developers" has roles:
  ["project-create-flags", "update-targeting", "apply-changes", ...]
```

### Step 2: For each role, get the policy statements
```
Role "update-targeting" has resource:
  "proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*"
```

### Step 3: Look up role attributes on the team
```
Team role_attributes:
  projects                      = ["default"]
  update-targeting-environments = ["production", "staging"]
```

### Step 4: Generate cartesian product of all values
```
For each project in ["default"]:
  For each env in ["production", "staging"]:
    → "proj/default:env/production:flag/*"
    → "proj/default:env/staging:flag/*"
```

### Step 5: Evaluate user's action against resolved resources
```
User action: updateOn flag "my-flag" in project "default", env "production"
Action resource: "proj/default:env/production:flag/my-flag"

Does it match "proj/default:env/production:flag/*" ? → YES ✅

User action: updateOn flag "my-flag" in project "default", env "test"
Action resource: "proj/default:env/test:flag/my-flag"

Does it match "proj/default:env/production:flag/*" ? → NO
Does it match "proj/default:env/staging:flag/*"   ? → NO  ❌
```

---

## Resource String Construction

### Full breakdown of a resolved resource

```
proj / default : env / production : flag / *
  │       │        │       │          │    │
  │       │        │       │          │    └── flag wildcard (all flags)
  │       │        │       │          └─────── resource type
  │       │        │       └────────────────── resolved from roleAttribute/update-targeting-environments
  │       │        └────────────────────────── resource type
  │       └─────────────────────────────────── resolved from roleAttribute/projects
  └─────────────────────────────────────────── resource type prefix
```

### Attribute name convention

| Role Attribute Key Pattern | Used For |
|---------------------------|----------|
| `projects` | All roles (shared) |
| `<role-key>-environments` | Per env role, unique scoping |

Example: role key = `apply-changes` → attribute key = `apply-changes-environments`

---

## Complete Example: Developers Team

### Input: What SA wants to configure

| Permission | Environments |
|-----------|-------------|
| Update Targeting | production, staging |
| Review Changes | production, staging |
| Apply Changes | production only |
| Manage Segments | production only |
| Manage Experiments | production, staging, test |
| View SDK Key | production, staging |
| Create Flags | all envs (project-level) |
| Update Flags | all envs (project-level) |
| Manage Metrics | all envs (project-level) |

### Output: Terraform team resource

```hcl
resource "launchdarkly_team" "developers" {
  key         = format(var.key_format, "developers")
  name        = format(var.name_format, "Developers")
  description = "Developers"

  custom_role_keys = setunion(
    var.additional_roles,
    # Project-level roles
    var.roles.project[*].create_flags,
    var.roles.project[*].update_flags,
    var.roles.project[*].manage_metrics,
    var.roles.project[*].view_project,
    # Environment-level roles
    var.roles.environment[*].update_targeting,
    var.roles.environment[*].review_changes,
    var.roles.environment[*].apply_changes,
    var.roles.environment[*].manage_segments,
    var.roles.environment[*].manage_experiments,
    var.roles.environment[*].view_sdk_key,
  )

  dynamic "role_attributes" {
    for_each = var.role_attributes
    content {
      key    = role_attributes.key
      values = role_attributes.value
    }
  }

  role_attributes {
    key    = "update-targeting-environments"
    values = ["production", "staging"]
  }
  role_attributes {
    key    = "review-changes-environments"
    values = ["production", "staging"]
  }
  role_attributes {
    key    = "apply-changes-environments"
    values = ["production"]
  }
  role_attributes {
    key    = "manage-segments-environments"
    values = ["production"]
  }
  role_attributes {
    key    = "manage-experiments-environments"
    values = ["production", "staging", "test"]
  }
  role_attributes {
    key    = "view-sdk-key-environments"
    values = ["production", "staging"]
  }

  lifecycle {
    ignore_changes = [member_ids, maintainers]
  }
}
```

---

## Edge Cases & Rules

### Rule 1: Missing role attribute = no access (fails closed)
If a team has a role assigned but no matching `role_attributes` block, the placeholder resolves to nothing → no resources match → no access granted.

```
Role resource: proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*
Team has:      projects = ["default"]
Team missing:  update-targeting-environments  ← not set

Result: placeholder cannot resolve → role grants nothing
```

### Rule 2: Project-level roles don't need env attributes
Per-project roles only use `${roleAttribute/projects}`. They do not need env attributes.

### Rule 3: Multiple values = multiple resolved resources
```
values = ["production", "staging", "test"]
→ resolves to 3 separate resource strings
→ user gets access to all 3 environments
```

### Rule 4: Role attribute names are case-sensitive
`update-targeting-environments` ≠ `Update-Targeting-Environments`

### Rule 5: Each env role scopes independently
A team can have:
- `apply-changes-environments = ["production"]`       — strict
- `update-targeting-environments = ["production", "staging"]`  — wider

This is the primary advantage over `{critical:true}`: **granular per-role environment scoping**.

---

## Navigation

- [← HLD](./HLD.md)
- [Pseudo Logic & Test Cases →](./PSEUDOLOGIC_AND_TESTS.md)
