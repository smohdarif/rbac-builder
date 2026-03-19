# Phase 3: Payload Builder

> **Goal:** Transform RBACConfig into LaunchDarkly API-ready JSON payloads
> **Depends On:** Phase 1 (Data Models) ✅, Phase 2 (Storage) ✅

---

## Quick Links

| Document | Purpose |
|----------|---------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Deep dive into enums, mappings, transformations |

---

## Overview

### What We're Building

```
services/
├── __init__.py           # Add PayloadBuilder export
├── storage.py            # Phase 2 ✅
└── payload_builder.py    # PayloadBuilder class (THIS PHASE)

core/
├── __init__.py           # Package exports
└── ld_actions.py         # LaunchDarkly action mappings
```

### The Transformation

```
┌─────────────────────┐           ┌─────────────────────┐
│     RBACConfig      │           │   LaunchDarkly      │
│                     │           │   API Payloads      │
│  ☑ create_flags     │    ──►    │                     │
│  ☑ update_flags     │           │  Custom Roles JSON  │
│  ☐ archive_flags    │           │  Teams JSON         │
│                     │           │  Manifest           │
└─────────────────────┘           └─────────────────────┘
      Checkboxes                    API-Ready Format
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Build Custom Roles** | Generate LD custom role JSON from permissions |
| **Build Teams** | Generate LD team JSON with role assignments |
| **Action Mapping** | Map permission checkboxes to LD action codes |
| **Policy Building** | Generate policy statements with resources |
| **Manifest Generation** | Create deployment manifest with order |

---

## PayloadBuilder Methods

```python
from services import PayloadBuilder

# Initialize with config
builder = PayloadBuilder(config)

# Build complete payload
payload = builder.build()

# Access results
roles = payload.roles      # List of custom role dicts
teams = payload.teams      # List of team dicts
manifest = payload.to_manifest()  # Deployment manifest

# Export
json_str = payload.to_json()  # Full JSON export
```

---

## Example Transformation

### Input: RBACConfig

```python
config = RBACConfig(
    customer_name="Acme Corp",
    project_key="mobile-app",
    teams=[Team(key="dev", name="Developer")],
    env_groups=[EnvironmentGroup(key="production")],
    project_permissions=[
        ProjectPermission(team_key="dev", create_flags=True, update_flags=True)
    ],
    env_permissions=[
        EnvironmentPermission(team_key="dev", environment_key="production",
                             update_targeting=False)
    ]
)
```

### Output: Custom Role JSON

```json
{
  "key": "dev-production",
  "name": "Developer - Production",
  "description": "Auto-generated role for Developer in production",
  "policy": [
    {
      "effect": "allow",
      "actions": ["createFlag", "updateName", "updateDescription", ...],
      "resources": ["proj/mobile-app"]
    }
  ]
}
```

### Output: Team JSON

```json
{
  "key": "dev",
  "name": "Developer",
  "description": "Team: Developer",
  "customRoleKeys": ["dev-production"]
}
```

---

## Python Concepts Used

| Concept | What It Does | Learn More |
|---------|--------------|------------|
| `Enum` | Type-safe constants | [Section 1](./PYTHON_CONCEPTS.md#1-python-enums) |
| Dictionary mappings | Lookup tables for actions | [Section 2](./PYTHON_CONCEPTS.md#2-dictionary-mappings) |
| List comprehensions | Transform data efficiently | [Section 3](./PYTHON_CONCEPTS.md#3-advanced-list-comprehensions) |
| f-strings | Build resource strings | [Section 4](./PYTHON_CONCEPTS.md#4-string-formatting-and-building) |
| Builder pattern | Step-by-step construction | [Section 6](./PYTHON_CONCEPTS.md#6-the-builder-pattern) |

---

## Action Mappings

### Project-Level Permissions

| Permission | Maps To |
|------------|---------|
| `create_flags` | `createFlag` |
| `update_flags` | `updateName`, `updateDescription`, `updateTags`, ... |
| `archive_flags` | `deleteFlag` |
| `manage_segments` | `createSegment`, `updateSegment`, `deleteSegment` |

### Environment-Level Permissions

| Permission | Maps To |
|------------|---------|
| `update_targeting` | `updateOn`, `updateTargets`, `updateRules`, ... |
| `apply_changes` | `applyApprovalRequest`, `createApprovalRequest` |
| `review_changes` | `reviewApprovalRequest` |
| `bypass_required_approval` | `bypassRequiredApproval` |

---

## Implementation Checklist

- [ ] `core/__init__.py` - Package setup
- [ ] `core/ld_actions.py` - Action mappings
  - [ ] `PermissionLevel` enum
  - [ ] `PROJECT_ACTIONS` mapping
  - [ ] `ENV_ACTIONS` mapping
  - [ ] `get_actions()` helper
- [ ] `services/payload_builder.py` - PayloadBuilder class
  - [ ] `DeployPayload` dataclass
  - [ ] `build()` - Main build method
  - [ ] `build_custom_roles()` - Build role payloads
  - [ ] `build_teams()` - Build team payloads
  - [ ] `_build_role_for_team_env()` - Single role builder
  - [ ] `_build_project_policy()` - Project policy statements
  - [ ] `_build_env_policy()` - Environment policy statements
  - [ ] `_generate_role_key()` - Role key generator
  - [ ] `_map_permission_to_actions()` - Action mapper
- [ ] Update `services/__init__.py` - Export new classes

---

## Status

| Item | Status |
|------|--------|
| HLD | ✅ Complete |
| DLD | ✅ Complete |
| Pseudo Logic | ✅ Complete |
| Python Concepts Doc | ✅ Complete |
| Implementation | 📋 Not Started |

---

## Integration Points

```python
# Usage in app.py or deployer
from services import StorageService, PayloadBuilder

# Load config
storage = StorageService()
config = storage.load("acme-corp")

# Build payload
builder = PayloadBuilder(config)
payload = builder.build()

# Option 1: Preview
st.json(payload.to_json())

# Option 2: Deploy (future)
deployer.deploy(payload)

# Option 3: Export (future)
export_builder.create_package(payload)
```

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Phase 2: Storage](../phase2/) ✅ | **Phase 3: Payload Builder** | Phase 4: Validation |

[← Back to Phases Index](../)
