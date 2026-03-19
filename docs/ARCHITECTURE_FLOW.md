# RBAC Builder - Architecture & Data Flow

> **Purpose:** This document explains how the different modules (phases) of the RBAC Builder interact with each other. Use this to understand the codebase architecture.

---

## Table of Contents

1. [Overview](#overview)
2. [Phase Dependencies](#phase-dependencies)
3. [Phase 1 & 2: Models + Storage](#phase-1--2-models--storage)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Code Examples](#code-examples)
6. [Future Phases](#future-phases)

---

## Overview

The RBAC Builder is organized into **phases**, where each phase builds on the previous ones:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RBAC BUILDER ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐                                                  │
│   │   UI Layer  │  app.py, ui/*.py                                │
│   │  (Streamlit)│  User interface, session state                  │
│   └──────┬──────┘                                                  │
│          │                                                          │
│          │ uses                                                     │
│          ▼                                                          │
│   ┌─────────────────────────────────────────────────────────────┐ │
│   │                    SERVICES LAYER                            │ │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐│ │
│   │  │  Storage  │  │  Payload  │  │ Validator │  │  Deployer ││ │
│   │  │  Service  │  │  Builder  │  │           │  │           ││ │
│   │  │ (Phase 2) │  │ (Phase 3) │  │ (Phase 4) │  │ (Phase 7) ││ │
│   │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘│ │
│   └────────┼──────────────┼──────────────┼──────────────┼───────┘ │
│            │              │              │              │          │
│            │ all use      │              │              │          │
│            ▼              ▼              ▼              ▼          │
│   ┌─────────────────────────────────────────────────────────────┐ │
│   │                     DATA MODELS (Phase 1)                    │ │
│   │  Team, EnvironmentGroup, ProjectPermission, RBACConfig      │ │
│   └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase Dependencies

```
Phase 1: Data Models ─────────────────────────────────────────────────┐
    │                                                                  │
    │  Provides: Team, EnvironmentGroup, RBACConfig                   │
    │  Used by: ALL other phases                                       │
    │                                                                  │
    ▼                                                                  │
Phase 2: Storage Service ─────────────────────────────────────────────┤
    │                                                                  │
    │  Provides: StorageService (save/load to JSON files)             │
    │  Uses: RBACConfig.to_json(), RBACConfig.from_json()             │
    │                                                                  │
    ▼                                                                  │
Phase 3: Payload Builder (Coming) ────────────────────────────────────┤
    │                                                                  │
    │  Provides: PayloadBuilder (transform to LD API format)          │
    │  Uses: RBACConfig (reads permissions)                           │
    │                                                                  │
    ▼                                                                  │
Phase 4-10: Future phases...                                          │
                                                                       │
───────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1 & 2: Models + Storage

### The Relationship

| Phase 1 (Models) | Phase 2 (Storage) |
|------------------|-------------------|
| Defines **what** data looks like | Handles **where** data goes |
| `RBACConfig` dataclass | Uses `RBACConfig` as input/output |
| `to_json()` method | Calls `config.to_json()` to save |
| `from_json()` method | Calls `RBACConfig.from_json()` to load |
| No file knowledge | Knows about files, paths, backups |

### Visual Interaction

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HOW PHASE 1 & 2 INTERACT                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PHASE 1: DATA MODELS (models/)                                    │
│  ════════════════════════════════                                   │
│  Defines the DATA STRUCTURES                                        │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │    Team      │  │EnvironmentGrp│  │     RBACConfig           │ │
│  │  - key       │  │  - key       │  │  - customer_name         │ │
│  │  - name      │  │  - is_critical│  │  - teams: [Team]        │ │
│  │  - desc      │  │  - notes     │  │  - env_groups: [Env]     │ │
│  │              │  │              │  │  - to_json()             │ │
│  │  to_dict()   │  │  to_dict()   │  │  - from_json()           │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘ │
│         │                 │                      │                 │
│         └─────────────────┼──────────────────────┘                 │
│                           │                                         │
│                           ▼                                         │
│  PHASE 2: STORAGE SERVICE (services/storage.py)                    │
│  ══════════════════════════════════════════════                     │
│  Handles PERSISTENCE (save/load to files)                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                     StorageService                            │ │
│  │                                                               │ │
│  │  save(config: RBACConfig)     ──► config.to_json() ──► file  │ │
│  │  load(name) -> RBACConfig     ◄── RBACConfig.from_json() ◄── │ │
│  │                                                               │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Import Dependencies

```
models/                         services/
═══════                         ═════════
┌─────────────┐                ┌─────────────────┐
│  __init__.py │◄──────────────│  storage.py     │
│             │   imports      │                 │
│  Team       │                │  from models    │
│  EnvGroup   │                │  import         │
│  RBACConfig │                │  RBACConfig     │
└─────────────┘                └─────────────────┘
      │                                │
      │                                │
      ▼                                ▼
No dependencies              Depends on Phase 1
(standalone)
```

### Key Methods That Connect Them

**Phase 1: RBACConfig provides serialization**

```python
# models/config.py

class RBACConfig:
    def to_json(self) -> str:
        """Convert config to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_string: str) -> "RBACConfig":
        """Create config from JSON string."""
        data = json.loads(json_string)
        return cls.from_dict(data)
```

**Phase 2: StorageService uses those methods**

```python
# services/storage.py

class StorageService:
    def save(self, config: RBACConfig) -> Path:
        """Save config to file."""
        json_string = config.to_json()  # ← Calls Phase 1 method
        config_path.write_text(json_string)
        return config_path

    def load(self, customer_name: str) -> RBACConfig:
        """Load config from file."""
        json_string = config_path.read_text()
        return RBACConfig.from_json(json_string)  # ← Calls Phase 1 method
```

---

## Data Flow Diagrams

### Save Flow: UI → Storage → Models → File

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SAVE FLOW                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User clicks "Save"                                              │
│         │                                                           │
│         ▼                                                           │
│  2. UI builds RBACConfig from session_state                        │
│     ┌─────────────────────────────────────────┐                    │
│     │  config = RBACConfig(                   │                    │
│     │      customer_name="Acme",              │  ← Phase 1 object  │
│     │      teams=[Team(key="dev", ...)],      │                    │
│     │  )                                      │                    │
│     └─────────────────────────────────────────┘                    │
│         │                                                           │
│         ▼                                                           │
│  3. UI calls storage.save(config)                                  │
│     ┌─────────────────────────────────────────┐                    │
│     │  storage = StorageService()             │  ← Phase 2 object  │
│     │  path = storage.save(config)            │                    │
│     └─────────────────────────────────────────┘                    │
│         │                                                           │
│         ▼                                                           │
│  4. StorageService internally:                                      │
│     ┌─────────────────────────────────────────┐                    │
│     │  json_string = config.to_json()         │  ← Calls Phase 1   │
│     │  path.write_text(json_string)           │  ← Phase 2 action  │
│     │  _create_backup()                       │  ← Phase 2 action  │
│     └─────────────────────────────────────────┘                    │
│         │                                                           │
│         ▼                                                           │
│  5. File saved to disk                                              │
│     configs/customers/acme/config.json                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Load Flow: File → Storage → Models → UI

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LOAD FLOW                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User selects "Acme" from dropdown                              │
│         │                                                           │
│         ▼                                                           │
│  2. UI calls storage.load("Acme")                                  │
│     ┌─────────────────────────────────────────┐                    │
│     │  config = storage.load("Acme")          │  ← Phase 2 call    │
│     └─────────────────────────────────────────┘                    │
│         │                                                           │
│         ▼                                                           │
│  3. StorageService internally:                                      │
│     ┌─────────────────────────────────────────┐                    │
│     │  json_string = path.read_text()         │  ← Phase 2 action  │
│     │  config = RBACConfig.from_json(...)     │  ← Calls Phase 1   │
│     │  return config                          │                    │
│     └─────────────────────────────────────────┘                    │
│         │                                                           │
│         ▼                                                           │
│  4. UI receives RBACConfig object                                  │
│     ┌─────────────────────────────────────────┐                    │
│     │  config.customer_name  → "Acme"         │  ← Phase 1 object  │
│     │  config.teams[0].name  → "Developer"    │                    │
│     │  config.env_groups     → [...]          │                    │
│     └─────────────────────────────────────────┘                    │
│         │                                                           │
│         ▼                                                           │
│  5. UI populates session_state for display                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Code Examples

### Complete Save Example

```python
from models import RBACConfig, Team, EnvironmentGroup, ProjectPermission
from services import StorageService

# ─────────────────────────────────────────────────────────────────────
# STEP 1: CREATE CONFIG (Phase 1 - Data Models)
# ─────────────────────────────────────────────────────────────────────
config = RBACConfig(
    customer_name="Demo Company",
    project_key="demo-project",
    teams=[
        Team(key="dev", name="Developer", description="Dev team"),
        Team(key="qa", name="QA Engineer", description="QA team"),
    ],
    env_groups=[
        EnvironmentGroup(key="development", is_critical=False),
        EnvironmentGroup(key="production", is_critical=True),
    ],
    project_permissions=[
        ProjectPermission(team_key="dev", create_flags=True, update_flags=True),
        ProjectPermission(team_key="qa", create_flags=False, update_flags=True),
    ],
)

# ─────────────────────────────────────────────────────────────────────
# STEP 2: SAVE (Phase 2 - Storage Service)
# ─────────────────────────────────────────────────────────────────────
storage = StorageService()
saved_path = storage.save(config)
print(f"Saved to: {saved_path}")
# Output: Saved to: configs/customers/demo-company/config.json
```

### Complete Load Example

```python
from services import StorageService

# ─────────────────────────────────────────────────────────────────────
# STEP 1: LOAD (Phase 2 calls Phase 1 internally)
# ─────────────────────────────────────────────────────────────────────
storage = StorageService()
loaded_config = storage.load("Demo Company")

# ─────────────────────────────────────────────────────────────────────
# STEP 2: USE THE DATA (Phase 1 object returned)
# ─────────────────────────────────────────────────────────────────────
print(loaded_config.customer_name)      # "Demo Company"
print(len(loaded_config.teams))         # 2
print(loaded_config.teams[0].name)      # "Developer"
print(loaded_config.teams[0].key)       # "dev"

# Access nested data
for team in loaded_config.teams:
    print(f"Team: {team.name} ({team.key})")

for env in loaded_config.env_groups:
    print(f"Env: {env.key}, Critical: {env.is_critical}")
```

### Template Load Example

```python
from services import StorageService

storage = StorageService()

# List available templates
templates = storage.list_templates()
print(templates)  # ['minimal-2-env', 'standard-4-env']

# Load a template (returns Phase 1 RBACConfig)
config = storage.load_template("standard-4-env")

# Template has placeholder values - customize them
config.customer_name = "My New Customer"
config.project_key = "my-project"

# Save the customized config
storage.save(config)
```

---

## Future Phases

### Phase 3: Payload Builder (Coming Next)

```
┌─────────────────────────────────────────────────────────────────────┐
│                PHASE 3 INTEGRATION (Preview)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1 (Models)      Phase 2 (Storage)     Phase 3 (Payload)     │
│  ════════════════      ═════════════════     ═════════════════     │
│                                                                     │
│  RBACConfig ─────────► StorageService        PayloadBuilder        │
│      │                      │                      │                │
│      │                      │                      │                │
│      │                      ▼                      │                │
│      │               Load config                   │                │
│      │                      │                      │                │
│      └──────────────────────┼──────────────────────┘                │
│                             │                                       │
│                             ▼                                       │
│                      PayloadBuilder(config)                        │
│                             │                                       │
│                             ▼                                       │
│                      LD API JSON Payloads                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Phase 3 will:**
- Take `RBACConfig` as input (from Phase 1)
- Can load config via `StorageService` (from Phase 2)
- Transform to LaunchDarkly API format
- Output deployment-ready JSON

### Full Integration (Future)

```
UI (app.py)
    │
    ├── Creates RBACConfig ────────────────────► Phase 1 (Models)
    │
    ├── Saves/Loads via StorageService ────────► Phase 2 (Storage)
    │
    ├── Transforms via PayloadBuilder ─────────► Phase 3 (Payload)
    │
    ├── Validates via ConfigValidator ─────────► Phase 4 (Validation)
    │
    └── Deploys via Deployer ──────────────────► Phase 7 (Deployer)
```

---

## Quick Reference

### Module Summary

| Phase | Module | Purpose | Key Class |
|-------|--------|---------|-----------|
| 1 | `models/` | Data structures | `RBACConfig` |
| 2 | `services/storage.py` | File persistence | `StorageService` |
| 3 | `services/payload_builder.py` | API transformation | `PayloadBuilder` |
| 4 | `services/validation.py` | Config validation | `ConfigValidator` |

### Import Patterns

```python
# Phase 1: Data Models
from models import RBACConfig, Team, EnvironmentGroup
from models import ProjectPermission, EnvironmentPermission

# Phase 2: Storage
from services import StorageService
from services import ConfigNotFoundError, ConfigParseError

# Phase 3: Payload Builder (coming)
from services import PayloadBuilder, DeployPayload

# Core utilities
from core import is_streamlit_cloud, get_storage_warning
```

### Common Operations

```python
# Create config
config = RBACConfig(customer_name="X", project_key="y", ...)

# Save config
storage = StorageService()
storage.save(config)

# Load config
config = storage.load("Customer Name")

# Load template
config = storage.load_template("standard-4-env")

# List customers
customers = storage.list_customers()

# Export JSON
json_str = storage.export_json(config)

# Import JSON
config = storage.import_json(json_str)
```

---

## See Also

- [Phase 1 Design](./phases/phase1/DESIGN.md) - Data Models
- [Phase 2 Design](./phases/phase2/DESIGN.md) - Storage Service
- [Phase 3 Design](./phases/phase3/DESIGN.md) - Payload Builder
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
