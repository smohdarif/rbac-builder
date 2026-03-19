# Phase 3: Payload Builder Design Document

> **Phase:** 3 of 10
> **Status:** 📋 Planning
> **Goal:** Transform RBACConfig into LaunchDarkly API-ready JSON payloads
> **Depends On:** Phase 1 (Data Models), Phase 2 (Storage)

---

## Related Documents

| Document | Description |
|----------|-------------|
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Deep dive into string formatting, data transformation, enums |
| [README.md](./README.md) | Phase 3 overview and quick reference |
| [../phase2/](../phase2/) | Phase 2 - Storage Service (dependency) |
| [../phase1/](../phase1/) | Phase 1 - Data Models (dependency) |

---

## Table of Contents

1. [High-Level Design (HLD)](#high-level-design-hld)
2. [Detailed Low-Level Design (DLD)](#detailed-low-level-design-dld)
3. [Pseudo Logic](#pseudo-logic)
4. [Implementation Plan](#implementation-plan)
5. [Learning Resources](#learning-resources)

---

## High-Level Design (HLD)

### What Are We Building?

A **Payload Builder** service that transforms our internal `RBACConfig` data model into LaunchDarkly-compatible JSON payloads ready for API deployment.

Think of it as a **translator**:
- **Input:** Our RBACConfig (what the user designed in the UI)
- **Output:** LaunchDarkly API payloads (what LD's API expects)

### Why Do We Need a Payload Builder?

```
OUR DATA MODEL:                         LAUNCHDARKLY API FORMAT:
─────────────────                       ─────────────────────────

RBACConfig                              Custom Role JSON
├── teams: [Team, Team]                 {
├── env_groups: [Env, Env]                "key": "dev-team-production",
├── project_permissions: [...]            "name": "Dev Team - Production",
└── env_permissions: [...]                "policy": [
                                            {
    Simple checkboxes!                        "effect": "allow",
                                              "actions": ["updateOn"],
                                              "resources": ["proj/*:env/prod"]
                                            }
                                          ]
                                        }

                                        Team JSON
                                        {
                                          "key": "dev-team",
                                          "name": "Dev Team",
                                          "customRoleKeys": [
                                            "dev-team-production",
                                            "dev-team-staging"
                                          ]
                                        }
```

### Where Does Payload Builder Fit?

```
┌─────────────────────────────────────────────────────────────────────┐
│                           RBAC BUILDER                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐         ┌──────────────────────────────────────┐ │
│  │   UI Layer   │         │         SERVICES LAYER               │ │
│  │   (app.py)   │         │                                      │ │
│  │              │         │  ┌──────────────┐  ┌──────────────┐ │ │
│  │  Permission  │ ──────► │  │   STORAGE    │  │  PAYLOAD     │ │ │
│  │  Matrix      │         │  │   SERVICE    │  │  BUILDER     │ │ │
│  │              │         │  │   (Phase 2)  │  │  ◄── HERE    │ │ │
│  └──────────────┘         │  └──────────────┘  └──────┬───────┘ │ │
│                           │                           │          │ │
│                           │                           ▼          │ │
│                           │                    ┌──────────────┐ │ │
│                           │                    │  (Future)    │ │ │
│                           │                    │  LD Client   │ │ │
│                           │                    │  Deployer    │ │ │
│                           │                    └──────────────┘ │ │
│                           └──────────────────────────────────────┘ │
│                                                                      │
│                           ┌──────────────────┐                     │
│                           │   DATA MODELS    │                     │
│                           │   (Phase 1) ✅   │                     │
│                           └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Features

| Feature | Description |
|---------|-------------|
| **Build Custom Roles** | Generate LD custom role JSON from permissions |
| **Build Teams** | Generate LD team JSON with role assignments |
| **Build Policies** | Generate policy statements from checkboxes |
| **Action Mapping** | Map our permission names to LD action codes |
| **Resource Building** | Build LD resource strings (proj/X:env/Y) |
| **Export Package** | Generate deployment-ready package with docs |

### Data Flow

```
BUILD PAYLOAD FLOW:
───────────────────

    RBACConfig (from UI or storage)
           │
           ▼
    ┌─────────────────┐
    │ PayloadBuilder  │
    │                 │
    │ 1. Extract      │
    │    permissions  │
    │                 │
    │ 2. Map to LD    │
    │    actions      │
    │                 │
    │ 3. Build policy │
    │    statements   │
    │                 │
    │ 4. Generate     │
    │    role JSON    │
    │                 │
    │ 5. Generate     │
    │    team JSON    │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  DeployPayload  │
    │                 │
    │  - roles: []    │
    │  - teams: []    │
    │  - manifest     │
    └─────────────────┘
             │
             ├──────────────────────┐
             │                      │
             ▼                      ▼
    ┌─────────────────┐    ┌─────────────────┐
    │  LD Client      │    │  Export Package │
    │  (Deploy)       │    │  (Download)     │
    └─────────────────┘    └─────────────────┘
```

---

## Detailed Low-Level Design (DLD)

### File Structure

```
rbac-builder/
├── services/
│   ├── __init__.py           # Add PayloadBuilder export
│   ├── storage.py            # Phase 2 ✅
│   └── payload_builder.py    # THIS PHASE
│
├── core/                      # New folder for constants
│   ├── __init__.py
│   └── ld_actions.py         # LaunchDarkly action mappings
│
└── models/                    # Phase 1 ✅
    └── ...
```

### LaunchDarkly API Structures

#### Custom Role JSON Format

```json
{
  "key": "dev-team-production",
  "name": "Dev Team - Production",
  "description": "Auto-generated by RBAC Builder",
  "policy": [
    {
      "effect": "allow",
      "actions": ["viewProject"],
      "resources": ["proj/my-project"]
    },
    {
      "effect": "allow",
      "actions": ["updateOn", "updateFallthrough"],
      "resources": ["proj/my-project:env/production"]
    }
  ]
}
```

#### Team JSON Format

```json
{
  "key": "dev-team",
  "name": "Dev Team",
  "description": "Development team",
  "customRoleKeys": [
    "dev-team-production",
    "dev-team-staging",
    "dev-team-development"
  ]
}
```

### Action Mapping Tables

#### Project-Level Actions

| Our Permission | LaunchDarkly Action(s) | Description |
|----------------|------------------------|-------------|
| `create_flags` | `createFlag` | Create new feature flags |
| `update_flags` | `updateName`, `updateDescription`, `updateTags`, `updateFlagVariations`, `updateFlagDefaultVariations` | Modify flag settings |
| `archive_flags` | `deleteFlag` | Archive/delete flags |
| `manage_webhooks` | `*` on webhooks resource | Manage webhooks |
| `manage_integrations` | `*` on integrations resource | Manage integrations |
| `manage_environments` | `*` on environments resource | Manage environments |
| `manage_tokens` | `*` on tokens resource | Manage API tokens |
| `manage_context_kinds` | `*` on context-kinds resource | Manage context kinds |
| `manage_segments` | `createSegment`, `updateSegment`, `deleteSegment` | Manage segments |
| `manage_ai_configs` | `*` on ai-configs resource | Manage AI configurations |

#### Environment-Level Actions

| Our Permission | LaunchDarkly Action(s) | Description |
|----------------|------------------------|-------------|
| `update_targeting` | `updateOn`, `updateFallthrough`, `updateTargets`, `updateRules`, `updatePrerequisites`, `updateOffVariation`, `updateScheduledChanges` | Modify targeting rules |
| `apply_changes` | `applyApprovalRequest`, `createApprovalRequest` | Apply pending changes |
| `review_changes` | `reviewApprovalRequest` | Review and approve changes |
| `bypass_required_approval` | `bypassRequiredApproval` | Skip approval workflow |
| `manage_segments` | `updateIncluded`, `updateExcluded`, `updateRules` on segments | Manage segment targeting |
| `manage_holdouts` | `*` on holdouts resource | Manage experiment holdouts |
| `manage_triggers` | `*` on triggers resource | Manage flag triggers |

### Resource String Format

```
LaunchDarkly Resource Syntax:
─────────────────────────────

Project-level:
  proj/{project-key}                    # Specific project
  proj/*                                # All projects

Environment-level:
  proj/{project-key}:env/{env-key}      # Specific environment
  proj/{project-key}:env/*              # All environments in project

Flag-level:
  proj/{project-key}:env/{env-key}:flag/{flag-key}
  proj/{project-key}:env/{env-key}:flag/*

Segment-level:
  proj/{project-key}:env/{env-key}:segment/*

Examples:
  proj/mobile-app                       # mobile-app project
  proj/mobile-app:env/production        # production env in mobile-app
  proj/mobile-app:env/production:flag/* # all flags in production
```

### Class Design: PayloadBuilder

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PayloadBuilder                               │
├─────────────────────────────────────────────────────────────────────┤
│  Attributes:                                                         │
│  ┌─────────────────┬──────────────┬─────────────────────────────┐  │
│  │ Attribute       │ Type         │ Description                  │  │
│  ├─────────────────┼──────────────┼─────────────────────────────┤  │
│  │ config          │ RBACConfig   │ Source configuration         │  │
│  │ project_key     │ str          │ Target project key           │  │
│  └─────────────────┴──────────────┴─────────────────────────────┘  │
│                                                                      │
│  Methods:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ MAIN BUILD METHODS                                               ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ build() -> DeployPayload                                        ││
│  │   Build complete deployment payload                             ││
│  │                                                                  ││
│  │ build_custom_roles() -> list[dict]                              ││
│  │   Generate all custom role JSON payloads                        ││
│  │                                                                  ││
│  │ build_teams() -> list[dict]                                     ││
│  │   Generate all team JSON payloads                               ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ ROLE BUILDING METHODS                                            ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ _build_role_for_team_env(team, env) -> dict                     ││
│  │   Build a single custom role for team+environment               ││
│  │                                                                  ││
│  │ _build_project_policy(team_key) -> list[dict]                   ││
│  │   Build project-level policy statements                         ││
│  │                                                                  ││
│  │ _build_env_policy(team_key, env_key) -> list[dict]              ││
│  │   Build environment-level policy statements                     ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ HELPER METHODS                                                   ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ _generate_role_key(team_key, env_key) -> str                    ││
│  │   Generate unique role key: "dev-team-production"               ││
│  │                                                                  ││
│  │ _build_resource_string(env_key?) -> str                         ││
│  │   Build LD resource string: "proj/X:env/Y"                      ││
│  │                                                                  ││
│  │ _map_permission_to_actions(permission, level) -> list[str]      ││
│  │   Map our permission name to LD action codes                    ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Class Design: DeployPayload

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DeployPayload                                │
├─────────────────────────────────────────────────────────────────────┤
│  A container for all deployment data                                 │
│                                                                      │
│  Attributes:                                                         │
│  ┌─────────────────┬──────────────┬─────────────────────────────┐  │
│  │ Attribute       │ Type         │ Description                  │  │
│  ├─────────────────┼──────────────┼─────────────────────────────┤  │
│  │ customer_name   │ str          │ Customer name                │  │
│  │ project_key     │ str          │ Project key                  │  │
│  │ roles           │ list[dict]   │ Custom role payloads         │  │
│  │ teams           │ list[dict]   │ Team payloads                │  │
│  │ created_at      │ datetime     │ When payload was built       │  │
│  └─────────────────┴──────────────┴─────────────────────────────┘  │
│                                                                      │
│  Methods:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ to_manifest() -> dict                                           ││
│  │   Generate deployment manifest with order                       ││
│  │                                                                  ││
│  │ get_role_payloads() -> list[dict]                               ││
│  │   Get role payloads with metadata                               ││
│  │                                                                  ││
│  │ get_team_payloads() -> list[dict]                               ││
│  │   Get team payloads with metadata                               ││
│  │                                                                  ││
│  │ to_json() -> str                                                ││
│  │   Serialize entire payload to JSON                              ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Action Mappings Module (core/ld_actions.py)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      core/ld_actions.py                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  # Enums for type safety                                            │
│  class PermissionLevel(Enum):                                       │
│      PROJECT = "project"                                            │
│      ENVIRONMENT = "environment"                                    │
│                                                                      │
│  # Action mapping dictionaries                                      │
│  PROJECT_ACTIONS: dict[str, list[str]]                              │
│  ENV_ACTIONS: dict[str, list[str]]                                  │
│                                                                      │
│  # Helper functions                                                  │
│  def get_actions(permission: str, level: PermissionLevel) -> list   │
│  def get_all_project_permissions() -> list[str]                     │
│  def get_all_env_permissions() -> list[str]                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Role Naming Convention

```
Role Key Format:
────────────────
{team-key}-{environment-key}

Examples:
  dev-team + production   →  dev-team-production
  qa-team + staging       →  qa-team-staging
  admin + development     →  admin-development

Why this format?
  - Unique: Each team/env combo gets its own role
  - Readable: Easy to understand what the role is for
  - Consistent: Predictable naming makes debugging easier
```

---

## Pseudo Logic

### 1. Main Build Method

```
FUNCTION build() -> DeployPayload:
    """Build complete deployment payload from RBACConfig."""

    # Step 1: Build all custom roles
    roles = build_custom_roles()

    # Step 2: Build all teams with role assignments
    teams = build_teams()

    # Step 3: Create deployment payload
    payload = DeployPayload(
        customer_name = config.customer_name,
        project_key = config.project_key,
        roles = roles,
        teams = teams,
        created_at = now()
    )

    RETURN payload
```

### 2. Build Custom Roles

```
FUNCTION build_custom_roles() -> list[dict]:
    """Generate custom role payloads for all team/environment combinations."""

    roles = []

    # For each team...
    FOR team IN config.teams:

        # For each environment...
        FOR env IN config.env_groups:

            # Build role for this team+env combination
            role = _build_role_for_team_env(team, env)

            # Only add if role has any permissions
            IF role["policy"] is not empty:
                roles.append(role)

    RETURN roles
```

### 3. Build Single Role

```
FUNCTION _build_role_for_team_env(team: Team, env: EnvironmentGroup) -> dict:
    """Build a custom role for a specific team/environment combination."""

    role_key = _generate_role_key(team.key, env.key)
    policy_statements = []

    # Step 1: Get project-level permissions for this team
    project_perm = config.get_project_permission(team.key)

    IF project_perm exists:
        # Build project-level policy statements
        project_policies = _build_project_policy(project_perm)
        policy_statements.extend(project_policies)

    # Step 2: Get environment-level permissions for this team+env
    env_perm = config.get_env_permission(team.key, env.key)

    IF env_perm exists:
        # Build environment-level policy statements
        env_policies = _build_env_policy(env_perm, env.key)
        policy_statements.extend(env_policies)

    # Step 3: Build the role JSON
    role = {
        "key": role_key,
        "name": f"{team.name} - {env.key.title()}",
        "description": f"Auto-generated role for {team.name} in {env.key}",
        "policy": policy_statements
    }

    RETURN role
```

### 4. Build Project Policy Statements

```
FUNCTION _build_project_policy(perm: ProjectPermission) -> list[dict]:
    """Build policy statements for project-level permissions."""

    statements = []
    project_resource = f"proj/{config.project_key}"

    # Map each enabled permission to LD actions
    permission_map = {
        "create_flags": perm.create_flags,
        "update_flags": perm.update_flags,
        "archive_flags": perm.archive_flags,
        "manage_webhooks": perm.manage_webhooks,
        "manage_integrations": perm.manage_integrations,
        "manage_environments": perm.manage_environments,
        "manage_tokens": perm.manage_tokens,
        "manage_context_kinds": perm.manage_context_kinds,
        "manage_segments": perm.manage_segments,
        "manage_ai_configs": perm.manage_ai_configs,
    }

    # Collect all enabled actions
    enabled_actions = []

    FOR permission_name, is_enabled IN permission_map:
        IF is_enabled:
            actions = _map_permission_to_actions(permission_name, PROJECT)
            enabled_actions.extend(actions)

    # Create single policy statement with all actions
    IF enabled_actions is not empty:
        statement = {
            "effect": "allow",
            "actions": enabled_actions,
            "resources": [project_resource]
        }
        statements.append(statement)

    RETURN statements
```

### 5. Build Environment Policy Statements

```
FUNCTION _build_env_policy(perm: EnvironmentPermission, env_key: str) -> list[dict]:
    """Build policy statements for environment-level permissions."""

    statements = []
    env_resource = f"proj/{config.project_key}:env/{env_key}"

    # Map each enabled permission to LD actions
    permission_map = {
        "update_targeting": perm.update_targeting,
        "apply_changes": perm.apply_changes,
        "review_changes": perm.review_changes,
        "bypass_required_approval": perm.bypass_required_approval,
        "manage_segments": perm.manage_segments,
        "manage_holdouts": perm.manage_holdouts,
        "manage_triggers": perm.manage_triggers,
    }

    # Collect all enabled actions
    enabled_actions = []

    FOR permission_name, is_enabled IN permission_map:
        IF is_enabled:
            actions = _map_permission_to_actions(permission_name, ENVIRONMENT)
            enabled_actions.extend(actions)

    # Create policy statement
    IF enabled_actions is not empty:
        statement = {
            "effect": "allow",
            "actions": enabled_actions,
            "resources": [env_resource]
        }
        statements.append(statement)

    RETURN statements
```

### 6. Build Teams

```
FUNCTION build_teams() -> list[dict]:
    """Generate team payloads with custom role assignments."""

    teams = []

    FOR team IN config.teams:

        # Collect all role keys for this team
        role_keys = []

        FOR env IN config.env_groups:
            role_key = _generate_role_key(team.key, env.key)

            # Only add if we actually created this role
            IF role_exists_in_payload(role_key):
                role_keys.append(role_key)

        # Build team JSON
        team_payload = {
            "key": team.key,
            "name": team.name,
            "description": team.description or f"Team: {team.name}",
            "customRoleKeys": role_keys
        }

        teams.append(team_payload)

    RETURN teams
```

### 7. Action Mapping

```
FUNCTION _map_permission_to_actions(permission: str, level: PermissionLevel) -> list[str]:
    """Map our permission name to LaunchDarkly action codes."""

    # Project-level mappings
    PROJECT_ACTIONS = {
        "create_flags": ["createFlag"],
        "update_flags": [
            "updateName",
            "updateDescription",
            "updateTags",
            "updateFlagVariations",
            "updateFlagDefaultVariations"
        ],
        "archive_flags": ["deleteFlag"],
        "manage_webhooks": ["*"],  # All actions on webhook resources
        "manage_integrations": ["*"],
        "manage_environments": ["*"],
        "manage_tokens": ["*"],
        "manage_context_kinds": ["*"],
        "manage_segments": ["createSegment", "updateSegment", "deleteSegment"],
        "manage_ai_configs": ["*"],
    }

    # Environment-level mappings
    ENV_ACTIONS = {
        "update_targeting": [
            "updateOn",
            "updateFallthrough",
            "updateTargets",
            "updateRules",
            "updatePrerequisites",
            "updateOffVariation",
            "updateScheduledChanges"
        ],
        "apply_changes": [
            "applyApprovalRequest",
            "createApprovalRequest"
        ],
        "review_changes": ["reviewApprovalRequest"],
        "bypass_required_approval": ["bypassRequiredApproval"],
        "manage_segments": [
            "updateIncluded",
            "updateExcluded",
            "updateRules"
        ],
        "manage_holdouts": ["*"],
        "manage_triggers": ["*"],
    }

    # Look up in appropriate mapping
    IF level == PROJECT:
        RETURN PROJECT_ACTIONS.get(permission, [])
    ELSE:
        RETURN ENV_ACTIONS.get(permission, [])
```

### 8. Generate Manifest

```
FUNCTION to_manifest(payload: DeployPayload) -> dict:
    """Generate deployment manifest with order and metadata."""

    manifest = {
        "version": "1.0",
        "customer": payload.customer_name,
        "project": payload.project_key,
        "generated": payload.created_at.isoformat(),
        "generated_by": "RBAC Builder",
        "deployment_order": [
            {
                "step": 1,
                "type": "custom-roles",
                "description": "Create custom roles with permissions",
                "endpoint": "POST /api/v2/roles",
                "count": len(payload.roles),
                "items": [role["key"] for role in payload.roles]
            },
            {
                "step": 2,
                "type": "teams",
                "description": "Create teams and assign roles",
                "endpoint": "POST /api/v2/teams",
                "count": len(payload.teams),
                "items": [team["key"] for team in payload.teams]
            }
        ],
        "summary": {
            "total_roles": len(payload.roles),
            "total_teams": len(payload.teams),
            "environments": [env.key for env in config.env_groups]
        }
    }

    RETURN manifest
```

### 9. Integration Example

```
PSEUDO CODE for usage in app.py or deployer:

# Build payload from config
builder = PayloadBuilder(config)
payload = builder.build()

# Option 1: Deploy directly
for role in payload.roles:
    ld_client.create_role(role)

for team in payload.teams:
    ld_client.create_team(team)

# Option 2: Export as package
manifest = payload.to_manifest()
export_to_zip(payload, manifest)

# Option 3: Preview before deploy
st.json(payload.to_json())
```

---

## Implementation Plan

### Step-by-Step Implementation

```
STEP 1: Create core/ld_actions.py
        ├── Define PermissionLevel enum
        ├── Define PROJECT_ACTIONS mapping
        ├── Define ENV_ACTIONS mapping
        └── Add helper functions

STEP 2: Create services/payload_builder.py
        ├── Import dependencies
        ├── Create DeployPayload dataclass
        └── Create PayloadBuilder class shell

STEP 3: Implement helper methods
        ├── _generate_role_key()
        ├── _build_resource_string()
        └── _map_permission_to_actions()

STEP 4: Implement policy building
        ├── _build_project_policy()
        └── _build_env_policy()

STEP 5: Implement role building
        ├── _build_role_for_team_env()
        └── build_custom_roles()

STEP 6: Implement team building
        └── build_teams()

STEP 7: Implement main build method
        └── build()

STEP 8: Implement DeployPayload methods
        ├── to_manifest()
        ├── to_json()
        └── get_role_payloads() / get_team_payloads()

STEP 9: Update services/__init__.py
        └── Export PayloadBuilder, DeployPayload

STEP 10: Test with sample configs
         └── Manual testing with Python REPL
```

### Python Concepts You'll Learn

| Concept | What It Does | Example |
|---------|--------------|---------|
| `Enum` | Type-safe constants | `class PermissionLevel(Enum)` |
| `dict[str, list]` | Type hints for mappings | `PROJECT_ACTIONS: dict[str, list[str]]` |
| List comprehension | Transform data | `[role["key"] for role in roles]` |
| `@dataclass` | Data containers | `DeployPayload` |
| f-strings | String formatting | `f"proj/{project}:env/{env}"` |
| `.get()` with default | Safe dict access | `mapping.get(key, [])` |

### Estimated Learning Topics

```
┌─────────────────────────────────────────────────────────────────┐
│                  PYTHON LESSONS IN PHASE 3                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LESSON 69: Python Enums                                        │
│  ├── Creating enums for type safety                             │
│  ├── Enum values and comparisons                                │
│  └── When to use enums vs strings                               │
│                                                                  │
│  LESSON 70: Dictionary Mappings                                  │
│  ├── Using dicts as lookup tables                               │
│  ├── Type hints for complex dicts                               │
│  └── .get() with default values                                 │
│                                                                  │
│  LESSON 71: List Comprehensions (Advanced)                       │
│  ├── Filtering with conditions                                  │
│  ├── Nested comprehensions                                      │
│  └── When to use comprehensions vs loops                        │
│                                                                  │
│  LESSON 72: String Formatting                                    │
│  ├── f-strings with expressions                                 │
│  ├── Building resource strings                                  │
│  └── .join() for combining lists                                │
│                                                                  │
│  LESSON 73: Data Transformation Patterns                         │
│  ├── Extracting data from nested structures                     │
│  ├── Building new structures from existing data                 │
│  └── The "builder" pattern                                      │
│                                                                  │
│  LESSON 74: Working with LaunchDarkly API                        │
│  ├── Understanding policy syntax                                │
│  ├── Resource string format                                     │
│  └── Action codes and meanings                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example Output

### Input RBACConfig

```json
{
  "customer_name": "Acme Corp",
  "project_key": "mobile-app",
  "teams": [
    {"key": "dev", "name": "Developer"}
  ],
  "env_groups": [
    {"key": "production", "is_critical": true}
  ],
  "project_permissions": [
    {"team_key": "dev", "create_flags": true, "update_flags": true}
  ],
  "env_permissions": [
    {"team_key": "dev", "environment_key": "production", "update_targeting": false}
  ]
}
```

### Output Custom Role

```json
{
  "key": "dev-production",
  "name": "Developer - Production",
  "description": "Auto-generated role for Developer in production",
  "policy": [
    {
      "effect": "allow",
      "actions": [
        "createFlag",
        "updateName",
        "updateDescription",
        "updateTags",
        "updateFlagVariations",
        "updateFlagDefaultVariations"
      ],
      "resources": ["proj/mobile-app"]
    }
  ]
}
```

### Output Team

```json
{
  "key": "dev",
  "name": "Developer",
  "description": "Team: Developer",
  "customRoleKeys": ["dev-production"]
}
```

---

## Summary

### What We're Building

- **PayloadBuilder class** to transform RBACConfig to LD payloads
- **DeployPayload dataclass** to hold all deployment data
- **Action mappings** in core/ld_actions.py
- **Policy statement** generation logic

### Why This Matters

```
Without PayloadBuilder:              With PayloadBuilder:
──────────────────────              ─────────────────────
• Manual JSON construction          • Automatic transformation
• Easy to make syntax errors        • Validated output
• No standardization                • Consistent format
• Hard to maintain                  • Single source of truth
```

### Integration Points

| Component | How PayloadBuilder Connects |
|-----------|----------------------------|
| **RBACConfig** | Input - reads permissions from config |
| **StorageService** | Can build payload from loaded config |
| **Deployer (future)** | Consumes payload for API calls |
| **ExportBuilder (future)** | Uses payload for export package |
| **UI** | Preview payload before deploy |

---

## Learning Resources

### Deep Dive Documents

| Topic | Document | Description |
|-------|----------|-------------|
| **All Phase 3 Concepts** | [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Enums, mappings, transformations |

### External Resources

| Resource | Link |
|----------|------|
| LaunchDarkly Custom Roles | https://docs.launchdarkly.com/home/members/role-concepts |
| LaunchDarkly Actions Reference | https://docs.launchdarkly.com/home/members/role-actions |
| LaunchDarkly Teams API | https://apidocs.launchdarkly.com/tag/Teams |
| Python Enums | https://docs.python.org/3/library/enum.html |

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Phase 2: Storage](../phase2/) | **Phase 3: Payload Builder** | Phase 4: Validation |

[← Back to Phases Index](../) | [View Python Concepts →](./PYTHON_CONCEPTS.md)
