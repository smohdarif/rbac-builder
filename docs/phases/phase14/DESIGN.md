# Phase 14: Design Document — Observability Permissions

| Field | Value |
|-------|-------|
| **Phase** | 14 |
| **Status** | 📋 Design Complete |
| **Goal** | Add Observability permissions to the rbac-builder |
| **Dependencies** | Phase 11 (Role Attribute Pattern), Phase 12 (Resource Builders) |

## Related Documents

| Document | Link |
|----------|------|
| Phase README | [README.md](./README.md) |
| Python Concepts | [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) |
| Gonfalon action source | `gonfalon/internal/roles/action.go` |
| Gonfalon resource source | `gonfalon/internal/roles/resource_identifier.go` |

---

## High-Level Design (HLD)

### What Are We Building and Why?

LaunchDarkly's Observability suite (Sessions, Logs, Errors, Traces, Alerts, Dashboards, Vega AI) requires custom RBAC permissions. Currently rbac-builder has no support for these. Customers using Observability must configure permissions manually.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXISTING ARCHITECTURE                        │
│                                                                 │
│  ui/matrix_tab.py                                               │
│  PROJECT_PERMISSIONS = [                                        │
│    "Create Flags", "Update Flags", ...                          │
│  ]                                ← ADD observability here      │
│         │                                                       │
│         ▼                                                       │
│  core/ld_actions.py                                             │
│  PROJECT_PERMISSION_MAP = {                                     │
│    "Create Flags": ProjectAction.CREATE_FLAGS, ...              │
│  }                                ← ADD ObservabilityAction     │
│         │                                                       │
│         ▼                                                       │
│  services/payload_builder.py                                    │
│  _build_project_template_role()                                 │
│    → build_role_attribute_resource()   ← FLAG/SEGMENT PATH     │
│    → build_project_type_resource()     ← NEW: OBSERVABILITY PATH│
└─────────────────────────────────────────────────────────────────┘
```

### Core Features Table

| Feature | Default in Matrix? | Resource Pattern |
|---------|:-----------------:|-----------------|
| View Sessions | ✅ | `proj/${roleAttribute/projects}:session/*` |
| View Errors | ✅ | `proj/${roleAttribute/projects}:error/*` |
| View Logs | ✅ | `proj/${roleAttribute/projects}:log/*` |
| View Traces | ✅ | `proj/${roleAttribute/projects}:trace/*` |
| Manage Alerts | 🔲 optional | `proj/${roleAttribute/projects}:alert/*` |
| Manage Observability Dashboards | 🔲 optional | `proj/${roleAttribute/projects}:observability-dashboard/*` |
| Talk to Vega | 🔲 optional | `proj/${roleAttribute/projects}:vega/*` |

### Why No Environment-Level Observability Permissions?

There are **no environment-level observability permissions** — this is a deliberate LaunchDarkly product decision.

Verified from `gonfalon/internal/roles/resource_identifier.go`:

```go
// Environment-scoped (e.g. flags) — has env in the path
type FlagResourceIdentifier struct {
    EnvironmentResourceIdentifier   // → proj/*:env/*:flag/*
}

// ALL observability types — project-scoped, no env
type SessionResourceIdentifier struct {
    ProjectResourceIdentifier       // → proj/*:session/*
}
type TraceResourceIdentifier struct {
    ProjectResourceIdentifier       // → proj/*:trace/*
}
// Same for: Error, Log, Vega, Alert, ObservabilityDashboard
```

Every observability resource identifier embeds `ProjectResourceIdentifier`, not `EnvironmentResourceIdentifier`. This means environment-level scoping is simply not supported by the LD RBAC engine for these resource types.

**Why this makes product sense:** Observability data (traces, logs, sessions, errors) is typically viewed across all environments when debugging an issue. Scoping it to a specific environment would limit the SA's ability to cross-reference data across production and staging during an incident.

> **Note:** The LD Slack response to College Board (2026-03-18) incorrectly stated that
> `trace` and `vega` were environment-scoped (`proj/*:env/*:trace/*`). The Gonfalon source
> confirms both are project-scoped only.

### Data Flow

```
SA checks "View Sessions" for Developer team
        │
        ▼
ui/matrix_tab.py marks True in project_matrix_df
        │
        ▼
payload_builder._build_project_template_role("View Sessions")
        │
        ├─ get_project_actions("View Sessions") → ["viewSession"]
        │
        ├─ is_observability_permission("View Sessions") → True
        │     (checks OBSERVABILITY_RESOURCE_MAP)
        │
        ├─ resource_type = get_observability_resource_type("View Sessions") → "session"
        │
        └─ build_project_type_resource("projects", "session")
              → "proj/${roleAttribute/projects}:session/*"
                          (NO env/* segment)

Output role JSON:
{
  "key": "view-sessions",
  "name": "View Sessions",
  "base_permissions": "no_access",
  "policy": [
    {
      "effect": "allow",
      "actions": ["viewSession"],
      "resources": ["proj/${roleAttribute/projects}:session/*"]
    },
    {
      "effect": "allow",
      "actions": ["viewProject"],
      "resources": ["proj/${roleAttribute/projects}"]
    }
  ]
}
```

---

## Detailed Low-Level Design (DLD)

### 1. core/ld_actions.py

#### New Enum: `ObservabilityAction`

```python
class ObservabilityAction(Enum):
    """
    Maps observability UI permission names to LD action codes.
    All observability resources are PROJECT-SCOPED (no env segment).
    Verified against gonfalon/internal/roles/action.go
    """

    VIEW_SESSIONS = ["viewSession"]

    VIEW_ERRORS   = ["viewError", "updateErrorStatus"]

    VIEW_LOGS     = ["viewLog"]

    VIEW_TRACES   = ["viewTrace"]

    MANAGE_ALERTS = [
        "viewAlert",
        "createAlert",
        "deleteAlert",
        "updateAlertOn",
        "updateAlertConfiguration",
    ]

    MANAGE_OBS_DASHBOARDS = [
        "viewObservabilityDashboard",
        "createObservabilityDashboard",
        "deleteObservabilityDashboard",
        "addObservabilityGraphToDashboard",
        "removeObservabilityGraphFromDashboard",
        "updateObservabilityDashboardConfiguration",
        "updateObservabilityGraphConfiguration",
        "updateObservabilitySettings",
    ]

    TALK_TO_VEGA = ["talkToVega"]
```

#### New Constant: `OBSERVABILITY_RESOURCE_MAP`

Maps each observability permission to its LD resource type segment.

```python
OBSERVABILITY_RESOURCE_MAP: Dict[str, str] = {
    "View Sessions":                    "session",
    "View Errors":                      "error",
    "View Logs":                        "log",
    "View Traces":                      "trace",
    "Manage Alerts":                    "alert",
    "Manage Observability Dashboards":  "observability-dashboard",
    "Talk to Vega":                     "vega",
}
```

**Key design decision:** Using a dict where presence = this is an observability permission. A permission NOT in this dict uses the standard `env/*:flag/*` path.

#### Update: `PROJECT_PERMISSION_MAP`

```python
PROJECT_PERMISSION_MAP: Dict[str, ProjectAction | ObservabilityAction] = {
    # ... existing entries ...
    "View Sessions":                   ObservabilityAction.VIEW_SESSIONS,
    "View Errors":                     ObservabilityAction.VIEW_ERRORS,
    "View Logs":                       ObservabilityAction.VIEW_LOGS,
    "View Traces":                     ObservabilityAction.VIEW_TRACES,
    "Manage Alerts":                   ObservabilityAction.MANAGE_ALERTS,
    "Manage Observability Dashboards": ObservabilityAction.MANAGE_OBS_DASHBOARDS,
    "Talk to Vega":                    ObservabilityAction.TALK_TO_VEGA,
}
```

#### New Resource Builder: `build_project_type_resource()`

```python
def build_project_type_resource(
    project_attr: str = "projects",
    resource_type: str = "session"
) -> str:
    """
    Build a project-scoped resource string for non-flag resource types.

    Used for observability resources that don't have an env segment.
    All observability resources are project-scoped:
        proj/${roleAttribute/projects}:session/*
        proj/${roleAttribute/projects}:trace/*   ← NOT :env/*:trace/*

    Example:
        >>> build_project_type_resource("projects", "session")
        'proj/${roleAttribute/projects}:session/*'
    """
    return f"proj/${{roleAttribute/{project_attr}}}:{resource_type}/*"
```

#### New Helper Functions

```python
def is_observability_permission(permission_name: str) -> bool:
    """Returns True if permission uses project-scoped observability resource."""
    return permission_name in OBSERVABILITY_RESOURCE_MAP

def get_observability_resource_type(permission_name: str) -> str:
    """Returns the resource type segment for an observability permission."""
    return OBSERVABILITY_RESOURCE_MAP.get(permission_name, "")
```

---

### 2. services/payload_builder.py

**Change:** `_build_project_template_role()` must detect observability permissions and use the correct resource builder.

#### Before (current code)

```python
def _build_project_template_role(self, permission_name: str):
    actions = get_project_actions(permission_name)
    resource_type = get_resource_type_for_permission(permission_name)

    policy = [{
        "effect": "allow",
        "actions": actions,
        "resources": [build_role_attribute_resource("projects", resource_type)]
        #             ^ always uses proj/${projects}:env/*:{type}/*
    }]
```

#### After (with observability detection)

```python
def _build_project_template_role(self, permission_name: str):
    actions = get_project_actions(permission_name)

    # =================================================================
    # LESSON: Branch on resource pattern based on permission type
    # =================================================================
    # Observability permissions use proj/${projects}:{type}/*  (no env)
    # All other project permissions use proj/${projects}:env/*:{type}/*
    if is_observability_permission(permission_name):
        obs_resource_type = get_observability_resource_type(permission_name)
        resource = build_project_type_resource("projects", obs_resource_type)
    else:
        resource_type = get_resource_type_for_permission(permission_name)
        resource = build_role_attribute_resource("projects", resource_type)

    policy = [{"effect": "allow", "actions": actions, "resources": [resource]}]
    # ... rest unchanged
```

---

### 3. ui/matrix_tab.py

#### Default matrix additions (4 new columns)

```python
PROJECT_PERMISSIONS = [
    # ... existing ...
    # Observability — Default
    "View Sessions",
    "View Errors",
    "View Logs",
    "View Traces",
]
```

#### Optional expander additions (3 new columns)

```python
OPTIONAL_PROJECT_PERMISSIONS = [
    # ... existing optional ...
    # Observability — Optional
    "Manage Alerts",
    "Manage Observability Dashboards",
    "Talk to Vega",
]
```

---

### 4. Output JSON Format

#### Example: View Sessions role

```json
{
  "key": "view-sessions",
  "name": "View Sessions",
  "description": "Template role for View Sessions",
  "base_permissions": "no_access",
  "policy": [
    {
      "effect": "allow",
      "actions": ["viewSession"],
      "resources": ["proj/${roleAttribute/projects}:session/*"]
    },
    {
      "effect": "allow",
      "actions": ["viewProject"],
      "resources": ["proj/${roleAttribute/projects}"]
    }
  ]
}
```

#### Example: Manage Observability Dashboards role

```json
{
  "key": "manage-observability-dashboards",
  "name": "Manage Observability Dashboards",
  "description": "Template role for Manage Observability Dashboards",
  "base_permissions": "no_access",
  "policy": [
    {
      "effect": "allow",
      "actions": [
        "viewObservabilityDashboard",
        "createObservabilityDashboard",
        "deleteObservabilityDashboard",
        "addObservabilityGraphToDashboard",
        "removeObservabilityGraphFromDashboard",
        "updateObservabilityDashboardConfiguration",
        "updateObservabilityGraphConfiguration",
        "updateObservabilitySettings"
      ],
      "resources": ["proj/${roleAttribute/projects}:observability-dashboard/*"]
    },
    {
      "effect": "allow",
      "actions": ["viewProject"],
      "resources": ["proj/${roleAttribute/projects}"]
    }
  ]
}
```

---

## Pseudo Logic

### 1. Action lookup for observability permissions

```
FUNCTION get_project_actions(permission_name):

  IF permission_name IN PROJECT_PERMISSION_MAP:
    enum_value = PROJECT_PERMISSION_MAP[permission_name]
    RETURN enum_value.value   # list of action strings

  RETURN []   # unknown permission
```

### 2. Resource selection in payload builder

```
FUNCTION _build_project_template_role(permission_name):

  actions = get_project_actions(permission_name)
  IF actions is empty: RETURN None

  role_key = slugify(permission_name)

  # ── Resource selection ────────────────────────────────────────
  IF permission_name == "View Project":
    # Special case: project-only resource, no resource type
    resource = build_project_only_role_attribute_resource("projects")
    policy = [{ allow, actions, resource }]

  ELSE IF is_observability_permission(permission_name):
    # Observability: project-scoped, no env segment
    obs_type = get_observability_resource_type(permission_name)
    resource = build_project_type_resource("projects", obs_type)
    # e.g. "proj/${roleAttribute/projects}:session/*"
    policy = [
      { allow, actions, resource },
      { allow, ["viewProject"], proj_resource }
    ]

  ELSE:
    # Standard flags/metrics/etc: project + env wildcard
    resource_type = get_resource_type_for_permission(permission_name)
    resource = build_role_attribute_resource("projects", resource_type)
    # e.g. "proj/${roleAttribute/projects}:env/*:flag/*"
    context_kind_actions = CONTEXT_KIND_ACTIONS_FOR_PERMISSION.get(permission_name)
    policy = [
      { allow, actions, resource },
      { allow, context_kind_actions, context_kind_resource }  # if applicable
      { allow, ["viewProject"], proj_resource }
    ]

  RETURN {
    key:              role_key,
    name:             permission_name,
    description:      f"Template role for {permission_name}",
    base_permissions: "no_access",
    policy:           policy
  }
```

### 3. UI matrix rendering

```
FUNCTION render_project_matrix():

  RENDER checkboxes for PROJECT_PERMISSIONS
    (View Sessions, View Errors, View Logs, View Traces visible by default)

  WITH st.expander("Optional Permissions", expanded=False):
    RENDER checkboxes for OPTIONAL_PROJECT_PERMISSIONS
      (Manage Alerts, Manage Observability Dashboards, Talk to Vega)
```

---

## Implementation Plan

| Step | Task | File |
|------|------|------|
| 1 | Add `ObservabilityAction` enum | `core/ld_actions.py` |
| 2 | Add `OBSERVABILITY_RESOURCE_MAP` | `core/ld_actions.py` |
| 3 | Add `build_project_type_resource()` | `core/ld_actions.py` |
| 4 | Add `is_observability_permission()`, `get_observability_resource_type()` | `core/ld_actions.py` |
| 5 | Update `PROJECT_PERMISSION_MAP` | `core/ld_actions.py` |
| 6 | Update `_build_project_template_role()` | `services/payload_builder.py` |
| 7 | Add 4 default observability columns | `ui/matrix_tab.py` |
| 8 | Add 3 optional observability columns | `ui/matrix_tab.py` |
| 9 | Write all tests | `tests/test_observability_permissions.py` |
| 10 | Run full test suite | `pytest tests/ -v` |

---

---

## Test Cases

**Test file:** `tests/test_observability_permissions.py`

### Group 1: Action Mappings

#### TC-OB-01: All observability permissions have correct action lists
```
GIVEN: each observability permission name
WHEN:  get_project_actions(permission_name) is called
THEN:
  "View Sessions"                  → ["viewSession"]
  "View Errors"                    → ["viewError", "updateErrorStatus"]
  "View Logs"                      → ["viewLog"]
  "View Traces"                    → ["viewTrace"]
  "Manage Alerts"                  → ["viewAlert", "createAlert", "deleteAlert", "updateAlertOn", "updateAlertConfiguration"]
  "Manage Observability Dashboards"→ ["viewObservabilityDashboard", "createObservabilityDashboard", ...]
  "Talk to Vega"                   → ["talkToVega"]
```

#### TC-OB-02: Observability permissions are in PROJECT_PERMISSION_MAP
```
GIVEN: OBSERVABILITY_RESOURCE_MAP keys
WHEN:  each key is checked in PROJECT_PERMISSION_MAP
THEN:  all 7 observability permissions are present
```

---

### Group 2: Resource Builder

#### TC-OB-03: build_project_type_resource generates correct path (no env)
```
GIVEN: build_project_type_resource("projects", "session")
THEN:  returns "proj/${roleAttribute/projects}:session/*"
       (no :env/* segment)
```

#### TC-OB-04: build_project_type_resource for all observability types
```
GIVEN: each resource type from OBSERVABILITY_RESOURCE_MAP
THEN:
  "session"                 → "proj/${roleAttribute/projects}:session/*"
  "error"                   → "proj/${roleAttribute/projects}:error/*"
  "log"                     → "proj/${roleAttribute/projects}:log/*"
  "trace"                   → "proj/${roleAttribute/projects}:trace/*"
  "alert"                   → "proj/${roleAttribute/projects}:alert/*"
  "observability-dashboard" → "proj/${roleAttribute/projects}:observability-dashboard/*"
  "vega"                    → "proj/${roleAttribute/projects}:vega/*"
```

#### TC-OB-05: is_observability_permission returns True only for observability perms
```
GIVEN: mix of permission names
THEN:
  is_observability_permission("View Sessions")  → True
  is_observability_permission("View Traces")    → True
  is_observability_permission("Create Flags")   → False
  is_observability_permission("Update Flags")   → False
  is_observability_permission("Unknown")        → False
```

---

### Group 3: Payload Builder — Role Generation

#### TC-OB-06: Observability role has NO env/* in resource path
```
GIVEN: payload with "View Sessions" enabled for Developer team
WHEN:  payload is built
THEN:
  role key = "view-sessions"
  policy[0].resources[0] = "proj/${roleAttribute/projects}:session/*"
  ":env/" NOT in policy[0].resources[0]   ← critical check
```

#### TC-OB-07: Observability role has base_permissions = no_access
```
GIVEN: any observability permission enabled
WHEN:  role is generated
THEN:  role["base_permissions"] == "no_access"
```

#### TC-OB-08: Observability role has viewProject statement
```
GIVEN: "View Sessions" role generated
WHEN:  policy is inspected
THEN:
  len(policy) == 2
  policy[1].actions == ["viewProject"]
  policy[1].resources[0] == "proj/${roleAttribute/projects}"
```

#### TC-OB-09: Standard flag roles are NOT affected by observability change
```
GIVEN: "Create Flags" enabled for Developer team
WHEN:  payload is built
THEN:
  create-flags role resource == "proj/${roleAttribute/projects}:env/*:flag/*"
  ":env/" in resource   ← env IS still present for flag roles
```

#### TC-OB-10: Mix of observability and flag permissions generates correct roles
```
GIVEN: Developer team has:
  "Create Flags" = True
  "View Sessions" = True
  "View Traces" = True
WHEN:  payload is built
THEN:
  "create-flags" role resource contains ":env/*:flag/*"
  "view-sessions" role resource contains ":session/*" (no env)
  "view-traces" role resource contains ":trace/*" (no env)
  All three roles present with correct structure
```

#### TC-OB-11: Manage Observability Dashboards role has all 8 actions
```
GIVEN: "Manage Observability Dashboards" enabled
WHEN:  role is generated
THEN:  actions list contains all 8:
  viewObservabilityDashboard, createObservabilityDashboard, deleteObservabilityDashboard,
  addObservabilityGraphToDashboard, removeObservabilityGraphFromDashboard,
  updateObservabilityDashboardConfiguration, updateObservabilityGraphConfiguration,
  updateObservabilitySettings
```

---

### Group 4: Edge Cases

#### TC-OB-12: Observability roles do NOT appear in output if not enabled
```
GIVEN: matrix with NO observability permissions checked
WHEN:  payload is built
THEN:  no role key contains "session", "error", "log", "trace", "alert",
       "observability-dashboard", or "vega"
```

#### TC-OB-13: All observability permissions can be enabled simultaneously
```
GIVEN: all 7 observability permissions enabled for one team
WHEN:  payload is built
THEN:
  7 observability roles generated
  No errors raised
  All resources use proj/${projects}:{type}/* pattern (no env)
```

#### TC-OB-14: slugify produces correct role keys
```
GIVEN: permission names with special characters/spaces
THEN:
  "View Sessions"                   → "view-sessions"
  "Manage Observability Dashboards" → "manage-observability-dashboards"
  "Talk to Vega"                    → "talk-to-vega"
```

---

### Group 5: Integration

#### TC-OB-15: Full payload with observability + flags + env permissions
```
GIVEN:
  Teams: [Developer, SRE]
  Project perms: Create Flags=True, View Sessions=True, View Errors=True
  Env perms: Update Targeting=True (production)

WHEN:  payload built

VERIFY:
  Roles include: create-flags, view-sessions, view-errors, update-targeting
  create-flags resource:     contains ":env/*:flag/*"
  view-sessions resource:    contains ":session/*" (no env)
  view-errors resource:      contains ":error/*" (no env)
  update-targeting resource: contains ":env/${roleAttribute/update-targeting-environments}:flag/*"
  Teams have roleAttributes for project + update-targeting-environments
  Teams do NOT have session/error/log attributes (no env scoping needed)
```

---

## Navigation

- [← README](./README.md)
- [Python Concepts →](./PYTHON_CONCEPTS.md)
