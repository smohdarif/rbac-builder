# RBAC Builder for LaunchDarkly - Design Document

## Overview

A Python-based UI application that allows Solution Architects (SAs) to design RBAC policies for LaunchDarkly customers through an interactive matrix interface, replacing the current Excel-based workflow.

### Key Goals

1. **Interactive Design** - SA can design RBAC with customer on a call using a visual matrix
2. **Flexible Input** - Support both API-connected and manual modes
3. **File Persistence** - Save configurations as JSON for later use
4. **Direct Deployment** - Deploy RBAC directly to LaunchDarkly via API

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DUAL MODE ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                    ┌─────────────────────────────────┐                         │
│                    │      RBAC Builder App           │                         │
│                    └───────────────┬─────────────────┘                         │
│                                    │                                            │
│                         ┌──────────┴──────────┐                                │
│                         │                     │                                │
│                         ▼                     ▼                                │
│              ┌─────────────────┐   ┌─────────────────┐                        │
│              │  CONNECTED MODE │   │   MANUAL MODE   │                        │
│              │  (With API Key) │   │  (No API Key)   │                        │
│              └────────┬────────┘   └────────┬────────┘                        │
│                       │                     │                                  │
│                       ▼                     ▼                                  │
│              ┌─────────────────┐   ┌─────────────────┐                        │
│              │ Auto-fetch:     │   │ Manual input:   │                        │
│              │ • Projects      │   │ • Projects      │                        │
│              │ • Environments  │   │ • Environments  │                        │
│              │ • Existing teams│   │ • Teams         │                        │
│              └────────┬────────┘   └────────┬────────┘                        │
│                       │                     │                                  │
│                       └──────────┬──────────┘                                  │
│                                  │                                              │
│                                  ▼                                              │
│                       ┌─────────────────────┐                                  │
│                       │   PERMISSION MATRIX │  ← Same UI for both modes       │
│                       │   (Design Phase)    │                                  │
│                       └──────────┬──────────┘                                  │
│                                  │                                              │
│                       ┌──────────┴──────────┐                                  │
│                       │                     │                                  │
│                       ▼                     ▼                                  │
│              ┌─────────────────┐   ┌─────────────────┐                        │
│              │ 🚀 DEPLOY       │   │ 💾 SAVE JSON    │                        │
│              │ (API required)  │   │ (Deploy later)  │                        │
│              └─────────────────┘   └─────────────────┘                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites: What Must Exist vs What Gets Created

| Resource | Must Exist Before? | Created by Tool? | Notes |
|----------|-------------------|------------------|-------|
| **Projects** | ✅ Yes | ❌ No | Fetched from LD API or manually entered |
| **Environments** | ✅ Yes | ❌ No | Fetched from LD API or manually entered |
| **Teams** | ❌ No | ✅ Yes | Defined in UI, created during deployment |
| **Custom Roles** | ❌ No | ✅ Yes | Generated from permission matrix |
| **Role Assignments** | ❌ No | ✅ Yes | Team ↔ Role bindings from matrix |

### Why These Prerequisites?

- **Projects** = Product boundaries (created by LD admins, structural)
- **Environments** = Deployment stages (created by LD admins, structural)
- RBAC is built **on top of** these existing structures

---

## Two Modes of Operation

### Mode Comparison

| Feature | Connected Mode | Manual Mode |
|---------|---------------|-------------|
| **API Key Required** | ✅ Yes | ❌ No |
| **Auto-fetch Projects** | ✅ Yes | ❌ Manual entry |
| **Auto-fetch Environments** | ✅ Yes | ❌ Manual entry |
| **Check if Teams Exist** | ✅ Yes | ❌ No |
| **Design Matrix** | ✅ Same UI | ✅ Same UI |
| **Save Config** | ✅ Yes | ✅ Yes |
| **Download JSON** | ✅ Yes | ✅ Yes |
| **Deploy Directly** | ✅ Yes | ❌ Add API key first |
| **Validation** | ✅ Real-time against LD | ⚠️ Basic (format only) |

### When to Use Each Mode

**Connected Mode:**
- SA has API key from customer
- Real-time design with customer on call
- Deploy immediately after design
- Validate against actual LD state
- Best for: Live customer calls

**Manual Mode:**
- Customer hasn't shared API key yet
- Pre-sales/planning phase
- Customer's LD not fully set up yet
- Designing template for later use
- Offline design sessions
- Best for: Initial planning

---

## Application Flow

### Stage 1: Setup & Prerequisites

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🔧 RBAC Builder for LaunchDarkly                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  [1. Setup ●]  [2. Design Matrix]  [3. Review & Deploy]                        │
│                                                                                 │
│  ┌─ Customer Info ──────────────────────────────────────────────────────────┐  │
│  │  Customer Name:  [ Epassi_________________________ ]                     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Data Source ────────────────────────────────────────────────────────────┐  │
│  │                                                                           │  │
│  │  How do you want to provide project/environment data?                    │  │
│  │                                                                           │  │
│  │  ┌─────────────────────────────┐  ┌─────────────────────────────┐        │  │
│  │  │  ◉ CONNECTED MODE           │  │  ○ MANUAL MODE              │        │  │
│  │  │                             │  │                             │        │  │
│  │  │  Fetch from LaunchDarkly    │  │  Enter details manually    │        │  │
│  │  │  API (recommended)          │  │  (no API key needed)       │        │  │
│  │  │                             │  │                             │        │  │
│  │  │  ✓ Auto-fetch projects      │  │  ✓ Design offline          │        │  │
│  │  │  ✓ Auto-fetch environments  │  │  ✓ Deploy later            │        │  │
│  │  │  ✓ Deploy directly          │  │  ✓ Export config           │        │  │
│  │  └─────────────────────────────┘  └─────────────────────────────┘        │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Connected Mode - Setup

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  MODE: 🔗 CONNECTED                                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─ LaunchDarkly Connection ────────────────────────────────────────────────┐  │
│  │  API Key:  [ •••••••••••••••••••••••••••• ]   [🔗 Connect]               │  │
│  │  Status: ✅ Connected to account: epassi-prod                            │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Projects (Auto-fetched) ────────────────────────────────────────────────┐  │
│  │  Select projects to include in RBAC:                                     │  │
│  │  ☑ default           Default Project                                    │  │
│  │  ☑ mobile-app        Mobile Application                                 │  │
│  │  ☐ internal-tools    Internal Tools (exclude)                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Environments (Auto-fetched) ────────────────────────────────────────────┐  │
│  │  ┌──────────────┬────────────────┬────────────┬──────────┐               │  │
│  │  │ Key          │ Name           │ Critical?  │ Include? │               │  │
│  │  ├──────────────┼────────────────┼────────────┼──────────┤               │  │
│  │  │ development  │ Development    │ ☐          │ ☑        │               │  │
│  │  │ test         │ Test           │ ☐          │ ☑        │               │  │
│  │  │ staging      │ Staging        │ ☑          │ ☑        │               │  │
│  │  │ production   │ Production     │ ☑          │ ☑        │               │  │
│  │  └──────────────┴────────────────┴────────────┴──────────┘               │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Teams / Functional Roles ───────────────────────────────────────────────┐  │
│  │  [+ Add Team]   [📥 Import from LD]                                      │  │
│  │  ┌──────────┬──────────────────┬──────────────┬─────────────────────────┐│  │
│  │  │ Key      │ Display Name     │ In LD?       │ Actions                 ││  │
│  │  ├──────────┼──────────────────┼──────────────┼─────────────────────────┤│  │
│  │  │ dev      │ Developer        │ ✅ Exists    │ [🗑]                    ││  │
│  │  │ qa       │ QA Engineer      │ 🆕 New       │ [🗑]                    ││  │
│  │  │ po       │ Product Owner    │ 🆕 New       │ [🗑]                    ││  │
│  │  │ admin    │ Administrator    │ ✅ Exists    │ [🗑]                    ││  │
│  │  └──────────┴──────────────────┴──────────────┴─────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Manual Mode - Setup

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  MODE: 📝 MANUAL                                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─ Projects ───────────────────────────────────────────────────────────────┐  │
│  │  Enter the project keys that will be included in RBAC:                   │  │
│  │  [+ Add Project]                                                          │  │
│  │  ┌──────────────────┬────────────────────────────┬───────────────────┐   │  │
│  │  │ Project Key      │ Display Name (optional)    │ Actions           │   │  │
│  │  ├──────────────────┼────────────────────────────┼───────────────────┤   │  │
│  │  │ [ default      ] │ [ Default Project        ] │ [🗑]              │   │  │
│  │  │ [ mobile-app   ] │ [ Mobile Application     ] │ [🗑]              │   │  │
│  │  └──────────────────┴────────────────────────────┴───────────────────┘   │  │
│  │  ⚠️  Make sure these projects exist in LaunchDarkly before deploying    │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Environments ───────────────────────────────────────────────────────────┐  │
│  │  Enter the environments (these become columns in the matrix):            │  │
│  │  [+ Add Environment]                                                      │  │
│  │  ┌──────────────────┬────────────────────┬────────────┬──────────────┐   │  │
│  │  │ Environment Key  │ Display Name       │ Critical?  │ Actions      │   │  │
│  │  ├──────────────────┼────────────────────┼────────────┼──────────────┤   │  │
│  │  │ [ development  ] │ [ Development    ] │ ☐          │ [🗑]         │   │  │
│  │  │ [ test         ] │ [ Test           ] │ ☐          │ [🗑]         │   │  │
│  │  │ [ staging      ] │ [ Staging        ] │ ☑          │ [🗑]         │   │  │
│  │  │ [ production   ] │ [ Production     ] │ ☑          │ [🗑]         │   │  │
│  │  └──────────────────┴────────────────────┴────────────┴──────────────┘   │  │
│  │  ⚠️  Make sure these environments exist in LaunchDarkly before deploying│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Teams / Functional Roles ───────────────────────────────────────────────┐  │
│  │  Define the teams (these become rows in the matrix):                     │  │
│  │  [+ Add Team]                                                             │  │
│  │  ┌──────────────────┬────────────────────────────┬───────────────────┐   │  │
│  │  │ Team Key         │ Display Name               │ Actions           │   │  │
│  │  ├──────────────────┼────────────────────────────┼───────────────────┤   │  │
│  │  │ [ dev          ] │ [ Developer              ] │ [🗑]              │   │  │
│  │  │ [ qa           ] │ [ QA Engineer            ] │ [🗑]              │   │  │
│  │  │ [ po           ] │ [ Product Owner          ] │ [🗑]              │   │  │
│  │  │ [ admin        ] │ [ Administrator          ] │ [🗑]              │   │  │
│  │  └──────────────────┴────────────────────────────┴───────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Stage 2: Permission Matrix (Design Phase)

This is the core UI where SA and customer design the RBAC together. It mirrors the existing Excel sheet format.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🔧 RBAC Builder for LaunchDarkly                     Customer: Epassi         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  [1. Setup ✓]  [2. Design Matrix ●]  [3. Deploy]           [💾 Save Draft]     │
│                                                                                 │
│  ┌─ Permission Matrix ──────────────────────────────────────────────────────┐  │
│  │                                                                           │  │
│  │         │░░ PROJECT SCOPE ░░│░░░ DEVELOPMENT ░░░│░░░░░ TEST ░░░░░│       │  │
│  │         │    (All Envs)     │   (Non-Critical)  │  (Non-Critical) │       │  │
│  │  ┌──────┼─────┬─────┬───────┼─────┬─────┬───┬───┼─────┬─────┬───┬───┤    │  │
│  │  │ Role │Creat│Updat│Archive│Targe│Revie│App│Seg│Targe│Revie│App│Seg│    │  │
│  │  │      │Flags│Flags│Flags  │ting │w    │ly │mnt│ting │w    │ly │mnt│    │  │
│  │  ├──────┼─────┼─────┼───────┼─────┼─────┼───┼───┼─────┼─────┼───┼───┤    │  │
│  │  │ Dev  │ [✓] │ [✓] │ [ ]   │ [✓] │ [✓] │[✓]│[✓]│ [✓] │ [✓] │[ ]│[✓]│    │  │
│  │  │ QA   │ [ ] │ [ ] │ [ ]   │ [ ] │ [ ] │[ ]│[ ]│ [✓] │ [✓] │[✓]│[✓]│    │  │
│  │  │ PO   │ [ ] │ [✓] │ [ ]   │ [ ] │ [✓] │[ ]│[ ]│ [ ] │ [✓] │[ ]│[ ]│    │  │
│  │  │Admin │ [✓] │ [✓] │ [✓]   │ [✓] │ [✓] │[✓]│[✓]│ [✓] │ [✓] │[✓]│[✓]│    │  │
│  │  └──────┴─────┴─────┴───────┴─────┴─────┴───┴───┴─────┴─────┴───┴───┘    │  │
│  │                                                                           │  │
│  │         │░ STAGING (Critical)░│░PRODUCTION (Critical)░│                  │  │
│  │  ┌──────┼─────┬─────┬───┬─────┼─────┬─────┬───┬────────┤                  │  │
│  │  │ Role │Targe│Revie│App│Segmt│Targe│Revie│App│Segmt   │                  │  │
│  │  ├──────┼─────┼─────┼───┼─────┼─────┼─────┼───┼────────┤                  │  │
│  │  │ Dev  │ [ ] │ [✓] │[ ]│ [ ] │ [ ] │ [ ] │[ ]│ [ ]    │                  │  │
│  │  │ QA   │ [✓] │ [✓] │[✓]│ [✓] │ [ ] │ [✓] │[ ]│ [ ]    │                  │  │
│  │  │ PO   │ [ ] │ [✓] │[ ]│ [ ] │ [ ] │ [✓] │[ ]│ [ ]    │                  │  │
│  │  │Admin │ [✓] │ [✓] │[✓]│ [✓] │ [✓] │ [✓] │[✓]│ [✓]    │                  │  │
│  │  └──────┴─────┴─────┴───┴─────┴─────┴─────┴───┴────────┘                  │  │
│  │                                                                           │  │
│  │  Legend: Critical environments highlighted in red/orange                 │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Quick Actions ──────────────────────────────────────────────────────────┐  │
│  │  [Select All for Role ▼]  [Clear All for Role ▼]  [Copy from Role ▼]    │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Available Permissions

**Project-Scoped Actions:**
- Create Flags
- Update Flags
- Archive Flags
- Manage Metrics
- Manage Release Pipelines
- Update Client-Side Availability
- Manage Context Kinds

**Environment-Scoped Actions:**
- Update Targeting
- Review Changes
- Apply Changes
- Manage Segments
- View SDK Key
- Manage Experiments
- Manage Holdouts
- Manage Triggers

### Stage 3: Review & Deploy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🔧 RBAC Builder                                          Customer: Epassi     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  [1. Setup ✓]  [2. Design Matrix ✓]  [3. Review & Deploy ●]                    │
│                                                                                 │
│  ┌─ Deployment Summary ─────────────────────────────────────────────────────┐  │
│  │                                                                           │  │
│  │  WILL BE CREATED:                                                        │  │
│  │  ├── 12 Custom Roles                                                     │  │
│  │  │   ├── project-create-flags                                            │  │
│  │  │   ├── project-update-flags                                            │  │
│  │  │   ├── project-archive-flags                                           │  │
│  │  │   ├── env-development-targeting                                       │  │
│  │  │   ├── env-development-apply                                           │  │
│  │  │   └── ... (7 more)                                                    │  │
│  │  │                                                                        │  │
│  │  └── 4 Teams with role assignments                                       │  │
│  │      ├── dev (Developer) → 8 roles                                       │  │
│  │      ├── qa (QA Engineer) → 6 roles                                      │  │
│  │      ├── po (Product Owner) → 4 roles                                    │  │
│  │      └── admin (Administrator) → 12 roles                                │  │
│  │                                                                           │  │
│  │  PREREQUISITES (must exist in LD):                                       │  │
│  │  ├── Projects: default, mobile-app                                       │  │
│  │  └── Environments: development, test, staging, production                │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Validation ─────────────────────────────────────────────────────────────┐  │
│  │  ✅ All projects exist in LaunchDarkly                                   │  │
│  │  ✅ All environments exist in LaunchDarkly                               │  │
│  │  ✅ No conflicting role names                                            │  │
│  │  ⚠️  2 teams will be created (qa, po)                                    │  │
│  │  ⚠️  2 teams will be updated (dev, admin)                                │  │
│  │  ✅ Admin role has full access to production                             │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Preview JSON (Expandable) ──────────────────────────────────────────────┐  │
│  │  [▼ Show JSON Payload]                                                   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌─ Actions ────────────────────────────────────────────────────────────────┐  │
│  │                                                                           │  │
│  │  CONNECTED MODE:                                                         │  │
│  │  [💾 Save Config]  [📥 Download JSON]  [🚀 Deploy to LaunchDarkly]       │  │
│  │                                                                           │  │
│  │  ─── OR ───                                                              │  │
│  │                                                                           │  │
│  │  MANUAL MODE (No API Key):                                               │  │
│  │  [💾 Save Config]  [📥 Download JSON]  [🔗 Add API Key to Deploy]        │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Core Data Structures

```python
@dataclass
class Project:
    key: str
    name: str
    included: bool = True

@dataclass
class Environment:
    key: str
    name: str
    is_critical: bool
    included: bool = True

@dataclass
class Team:
    key: str
    name: str
    description: str = ""
    exists_in_ld: bool = False  # Only known in connected mode

@dataclass
class ProjectPermissions:
    create_flags: bool = False
    update_flags: bool = False
    archive_flags: bool = False
    manage_metrics: bool = False
    manage_release_pipelines: bool = False
    update_client_side_availability: bool = False
    manage_context_kinds: bool = False

@dataclass
class EnvironmentPermissions:
    update_targeting: bool = False
    review_changes: bool = False
    apply_changes: bool = False
    manage_segments: bool = False
    view_sdk_key: bool = False
    manage_experiments: bool = False
    manage_holdouts: bool = False
    manage_triggers: bool = False

@dataclass
class TeamPermissions:
    team_key: str
    project: ProjectPermissions
    environments: dict[str, EnvironmentPermissions]  # env_key -> permissions

@dataclass
class RBACConfig:
    customer_name: str
    mode: str  # "connected" or "manual"
    created_at: datetime
    updated_at: datetime
    last_deployed_at: datetime | None

    projects: list[Project]
    environments: list[Environment]
    teams: list[Team]
    permissions: dict[str, TeamPermissions]  # team_key -> permissions

    # Only in connected mode
    ld_account: str | None = None
    api_key_hash: str | None = None  # For validation, never store actual key
```

---

## File Persistence

### Storage Structure

```
rbac-builder/
├── app.py
├── configs/
│   └── customers/
│       ├── epassi/
│       │   ├── config.json              # Current configuration
│       │   ├── deployed_2024-03-11.json # Snapshot after deployment
│       │   └── history/
│       │       ├── 2024-03-10.json
│       │       └── 2024-03-08.json
│       │
│       └── acme-corp/
│           └── config.json
│
└── templates/                            # Reusable starting points
    ├── standard-4-env.json
    └── minimal-2-env.json
```

### Config JSON Format

```json
{
  "version": "1.0",
  "customer_name": "Epassi",
  "mode": "manual",
  "created_at": "2024-03-11T10:00:00Z",
  "updated_at": "2024-03-11T14:30:00Z",
  "last_deployed_at": null,

  "projects": [
    {"key": "default", "name": "Default Project", "included": true},
    {"key": "mobile-app", "name": "Mobile Application", "included": true}
  ],

  "environments": [
    {"key": "development", "name": "Development", "is_critical": false, "included": true},
    {"key": "test", "name": "Test", "is_critical": false, "included": true},
    {"key": "staging", "name": "Staging", "is_critical": true, "included": true},
    {"key": "production", "name": "Production", "is_critical": true, "included": true}
  ],

  "teams": [
    {"key": "dev", "name": "Developer", "description": "Development team"},
    {"key": "qa", "name": "QA Engineer", "description": "Quality assurance"},
    {"key": "po", "name": "Product Owner", "description": "Product management"},
    {"key": "admin", "name": "Administrator", "description": "Full access"}
  ],

  "permissions": {
    "dev": {
      "project": {
        "create_flags": true,
        "update_flags": true,
        "archive_flags": false,
        "manage_metrics": false,
        "manage_release_pipelines": false,
        "update_client_side_availability": false,
        "manage_context_kinds": false
      },
      "environments": {
        "development": {
          "update_targeting": true,
          "review_changes": true,
          "apply_changes": true,
          "manage_segments": true,
          "view_sdk_key": true,
          "manage_experiments": false,
          "manage_holdouts": false,
          "manage_triggers": false
        },
        "test": {
          "update_targeting": true,
          "review_changes": true,
          "apply_changes": false,
          "manage_segments": true,
          "view_sdk_key": true,
          "manage_experiments": false,
          "manage_holdouts": false,
          "manage_triggers": false
        },
        "staging": {
          "update_targeting": false,
          "review_changes": true,
          "apply_changes": false,
          "manage_segments": false,
          "view_sdk_key": false,
          "manage_experiments": false,
          "manage_holdouts": false,
          "manage_triggers": false
        },
        "production": {
          "update_targeting": false,
          "review_changes": false,
          "apply_changes": false,
          "manage_segments": false,
          "view_sdk_key": false,
          "manage_experiments": false,
          "manage_holdouts": false,
          "manage_triggers": false
        }
      }
    },
    "qa": { },
    "po": { },
    "admin": { }
  }
}
```

---

## LaunchDarkly API Integration

### Deployment Sequence

```
STEP 1: Create Custom Roles (no dependencies)
────────────────────────────────────────────
POST /api/v2/roles

For each unique permission combination, create a role:
- project-create-flags
- project-update-flags
- project-archive-flags
- env-{env-key}-update-targeting
- env-{env-key}-apply-changes
- env-{env-key}-manage-segments
- etc.


STEP 2: Create/Update Teams (depends on roles existing)
───────────────────────────────────────────────────────
POST /api/v2/teams (for new teams)
PATCH /api/v2/teams/{key} (for existing teams)

Include:
- customRoleKeys: [...list of role keys...]


STEP 3: Verification
────────────────────
GET /api/v2/teams/{key}
Verify roles are correctly assigned
```

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v2/projects` | GET | Fetch existing projects |
| `/api/v2/projects/{key}/environments` | GET | Fetch environments |
| `/api/v2/teams` | GET | Fetch existing teams |
| `/api/v2/roles` | GET | Fetch existing custom roles |
| `/api/v2/roles` | POST | Create custom role |
| `/api/v2/teams` | POST | Create team |
| `/api/v2/teams/{key}` | PATCH | Update team (assign roles) |

---

## Project Structure

```
rbac-builder/
├── app.py                      # Main Streamlit entry point
├── config.py                   # App configuration
├── requirements.txt            # Python dependencies
│
├── models/
│   ├── __init__.py
│   ├── project.py              # Project dataclass
│   ├── environment.py          # Environment dataclass
│   ├── team.py                 # Team dataclass
│   ├── permissions.py          # Permission dataclasses
│   └── rbac_config.py          # Full config model
│
├── services/
│   ├── __init__.py
│   ├── ld_api_client.py        # LaunchDarkly API client
│   ├── config_storage.py       # JSON file persistence
│   ├── payload_builder.py      # Build API payloads from config
│   └── validation.py           # Validation logic
│
├── ui/
│   ├── __init__.py
│   ├── setup_tab.py            # Stage 1: Setup UI
│   ├── matrix_tab.py           # Stage 2: Permission matrix
│   ├── deploy_tab.py           # Stage 3: Review & deploy
│   └── components.py           # Reusable UI components
│
├── configs/                    # Saved customer configs
│   └── customers/
│
└── templates/                  # Starter templates
    └── standard-4-env.json
```

---

## User Workflow

### SA + Customer Call Workflow

```
BEFORE THE CALL:
────────────────
• Customer has LaunchDarkly account set up
• Projects already created (e.g., "web-app", "mobile-app")
• Environments already created (e.g., dev, test, staging, prod)
• Customer provides API key to SA (optional - can use manual mode)

ON THE CALL:
────────────
1. SA opens RBAC Builder UI
2. Enters customer name
3. Chooses mode:
   - Connected: Enter API key, auto-fetch projects/environments
   - Manual: Enter projects/environments manually

4. Define teams together:
   "What teams/roles do you have?"
   → "Developers, QA, Product, and Admins"
   → SA adds these teams in the UI

5. Walk through permission matrix together:
   "Should Developers be able to create flags?" → ✓
   "Should Developers apply changes in production?" → ✗
   "Should QA apply changes in test?" → ✓
   ... (fill out matrix together)

6. Save configuration
7. Deploy (if connected mode) or export for later

AFTER THE CALL:
───────────────
• Customer adds team members to teams in LaunchDarkly UI
• SA can revisit saved config to make changes later
• Config can be shared with customer for review
```

---

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **UI Framework** | Streamlit | Fast iteration, good for forms |
| **Matrix Grid** | `st.data_editor` | Native checkbox support |
| **State Management** | `st.session_state` | Persist across reruns |
| **Persistence** | JSON files | Simple, portable |
| **API Client** | `requests` | Standard HTTP client |
| **Data Models** | `dataclasses` | Clean Python models |

---

---

## Implementation Modules

The application is divided into logical modules for clean separation of concerns and easier development.

### Module Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MODULE ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                              ┌─────────────────┐                               │
│                              │     app.py      │                               │
│                              │  (Entry Point)  │                               │
│                              └────────┬────────┘                               │
│                                       │                                         │
│                    ┌──────────────────┼──────────────────┐                     │
│                    │                  │                  │                     │
│                    ▼                  ▼                  ▼                     │
│           ┌──────────────┐   ┌──────────────┐   ┌──────────────┐              │
│           │   UI Layer   │   │   UI Layer   │   │   UI Layer   │              │
│           │  setup_tab   │   │  matrix_tab  │   │  deploy_tab  │              │
│           └──────┬───────┘   └──────┬───────┘   └──────┬───────┘              │
│                  │                  │                  │                       │
│                  └──────────────────┼──────────────────┘                       │
│                                     │                                           │
│                    ┌────────────────┼────────────────┐                         │
│                    │                │                │                         │
│                    ▼                ▼                ▼                         │
│           ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐              │
│           │   Services   │  │   Services  │  │    Services     │              │
│           │  ld_client   │  │   storage   │  │ payload_builder │              │
│           └──────┬───────┘  └──────┬──────┘  └────────┬────────┘              │
│                  │                 │                  │                        │
│                  └─────────────────┼──────────────────┘                        │
│                                    │                                            │
│                    ┌───────────────┼───────────────┐                           │
│                    │               │               │                           │
│                    ▼               ▼               ▼                           │
│           ┌──────────────┐ ┌─────────────┐ ┌─────────────────┐                │
│           │    Core      │ │    Core     │ │      Core       │                │
│           │   models     │ │  constants  │ │   validation    │                │
│           └──────────────┘ └─────────────┘ └─────────────────┘                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Module Breakdown

#### Module 1: Core Models (`models/`)

**Purpose:** Define all data structures used throughout the application.

**Files:**
```
models/
├── __init__.py
├── project.py          # Project dataclass
├── environment.py      # Environment dataclass
├── team.py             # Team dataclass
├── permissions.py      # Permission dataclasses
├── config.py           # RBACConfig (main config model)
└── payload.py          # API payload models
```

**Key Classes:**

```python
# models/project.py
@dataclass
class Project:
    key: str
    name: str
    included: bool = True

# models/environment.py
@dataclass
class Environment:
    key: str
    name: str
    is_critical: bool = False
    included: bool = True

# models/team.py
@dataclass
class Team:
    key: str
    name: str
    description: str = ""
    exists_in_ld: bool = False

# models/permissions.py
@dataclass
class ProjectPermissions:
    create_flags: bool = False
    update_flags: bool = False
    archive_flags: bool = False
    manage_metrics: bool = False
    manage_release_pipelines: bool = False
    update_client_side_availability: bool = False
    view_project: bool = True

@dataclass
class EnvironmentPermissions:
    update_targeting: bool = False
    review_changes: bool = False
    apply_changes: bool = False
    manage_segments: bool = False
    view_sdk_key: bool = False

@dataclass
class TeamPermissions:
    team_key: str
    project: ProjectPermissions
    environments: Dict[str, EnvironmentPermissions]

# models/config.py
@dataclass
class RBACConfig:
    customer_name: str
    mode: str  # "connected" or "manual"
    projects: List[Project]
    environments: List[Environment]
    teams: List[Team]
    permissions: Dict[str, TeamPermissions]
    created_at: datetime
    updated_at: datetime
    ld_account: Optional[str] = None
```

**Dependencies:** None (base layer)

---

#### Module 2: Constants & Mappings (`core/`)

**Purpose:** Store all static configuration, permission mappings, and LaunchDarkly action definitions.

**Files:**
```
core/
├── __init__.py
├── constants.py        # App-wide constants
└── permission_mapping.py  # UI permission → LD actions mapping
```

**Key Content:**

```python
# core/constants.py
APP_VERSION = "1.0.0"
CONFIG_DIR = "configs/customers"
TEMPLATES_DIR = "templates"

# LaunchDarkly API
LD_API_BASE_URL = "https://app.launchdarkly.com/api/v2"
LD_API_VERSION = "20220603"

# core/permission_mapping.py
PROJECT_PERMISSIONS = {
    "create_flags": {
        "key": "create-flags",
        "name": "Create Flags",
        "actions": ["createFlag", "cloneFlag"],
        "resource_template": "proj/*:env/*:flag/*"
    },
    "update_flags": {
        "key": "update-flags",
        "name": "Update Flags",
        "actions": [
            "updateName", "updateDescription", "updateTags",
            "updateDeprecated", "updateMaintainer", "updateTemporary",
            "createFlagLink", "deleteFlagLink", "updateFlagLink",
            "manageFlagFollowers", "updateFlagCustomProperties",
            "updateFlagDefaultVariations"
        ],
        "resource_template": "proj/*:env/*:flag/*"
    },
    "archive_flags": {
        "key": "archive-flags",
        "name": "Archive Flags",
        "actions": ["updateGlobalArchived"],
        "resource_template": "proj/*:env/*:flag/*"
    },
    # ... more mappings
}

ENVIRONMENT_PERMISSIONS = {
    "update_targeting": {
        "key": "update-targeting",
        "name": "Update Targeting",
        "actions": [
            "updateOn", "updateRules", "updateTargets",
            "updateFallthrough", "updateOffVariation",
            "updatePrerequisites", "updateScheduledChanges",
            "copyFlagConfigFrom", "copyFlagConfigTo",
            "createApprovalRequest", "updateExpiringTargets"
        ],
        "resource_template": "proj/*:env/{env}:flag/*"
    },
    "apply_changes": {
        "key": "apply-changes",
        "name": "Apply Changes",
        "actions": ["applyApprovalRequest"],
        "resource_template": "proj/*:env/{env}:flag/*"
    },
    "review_changes": {
        "key": "review-changes",
        "name": "Review Changes",
        "actions": ["reviewApprovalRequest", "updateApprovalRequest"],
        "resource_template": "proj/*:env/{env}:flag/*"
    },
    "manage_segments": {
        "key": "manage-segments",
        "name": "Manage Segments",
        "actions": [
            "createSegment", "deleteSegment",
            "updateName", "updateDescription", "updateTags",
            "updateIncluded", "updateExcluded", "updateRules"
        ],
        "resource_template": "proj/*:env/{env}:segment/*"
    },
    "view_sdk_key": {
        "key": "view-sdk-key",
        "name": "View SDK Key",
        "actions": ["viewSdkKey"],
        "resource_template": "proj/*:env/{env}"
    }
}
```

**Dependencies:** None

---

#### Module 3: LaunchDarkly API Client (`services/ld_client.py`)

**Purpose:** Handle all interactions with LaunchDarkly API.

**Files:**
```
services/
├── __init__.py
└── ld_client.py
```

**Key Functions:**

```python
# services/ld_client.py
class LaunchDarklyClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = LD_API_BASE_URL

    # Connection & Validation
    def test_connection(self) -> Tuple[bool, str]:
        """Test API key and return account info"""

    # Fetch Operations (Connected Mode)
    def get_projects(self) -> List[Project]:
        """Fetch all projects from LD"""

    def get_environments(self, project_key: str) -> List[Environment]:
        """Fetch environments for a project"""

    def get_teams(self) -> List[Team]:
        """Fetch existing teams"""

    def get_custom_roles(self) -> List[dict]:
        """Fetch existing custom roles"""

    # Create Operations (Deployment)
    def create_custom_role(self, role: dict) -> Tuple[bool, str]:
        """Create a custom role"""

    def update_custom_role(self, role_key: str, role: dict) -> Tuple[bool, str]:
        """Update existing custom role"""

    def create_team(self, team: dict) -> Tuple[bool, str]:
        """Create a new team"""

    def update_team(self, team_key: str, team: dict) -> Tuple[bool, str]:
        """Update existing team with role assignments"""

    # Check Operations
    def role_exists(self, role_key: str) -> bool:
        """Check if a custom role exists"""

    def team_exists(self, team_key: str) -> bool:
        """Check if a team exists"""
```

**Dependencies:** `models/`, `core/constants`

---

#### Module 4: Configuration Storage (`services/storage.py`)

**Purpose:** Handle saving/loading configurations to/from JSON files.

**Files:**
```
services/
└── storage.py
```

**Key Functions:**

```python
# services/storage.py
class ConfigStorage:
    def __init__(self, base_dir: str = CONFIG_DIR):
        self.base_dir = base_dir

    # Save Operations
    def save_config(self, config: RBACConfig) -> str:
        """Save config to JSON file, return file path"""

    def save_deployed_snapshot(self, config: RBACConfig) -> str:
        """Save snapshot after successful deployment"""

    def auto_save_draft(self, config: RBACConfig) -> str:
        """Auto-save current work as draft"""

    # Load Operations
    def load_config(self, customer_name: str) -> Optional[RBACConfig]:
        """Load config for a customer"""

    def list_customers(self) -> List[str]:
        """List all saved customer configs"""

    def list_customer_history(self, customer_name: str) -> List[dict]:
        """List config history for a customer"""

    # Export Operations
    def export_to_json(self, config: RBACConfig) -> str:
        """Export config as JSON string"""

    def export_to_file(self, config: RBACConfig, file_path: str) -> None:
        """Export config to specific file"""

    # Import Operations
    def import_from_json(self, json_str: str) -> RBACConfig:
        """Import config from JSON string"""

    def import_from_file(self, file_path: str) -> RBACConfig:
        """Import config from file"""
```

**Dependencies:** `models/`

---

#### Module 5: Payload Builder (`services/payload_builder.py`)

**Purpose:** Transform UI matrix data into LaunchDarkly API payloads.

**Files:**
```
services/
└── payload_builder.py
```

**Key Functions:**

```python
# services/payload_builder.py
class PayloadBuilder:
    def __init__(self):
        self.permission_mapping = {
            **PROJECT_PERMISSIONS,
            **ENVIRONMENT_PERMISSIONS
        }

    # Main Build Function
    def build_rbac_bundle(self, config: RBACConfig) -> dict:
        """Build complete RBAC bundle from config"""

    # Role Generation
    def generate_roles(self, config: RBACConfig) -> List[dict]:
        """Generate unique custom roles from matrix"""

    def create_role_definition(
        self,
        scope: str,
        permission: str,
        env_key: str = None
    ) -> dict:
        """Create single role definition"""

    # Team Generation
    def generate_teams(
        self,
        config: RBACConfig,
        roles: List[dict]
    ) -> List[dict]:
        """Generate team definitions with role assignments"""

    def get_team_roles(
        self,
        team_key: str,
        permissions: TeamPermissions,
        available_roles: Set[str]
    ) -> List[str]:
        """Get list of role keys for a team"""

    # Utility Functions
    def get_roles_needed(self, config: RBACConfig) -> Set[Tuple]:
        """Scan matrix to find which roles are needed"""

    def format_role_key(self, scope: str, permission: str, env_key: str = None) -> str:
        """Generate consistent role key"""

    def format_role_name(self, scope: str, permission: str, env_key: str = None) -> str:
        """Generate human-readable role name"""
```

**Dependencies:** `models/`, `core/permission_mapping`

---

#### Module 6: Validation (`services/validation.py`)

**Purpose:** Validate configurations before deployment.

**Files:**
```
services/
└── validation.py
```

**Key Functions:**

```python
# services/validation.py
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class ConfigValidator:
    def __init__(self, ld_client: Optional[LaunchDarklyClient] = None):
        self.ld_client = ld_client

    # Full Validation
    def validate(self, config: RBACConfig) -> ValidationResult:
        """Run all validations"""

    # Structure Validation (works in manual mode)
    def validate_structure(self, config: RBACConfig) -> ValidationResult:
        """Validate config structure and format"""

    def validate_team_keys(self, teams: List[Team]) -> List[str]:
        """Validate team keys are valid format"""

    def validate_environment_keys(self, envs: List[Environment]) -> List[str]:
        """Validate environment keys"""

    def validate_permissions_complete(self, config: RBACConfig) -> List[str]:
        """Check all teams have permission entries"""

    # LaunchDarkly Validation (requires connected mode)
    def validate_against_ld(self, config: RBACConfig) -> ValidationResult:
        """Validate config against actual LD state"""

    def validate_projects_exist(self, projects: List[Project]) -> List[str]:
        """Check projects exist in LD"""

    def validate_environments_exist(
        self,
        projects: List[Project],
        environments: List[Environment]
    ) -> List[str]:
        """Check environments exist in LD"""

    def check_role_conflicts(self, roles: List[dict]) -> List[str]:
        """Check for conflicting role names"""

    # Warnings
    def check_admin_access(self, config: RBACConfig) -> List[str]:
        """Warn if no team has full admin access"""

    def check_orphan_permissions(self, config: RBACConfig) -> List[str]:
        """Warn about teams with no permissions"""
```

**Dependencies:** `models/`, `services/ld_client`

---

#### Module 7: Deployment Service (`services/deployer.py`)

**Purpose:** Execute deployment to LaunchDarkly.

**Files:**
```
services/
└── deployer.py
```

**Key Functions:**

```python
# services/deployer.py
@dataclass
class DeploymentResult:
    success: bool
    roles_created: List[str]
    roles_updated: List[str]
    teams_created: List[str]
    teams_updated: List[str]
    errors: List[str]

class Deployer:
    def __init__(self, ld_client: LaunchDarklyClient):
        self.ld_client = ld_client

    # Main Deployment
    def deploy(self, bundle: dict) -> DeploymentResult:
        """Deploy RBAC bundle to LaunchDarkly"""

    # Step-by-step Deployment
    def deploy_roles(self, roles: List[dict]) -> Tuple[List[str], List[str], List[str]]:
        """Deploy custom roles, return (created, updated, errors)"""

    def deploy_teams(self, teams: List[dict]) -> Tuple[List[str], List[str], List[str]]:
        """Deploy teams, return (created, updated, errors)"""

    # Verification
    def verify_deployment(self, bundle: dict) -> List[str]:
        """Verify all resources were created correctly"""

    # Rollback (future)
    def rollback(self, deployment_result: DeploymentResult) -> bool:
        """Rollback a failed deployment"""
```

**Dependencies:** `models/`, `services/ld_client`, `services/payload_builder`

---

#### Module 8: UI - Setup Tab (`ui/setup_tab.py`)

**Purpose:** Render Stage 1 UI for configuration setup.

**Files:**
```
ui/
├── __init__.py
├── setup_tab.py
└── components/
    └── __init__.py
```

**Key Functions:**

```python
# ui/setup_tab.py
def render_setup_tab(state: SessionState) -> None:
    """Render the complete setup tab"""

def render_customer_info(state: SessionState) -> None:
    """Render customer name input"""

def render_mode_selector(state: SessionState) -> None:
    """Render connected/manual mode selection"""

def render_connected_mode(state: SessionState) -> None:
    """Render API key input and auto-fetch UI"""

def render_manual_mode(state: SessionState) -> None:
    """Render manual input forms"""

def render_projects_section(state: SessionState, mode: str) -> None:
    """Render projects list (fetched or manual)"""

def render_environments_section(state: SessionState, mode: str) -> None:
    """Render environments list with critical toggle"""

def render_teams_section(state: SessionState) -> None:
    """Render teams/functional roles editor"""
```

**Dependencies:** `models/`, `services/ld_client`, `services/storage`

---

#### Module 9: UI - Matrix Tab (`ui/matrix_tab.py`)

**Purpose:** Render Stage 2 UI for permission matrix.

**Files:**
```
ui/
└── matrix_tab.py
```

**Key Functions:**

```python
# ui/matrix_tab.py
def render_matrix_tab(state: SessionState) -> None:
    """Render the complete matrix tab"""

def render_permission_matrix(state: SessionState) -> None:
    """Render the main permission matrix grid"""

def build_matrix_dataframe(state: SessionState) -> pd.DataFrame:
    """Build DataFrame for st.data_editor"""

def parse_matrix_changes(edited_df: pd.DataFrame, state: SessionState) -> None:
    """Parse changes from edited DataFrame back to state"""

def render_project_permissions_columns() -> List[str]:
    """Get column names for project permissions"""

def render_environment_columns(env_key: str) -> List[str]:
    """Get column names for environment permissions"""

def render_quick_actions(state: SessionState) -> None:
    """Render quick action buttons (select all, clear, copy)"""

def apply_template(state: SessionState, template_name: str) -> None:
    """Apply a permission template to matrix"""
```

**Dependencies:** `models/`, `core/permission_mapping`

---

#### Module 10: UI - Deploy Tab (`ui/deploy_tab.py`)

**Purpose:** Render Stage 3 UI for review and deployment.

**Files:**
```
ui/
└── deploy_tab.py
```

**Key Functions:**

```python
# ui/deploy_tab.py
def render_deploy_tab(state: SessionState) -> None:
    """Render the complete deploy tab"""

def render_deployment_summary(state: SessionState) -> None:
    """Render summary of what will be created"""

def render_validation_status(state: SessionState) -> None:
    """Render validation results"""

def render_json_preview(state: SessionState) -> None:
    """Render expandable JSON preview"""

def render_action_buttons(state: SessionState) -> None:
    """Render save/download/deploy buttons"""

def handle_save_config(state: SessionState) -> None:
    """Handle save config button click"""

def handle_download_json(state: SessionState) -> None:
    """Handle download JSON button click"""

def handle_deploy(state: SessionState) -> None:
    """Handle deploy button click"""

def render_deployment_progress(state: SessionState) -> None:
    """Render deployment progress UI"""

def render_deployment_result(result: DeploymentResult) -> None:
    """Render deployment result summary"""
```

**Dependencies:** `models/`, `services/payload_builder`, `services/validation`, `services/deployer`, `services/storage`

---

#### Module 11: Main Application (`app.py`)

**Purpose:** Entry point, orchestrate all modules.

**Files:**
```
app.py
```

**Key Functions:**

```python
# app.py
def main():
    """Main application entry point"""

    # Page config
    st.set_page_config(
        page_title="RBAC Builder for LaunchDarkly",
        page_icon="🔧",
        layout="wide"
    )

    # Initialize session state
    initialize_session_state()

    # Render header
    render_header()

    # Render tabs
    tab1, tab2, tab3 = st.tabs(["1. Setup", "2. Design Matrix", "3. Review & Deploy"])

    with tab1:
        render_setup_tab(st.session_state)

    with tab2:
        render_matrix_tab(st.session_state)

    with tab3:
        render_deploy_tab(st.session_state)

def initialize_session_state():
    """Initialize all session state variables"""

def render_header():
    """Render app header with customer name and save status"""
```

**Dependencies:** All UI modules, all services

---

### Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DEPENDENCY GRAPH                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Level 0 (No Dependencies):                                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  models/           core/constants      core/permission_mapping         │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                          │
│                                      ▼                                          │
│  Level 1 (Depends on Level 0):                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  services/ld_client    services/storage    services/payload_builder    │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                          │
│                                      ▼                                          │
│  Level 2 (Depends on Level 1):                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  services/validation                   services/deployer               │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                          │
│                                      ▼                                          │
│  Level 3 (Depends on Level 2):                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  ui/setup_tab      ui/matrix_tab       ui/deploy_tab                   │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                          │
│                                      ▼                                          │
│  Level 4 (Entry Point):                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │                              app.py                                    │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Implementation Order

Recommended order to implement modules:

| Phase | Modules | Description |
|-------|---------|-------------|
| **Phase 1** | `models/`, `core/` | Foundation - data structures and constants |
| **Phase 2** | `services/storage.py` | File persistence (can test without LD) |
| **Phase 3** | `services/payload_builder.py` | Core transformation logic |
| **Phase 4** | `services/validation.py` | Basic validation (structure only) |
| **Phase 5** | `ui/setup_tab.py`, `ui/matrix_tab.py` | UI for manual mode |
| **Phase 6** | `services/ld_client.py` | LaunchDarkly API integration |
| **Phase 7** | `services/deployer.py` | Deployment execution |
| **Phase 8** | `ui/deploy_tab.py` | Complete deployment UI |
| **Phase 9** | `app.py` | Wire everything together |
| **Phase 10** | Testing & Polish | End-to-end testing, error handling |

### Final Project Structure

```
rbac-builder/
├── app.py                          # Main entry point
├── requirements.txt                # Python dependencies
├── README.md                       # Usage documentation
│
├── models/                         # Data models
│   ├── __init__.py
│   ├── project.py
│   ├── environment.py
│   ├── team.py
│   ├── permissions.py
│   ├── config.py
│   └── payload.py
│
├── core/                           # Constants and mappings
│   ├── __init__.py
│   ├── constants.py
│   └── permission_mapping.py
│
├── services/                       # Business logic
│   ├── __init__.py
│   ├── ld_client.py               # LaunchDarkly API client
│   ├── storage.py                 # Config persistence
│   ├── payload_builder.py         # Matrix → JSON transformation
│   ├── validation.py              # Config validation
│   └── deployer.py                # Deployment execution
│
├── ui/                            # Streamlit UI
│   ├── __init__.py
│   ├── setup_tab.py              # Stage 1: Setup
│   ├── matrix_tab.py             # Stage 2: Matrix
│   ├── deploy_tab.py             # Stage 3: Deploy
│   └── components/               # Reusable UI components
│       ├── __init__.py
│       ├── data_table.py
│       └── status_badge.py
│
├── configs/                       # Saved configurations
│   └── customers/
│       └── .gitkeep
│
├── templates/                     # Starter templates
│   ├── standard-4-env.json
│   └── minimal-2-env.json
│
└── tests/                         # Unit tests
    ├── __init__.py
    ├── test_models.py
    ├── test_payload_builder.py
    ├── test_validation.py
    └── test_storage.py
```

---

## Payload Generation: Matrix to LaunchDarkly API

This section explains how the UI matrix data transforms into LaunchDarkly API payloads.

### Transformation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    TRANSFORMATION PIPELINE                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STEP 1                    STEP 2                    STEP 3                    │
│  UI Matrix Data            Role Definitions          API Payloads              │
│                                                                                 │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐        │
│  │                 │      │                 │      │                 │        │
│  │  Checkboxes     │─────▶│  Permission     │─────▶│  LaunchDarkly   │        │
│  │  (True/False)   │      │  to Actions     │      │  API JSON       │        │
│  │                 │      │  Mapping        │      │                 │        │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Permission to Action Mapping

#### Project-Scoped Permissions

| UI Permission | LaunchDarkly Actions | Resource Pattern |
|---------------|---------------------|------------------|
| **Create Flags** | `createFlag`, `cloneFlag` | `proj/{project}:env/*:flag/*` |
| **Update Flags** | `updateName`, `updateDescription`, `updateTags`, `updateDeprecated`, `updateMaintainer`, `updateTemporary`, `createFlagLink`, `deleteFlagLink`, `updateFlagLink`, `manageFlagFollowers`, `updateFlagCustomProperties`, `updateFlagDefaultVariations` | `proj/{project}:env/*:flag/*` |
| **Archive Flags** | `updateGlobalArchived` | `proj/{project}:env/*:flag/*` |
| **Manage Metrics** | `createMetric`, `updateMetric`, `deleteMetric` | `proj/{project}:metric/*` |
| **Manage Release Pipelines** | `addReleasePipeline`, `removeReleasePipeline`, `updateReleasePhaseCompleted`, `replaceReleasePipeline` | `proj/{project}:env/*:flag/*` |
| **Update Client-Side Availability** | `updateClientSideFlagAvailability` | `proj/{project}:env/*:flag/*` |
| **View Project** | `viewProject` | `proj/{project}` |

#### Environment-Scoped Permissions

| UI Permission | LaunchDarkly Actions | Resource Pattern |
|---------------|---------------------|------------------|
| **Update Targeting** | `updateOn`, `updateRules`, `updateTargets`, `updateFallthrough`, `updateOffVariation`, `updatePrerequisites`, `updateScheduledChanges`, `copyFlagConfigFrom`, `copyFlagConfigTo`, `createApprovalRequest`, `updateExpiringTargets`, `updateFeatureWorkflows` | `proj/{project}:env/{env}:flag/*` |
| **Review Changes** | `reviewApprovalRequest`, `updateApprovalRequest` | `proj/{project}:env/{env}:flag/*` |
| **Apply Changes** | `applyApprovalRequest` | `proj/{project}:env/{env}:flag/*` |
| **Manage Segments** | `createSegment`, `updateSegment`, `deleteSegment`, `updateIncluded`, `updateExcluded`, `updateRules` | `proj/{project}:env/{env}:segment/*` |
| **View SDK Key** | `viewSdkKey` | `proj/{project}:env/{env}` |
| **Manage Experiments** | `createExperiment`, `updateExperiment`, `deleteExperiment` | `proj/{project}:env/{env}:experiment/*` |

### Complete JSON Payload Structure

The RBAC bundle that gets generated:

```json
{
  "metadata": {
    "customer": "Epassi",
    "generated_at": "2024-03-11T15:30:00Z",
    "version": "1.0",
    "mode": "connected"
  },

  "config": {
    "projects": ["default", "mobile-app"],
    "environments": [
      {"key": "development", "critical": false},
      {"key": "test", "critical": false},
      {"key": "staging", "critical": true},
      {"key": "production", "critical": true}
    ]
  },

  "custom_roles": [
    {
      "key": "project-create-flags",
      "name": "Project: Create Flags",
      "description": "Allows creating new feature flags",
      "basePermissions": "no_access",
      "policy": [
        {
          "effect": "allow",
          "actions": ["createFlag", "cloneFlag"],
          "resources": ["proj/*:env/*:flag/*"]
        },
        {
          "effect": "allow",
          "actions": ["viewProject"],
          "resources": ["proj/*"]
        }
      ]
    },
    {
      "key": "project-update-flags",
      "name": "Project: Update Flags",
      "description": "Allows updating feature flag metadata",
      "basePermissions": "no_access",
      "policy": [
        {
          "effect": "allow",
          "actions": [
            "updateName",
            "updateDescription",
            "updateTags",
            "updateDeprecated",
            "updateMaintainer",
            "updateTemporary",
            "createFlagLink",
            "deleteFlagLink",
            "updateFlagLink",
            "manageFlagFollowers",
            "updateFlagCustomProperties",
            "updateFlagDefaultVariations"
          ],
          "resources": ["proj/*:env/*:flag/*"]
        },
        {
          "effect": "allow",
          "actions": ["viewProject"],
          "resources": ["proj/*"]
        }
      ]
    },
    {
      "key": "env-development-update-targeting",
      "name": "Development: Update Targeting",
      "description": "Allows updating flag targeting in Development environment",
      "basePermissions": "no_access",
      "policy": [
        {
          "effect": "allow",
          "actions": [
            "updateOn",
            "updateRules",
            "updateTargets",
            "updateFallthrough",
            "updateOffVariation",
            "updatePrerequisites",
            "updateScheduledChanges",
            "copyFlagConfigFrom",
            "copyFlagConfigTo",
            "createApprovalRequest",
            "updateExpiringTargets"
          ],
          "resources": ["proj/*:env/development:flag/*"]
        },
        {
          "effect": "allow",
          "actions": ["viewProject"],
          "resources": ["proj/*"]
        }
      ]
    },
    {
      "key": "env-development-apply-changes",
      "name": "Development: Apply Changes",
      "description": "Allows applying approved changes in Development environment",
      "basePermissions": "no_access",
      "policy": [
        {
          "effect": "allow",
          "actions": ["applyApprovalRequest"],
          "resources": ["proj/*:env/development:flag/*"]
        },
        {
          "effect": "allow",
          "actions": ["viewProject"],
          "resources": ["proj/*"]
        }
      ]
    }
  ],

  "teams": [
    {
      "key": "dev",
      "name": "Developer",
      "description": "Development team",
      "customRoleKeys": [
        "project-create-flags",
        "project-update-flags",
        "env-development-update-targeting",
        "env-development-apply-changes",
        "env-development-review-changes",
        "env-development-manage-segments",
        "env-test-update-targeting",
        "env-test-review-changes",
        "env-test-manage-segments"
      ]
    },
    {
      "key": "qa",
      "name": "QA Engineer",
      "description": "Quality assurance team",
      "customRoleKeys": [
        "env-test-update-targeting",
        "env-test-apply-changes",
        "env-test-review-changes",
        "env-test-manage-segments",
        "env-staging-update-targeting",
        "env-staging-apply-changes",
        "env-staging-review-changes",
        "env-staging-manage-segments"
      ]
    },
    {
      "key": "admin",
      "name": "Administrator",
      "description": "Full access administrators",
      "customRoleKeys": [
        "project-create-flags",
        "project-update-flags",
        "project-archive-flags",
        "env-development-update-targeting",
        "env-development-apply-changes",
        "env-production-update-targeting",
        "env-production-apply-changes"
      ]
    }
  ],

  "deployment_sequence": [
    {
      "step": 1,
      "action": "create_roles",
      "description": "Create all custom roles"
    },
    {
      "step": 2,
      "action": "create_teams",
      "description": "Create teams that don't exist"
    },
    {
      "step": 3,
      "action": "update_teams",
      "description": "Update existing teams with role assignments"
    }
  ]
}
```

### Role Generation Algorithm

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      ROLE GENERATION ALGORITHM                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  INPUT: Matrix checkboxes from UI                                              │
│                                                                                 │
│  FOR each unique permission type in matrix:                                    │
│                                                                                 │
│    1. PROJECT-SCOPED PERMISSIONS                                               │
│       ─────────────────────────────                                            │
│       IF any team has "Create Flags" checked:                                  │
│         → Generate role: "project-create-flags"                                │
│         → Actions: ["createFlag", "cloneFlag"]                                 │
│         → Resource: "proj/*:env/*:flag/*"                                      │
│                                                                                 │
│    2. ENVIRONMENT-SCOPED PERMISSIONS                                           │
│       ────────────────────────────────                                          │
│       FOR each environment (dev, test, staging, prod):                         │
│                                                                                 │
│         IF any team has "Update Targeting" for this env:                       │
│           → Generate role: "env-{env}-update-targeting"                        │
│           → Actions: [updateOn, updateRules, ...]                              │
│           → Resource: "proj/*:env/{env}:flag/*"                                │
│                                                                                 │
│  OUTPUT: List of unique custom roles                                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Team Assignment Logic

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      TEAM ROLE ASSIGNMENT                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  FOR each team in matrix:                                                      │
│                                                                                 │
│    team_roles = []                                                             │
│                                                                                 │
│    # Collect project-scoped roles                                              │
│    IF team.permissions.project.create_flags == true:                           │
│      team_roles.append("project-create-flags")                                 │
│                                                                                 │
│    # Collect environment-scoped roles                                          │
│    FOR each environment:                                                       │
│      IF team.permissions.env[environment].update_targeting == true:            │
│        team_roles.append(f"env-{environment}-update-targeting")                │
│                                                                                 │
│    # Generate team definition                                                  │
│    team_definition = {                                                         │
│      "key": team.key,                                                          │
│      "name": team.name,                                                        │
│      "customRoleKeys": team_roles                                              │
│    }                                                                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Payload Builder (Python Reference)

```python
class PayloadBuilder:
    """Transforms UI matrix into LaunchDarkly API payloads"""

    # Permission to Actions mapping
    PERMISSION_ACTIONS = {
        # Project-scoped
        "create_flags": {
            "actions": ["createFlag", "cloneFlag"],
            "resource_template": "proj/*:env/*:flag/*"
        },
        "update_flags": {
            "actions": [
                "updateName", "updateDescription", "updateTags",
                "updateDeprecated", "updateMaintainer", "updateTemporary",
                "createFlagLink", "deleteFlagLink", "updateFlagLink",
                "manageFlagFollowers", "updateFlagCustomProperties",
                "updateFlagDefaultVariations"
            ],
            "resource_template": "proj/*:env/*:flag/*"
        },
        "archive_flags": {
            "actions": ["updateGlobalArchived"],
            "resource_template": "proj/*:env/*:flag/*"
        },

        # Environment-scoped
        "update_targeting": {
            "actions": [
                "updateOn", "updateRules", "updateTargets",
                "updateFallthrough", "updateOffVariation",
                "updatePrerequisites", "updateScheduledChanges",
                "copyFlagConfigFrom", "copyFlagConfigTo",
                "createApprovalRequest", "updateExpiringTargets"
            ],
            "resource_template": "proj/*:env/{env}:flag/*"
        },
        "apply_changes": {
            "actions": ["applyApprovalRequest"],
            "resource_template": "proj/*:env/{env}:flag/*"
        },
        "review_changes": {
            "actions": ["reviewApprovalRequest", "updateApprovalRequest"],
            "resource_template": "proj/*:env/{env}:flag/*"
        },
        "manage_segments": {
            "actions": [
                "createSegment", "deleteSegment",
                "updateName", "updateDescription", "updateTags",
                "updateIncluded", "updateExcluded", "updateRules"
            ],
            "resource_template": "proj/*:env/{env}:segment/*"
        },
        "view_sdk_key": {
            "actions": ["viewSdkKey"],
            "resource_template": "proj/*:env/{env}"
        }
    }

    def build_rbac_bundle(self, config: RBACConfig) -> dict:
        """Build complete RBAC bundle from config"""

        # Step 1: Generate unique roles needed
        roles = self._generate_roles(config)

        # Step 2: Generate team definitions with role assignments
        teams = self._generate_teams(config, roles)

        # Step 3: Build deployment sequence
        sequence = self._build_deployment_sequence(roles, teams)

        return {
            "metadata": {
                "customer": config.customer_name,
                "generated_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            },
            "custom_roles": roles,
            "teams": teams,
            "deployment_sequence": sequence
        }

    def _generate_roles(self, config: RBACConfig) -> list:
        """Generate unique custom roles from permissions matrix"""
        roles = []
        roles_needed = set()

        # Scan matrix to find which roles are needed
        for team_key, team_perms in config.permissions.items():
            # Check project permissions
            for perm, enabled in team_perms.project.__dict__.items():
                if enabled:
                    roles_needed.add(("project", perm, None))

            # Check environment permissions
            for env_key, env_perms in team_perms.environments.items():
                for perm, enabled in env_perms.__dict__.items():
                    if enabled:
                        roles_needed.add(("environment", perm, env_key))

        # Generate role definitions
        for scope, perm, env_key in roles_needed:
            role = self._create_role_definition(scope, perm, env_key)
            roles.append(role)

        return roles

    def _create_role_definition(self, scope, permission, env_key=None):
        """Create a single role definition"""
        perm_config = self.PERMISSION_ACTIONS[permission]

        if scope == "project":
            role_key = f"project-{permission.replace('_', '-')}"
            role_name = f"Project: {permission.replace('_', ' ').title()}"
            resource = perm_config["resource_template"]
        else:
            role_key = f"env-{env_key}-{permission.replace('_', '-')}"
            role_name = f"{env_key.title()}: {permission.replace('_', ' ').title()}"
            resource = perm_config["resource_template"].replace("{env}", env_key)

        return {
            "key": role_key,
            "name": role_name,
            "description": f"Auto-generated role for {permission}",
            "basePermissions": "no_access",
            "policy": [
                {
                    "effect": "allow",
                    "actions": perm_config["actions"],
                    "resources": [resource]
                },
                {
                    "effect": "allow",
                    "actions": ["viewProject"],
                    "resources": ["proj/*"]
                }
            ]
        }

    def _generate_teams(self, config: RBACConfig, roles: list) -> list:
        """Generate team definitions with role assignments"""
        teams = []
        role_keys = {r["key"] for r in roles}

        for team in config.teams:
            team_perms = config.permissions[team.key]
            assigned_roles = []

            # Assign project roles
            for perm, enabled in team_perms.project.__dict__.items():
                if enabled:
                    role_key = f"project-{perm.replace('_', '-')}"
                    if role_key in role_keys:
                        assigned_roles.append(role_key)

            # Assign environment roles
            for env_key, env_perms in team_perms.environments.items():
                for perm, enabled in env_perms.__dict__.items():
                    if enabled:
                        role_key = f"env-{env_key}-{perm.replace('_', '-')}"
                        if role_key in role_keys:
                            assigned_roles.append(role_key)

            teams.append({
                "key": team.key,
                "name": team.name,
                "description": team.description,
                "customRoleKeys": assigned_roles
            })

        return teams
```

### API Deployment Sequence

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     API DEPLOYMENT SEQUENCE                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STEP 1: CREATE CUSTOM ROLES                                                   │
│  ════════════════════════════                                                   │
│                                                                                 │
│  FOR each role in custom_roles:                                                │
│    POST /api/v2/roles                                                          │
│    {                                                                            │
│      "key": "project-create-flags",                                            │
│      "name": "Project: Create Flags",                                          │
│      "basePermissions": "no_access",                                           │
│      "policy": [...]                                                           │
│    }                                                                            │
│                                                                                 │
│    Response: 201 Created (or 409 if exists → PATCH instead)                   │
│                                                                                 │
│                                                                                 │
│  STEP 2: CREATE/UPDATE TEAMS                                                   │
│  ════════════════════════════                                                   │
│                                                                                 │
│  FOR each team in teams:                                                       │
│                                                                                 │
│    # Check if team exists                                                      │
│    GET /api/v2/teams/{team.key}                                                │
│                                                                                 │
│    IF 404 (not found):                                                         │
│      POST /api/v2/teams                                                        │
│      {                                                                          │
│        "key": "dev",                                                           │
│        "name": "Developer",                                                    │
│        "customRoleKeys": ["project-create-flags", ...]                         │
│      }                                                                          │
│                                                                                 │
│    ELSE (team exists):                                                         │
│      PATCH /api/v2/teams/{team.key}                                            │
│      {                                                                          │
│        "customRoleKeys": ["project-create-flags", ...]                         │
│      }                                                                          │
│                                                                                 │
│                                                                                 │
│  STEP 3: VERIFICATION                                                          │
│  ═════════════════════                                                          │
│                                                                                 │
│  FOR each team in teams:                                                       │
│    GET /api/v2/teams/{team.key}                                                │
│    Verify customRoleKeys matches expected                                      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### End-to-End Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         END-TO-END FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  UI MATRIX                     JSON PAYLOAD                  LAUNCHDARKLY      │
│  ─────────                     ────────────                  ────────────      │
│                                                                                 │
│  ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐│
│  │ Dev: ✓ Create   │          │ custom_roles:   │          │ Custom Role:    ││
│  │      ✓ Update   │   ───►   │   - project-    │   ───►   │ project-create- ││
│  │      ✓ Dev Targ │          │     create-flags│          │ flags           ││
│  │                 │          │   - env-dev-    │          │                 ││
│  │ QA:  ✓ Test App │          │     targeting   │          │ Team: dev       ││
│  │      ✓ Stg App  │          │                 │          │ roles: [...]    ││
│  │                 │          │ teams:          │          │                 ││
│  │ Admin: ✓ ALL    │          │   - dev: [...]  │          │ Team: qa        ││
│  │                 │          │   - qa: [...]   │          │ roles: [...]    ││
│  └─────────────────┘          └─────────────────┘          └─────────────────┘│
│                                                                                 │
│        │                              │                              │         │
│        ▼                              ▼                              ▼         │
│   User clicks              PayloadBuilder            API calls execute         │
│   checkboxes               transforms data           in sequence               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Current UI Implementation (app.py)

This section documents the actual implementation of the Streamlit UI.

### Tab Structure

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🔧 RBAC Builder for LaunchDarkly                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  [📋 1. Setup]  [📊 2. Design Matrix]  [🚀 3. Deploy]  [📚 4. Reference Guide] │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

| Tab | Purpose | Key Components |
|-----|---------|----------------|
| **1. Setup** | Configure project, environments, teams | Project key input, Environment Groups table, Teams table |
| **2. Design Matrix** | Build permission matrices | Per-Project permissions, Per-Environment permissions |
| **3. Deploy** | Review and deploy | Summary metrics, JSON preview, Deploy button |
| **4. Reference Guide** | RBAC concepts reference | Expandable sections with terminology, diagrams |

### Session State Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    SESSION STATE DATA FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  TAB 1: SETUP                          TAB 2: DESIGN MATRIX                    │
│  ────────────                          ─────────────────────                    │
│                                                                                 │
│  ┌─────────────────┐                   ┌─────────────────────────────────────┐ │
│  │ Environment     │                   │ Per-Project Permissions             │ │
│  │ Groups Editor   │──────┐            │                                     │ │
│  │                 │      │            │ Team dropdown populated from        │ │
│  │ Key: "dev"      │      │            │ st.session_state.teams              │ │
│  │ Key: "prod"     │      │            └─────────────────────────────────────┘ │
│  └────────┬────────┘      │                                                    │
│           │               │            ┌─────────────────────────────────────┐ │
│           ▼               │            │ Per-Environment Permissions         │ │
│  st.session_state.        │            │                                     │ │
│  env_groups ──────────────┼───────────►│ Environment dropdown populated from │ │
│                           │            │ st.session_state.env_groups         │ │
│  ┌─────────────────┐      │            │                                     │ │
│  │ Teams Editor    │      │            │ Team dropdown populated from        │ │
│  │                 │      │            │ st.session_state.teams              │ │
│  │ Key: "dev"      │      │            └─────────────────────────────────────┘ │
│  │ Name: Developer │      │                                                    │
│  └────────┬────────┘      │                                                    │
│           │               │                                                    │
│           ▼               │                                                    │
│  st.session_state.        │                                                    │
│  teams ───────────────────┘                                                    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Session State Variables

| Variable | Type | Description | Set In | Used In |
|----------|------|-------------|--------|---------|
| `env_groups` | DataFrame | Environment group definitions | Tab 1 | Tab 2, Tab 3 |
| `teams` | DataFrame | Team definitions | Tab 1 | Tab 2, Tab 3 |
| `project_matrix` | DataFrame | Per-project permissions | Tab 2 | Tab 3 |
| `env_matrix` | DataFrame | Per-environment permissions | Tab 2 | Tab 3 |
| `visit_count` | int | Page load counter | Footer | Footer |

### Environment Groups Table

```
┌──────────────────────────────────────────────────────────────────┐
│  Environment Groups                                               │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────┬───────────────────┬──────────┬─────────────────┐│
│  │ Key         │ Requires Approvals│ Critical │ Notes           ││
│  ├─────────────┼───────────────────┼──────────┼─────────────────┤│
│  │ dev         │ ☐                 │ ☐        │ Dev, Test, Stg  ││
│  │ production  │ ☑                 │ ☑        │ Production      ││
│  └─────────────┴───────────────────┴──────────┴─────────────────┘│
│                                                                   │
│  🌍 2 environment group(s) defined                               │
└──────────────────────────────────────────────────────────────────┘
```

**Key Design Decision:** Instead of individual environments, we use **environment groups** (e.g., "dev", "production") which map to LaunchDarkly's resource specifiers with tags.

### Per-Project Permissions Matrix

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│  🏗️ Per-Project Permissions                                                              │
│  These permissions impact ALL environments in the project                                 │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┬────────┬────────┬─────────┬────────┬─────────┬──────┬──────┬──────┬──────┐│
│  │ Team       │ Create │ Update │ Archive │ Client │ Metrics │ Pipe │ View │Create│Update││
│  │            │ Flags  │ Flags  │ Flags   │ Side   │         │ lines│ Proj │AI Cfg│AI Cfg││
│  ├────────────┼────────┼────────┼─────────┼────────┼─────────┼──────┼──────┼──────┼──────┤│
│  │ Developer  │ ☑      │ ☑      │ ☐       │ ☐      │ ☑       │ ☐    │ ☑    │ ☑    │ ☑    ││
│  │ QA Engineer│ ☐      │ ☐      │ ☐       │ ☐      │ ☐       │ ☐    │ ☑    │ ☐    │ ☐    ││
│  │ Admin      │ ☑      │ ☑      │ ☑       │ ☑      │ ☑       │ ☑    │ ☑    │ ☑    │ ☑    ││
│  └────────────┴────────┴────────┴─────────┴────────┴─────────┴──────┴──────┴──────┴──────┘│
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

**AI Config Permissions (Added Dec 2024):**
- Create AI Configs, Update AI Configs, Delete AI Configs - Project-level actions for LLM management

### Per-Environment Permissions Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  🌍 Per-Environment Permissions                                                         │
│  Environment groups from Setup: dev, production                                         │
│  [🔄 Regenerate Matrix from Setup]                                                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┬─────────────┬──────────┬────────┬───────┬──────┬───────┬────┬─────────┐│
│  │ Team       │ Environment │ Update   │ Review │ Apply │ Seg- │ Exper │ SDK│ AI Cfg  ││
│  │            │             │ Targeting│ Changes│ Change│ ments│ iments│ Key│ Target  ││
│  ├────────────┼─────────────┼──────────┼────────┼───────┼──────┼───────┼────┼─────────┤│
│  │ Developer  │ dev         │ ☑        │ ☑      │ ☐     │ ☐    │ ☑     │ ☑  │ ☑       ││
│  │ Developer  │ production  │ ☐        │ ☑      │ ☐     │ ☐    │ ☐     │ ☐  │ ☐       ││
│  │ QA Engineer│ dev         │ ☑        │ ☑      │ ☑     │ ☑    │ ☑     │ ☑  │ ☑       ││
│  │ QA Engineer│ production  │ ☐        │ ☑      │ ☐     │ ☐    │ ☐     │ ☐  │ ☐       ││
│  │ Admin      │ dev         │ ☑        │ ☑      │ ☑     │ ☑    │ ☑     │ ☑  │ ☑       ││
│  │ Admin      │ production  │ ☑        │ ☑      │ ☑     │ ☑    │ ☑     │ ☑  │ ☑       ││
│  └────────────┴─────────────┴──────────┴────────┴───────┴──────┴───────┴────┴─────────┘│
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

**AI Config Targeting (Added Jun 2025):**
- Update AI Config Targeting - Environment-level action to control LLM targeting rules per environment

**Dynamic Features:**
- **Environment dropdown**: Options populated from `st.session_state.env_groups["Key"]`
- **Team dropdown**: Options populated from `st.session_state.teams["Name"]`
- **Regenerate button**: Rebuilds matrix when teams/environments change in Setup

### Reference Guide Tab

The Reference Guide tab provides in-app documentation with expandable sections:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  📚 LaunchDarkly RBAC Reference Guide                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ▼ 🔗 How It All Connects (Visual Overview)     [EXPANDED BY DEFAULT]       │
│    └── ASCII diagram showing Account → Members → Teams → Roles → Policies   │
│                                                                              │
│  ► 📖 Key Terms & Definitions                                                │
│    └── Table of RBAC terminology                                            │
│                                                                              │
│  ► 👥 Members & Teams                                                        │
│    └── Explanation of members, teams, permission aggregation                │
│                                                                              │
│  ► 🏷️ Built-in Roles                                                        │
│    └── Reader, Writer, Admin, Owner descriptions                            │
│                                                                              │
│  ► 📜 Policies (JSON Structure)                                             │
│    └── Policy syntax and evaluation rules                                   │
│                                                                              │
│  ► 🎯 Resources & Resource Syntax                                           │
│    └── Resource types, hierarchical syntax, wildcards                       │
│                                                                              │
│  ► ⚡ Actions Reference                                                      │
│    └── Project-level and Environment-level actions tables                   │
│                                                                              │
│  ► 🔐 Permission Scopes (Project vs Environment)                            │
│    └── Comparison with visual diagram                                       │
│                                                                              │
│  ► 🔗 Official LaunchDarkly Documentation                                   │
│    └── Links to official docs                                               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Educational Comments (Lessons)

The codebase includes numbered lessons to help learn Streamlit and Python:

| Lesson | Topic | Location |
|--------|-------|----------|
| LESSON 1 | Basic Text Output | Title, markdown |
| LESSON 2 | Sidebar | Settings panel |
| LESSON 3 | Tabs | Tab navigation |
| LESSON 4 | Session State | Data persistence |
| LESSON 5 | Environment Groups | Grouped environments concept |
| LESSON 6 | Teams / Functional Roles | Team definitions |
| LESSON 7 | Permission Matrix Design | Two-matrix approach |
| LESSON 8 | Reference Documentation | In-app help |
| LESSON 9 | Cross-Tab Data Sharing | Session state for tabs |
| LESSON 10 | Storing Edited Data | Session state updates |
| LESSON 11 | Dynamic Data | Building matrices from state |

---

## Export Package Feature

### Overview

In addition to direct deployment via API, the RBAC Builder supports generating a **self-contained deployment package** that can be delivered to clients. This allows clients to review and deploy using their own API keys.

### Two Deployment Options

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT OPTIONS                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Option A: DIRECT DEPLOY              Option B: EXPORT PACKAGE      │
│  ─────────────────────                ──────────────────────        │
│  • SA has API key                     • Client runs it themselves   │
│  • Deploy from UI                     • Download as ZIP             │
│  • Immediate execution                • Client uses their API key   │
│                                                                     │
│  ┌─────────┐                          ┌─────────────────────────┐   │
│  │ Deploy  │                          │  📦 deployment-package/ │   │
│  │ Button  │                          │  ├── docs/              │   │
│  └─────────┘                          │  ├── payloads/          │   │
│      │                                │  ├── scripts/           │   │
│      ▼                                │  └── README.md          │   │
│  LaunchDarkly                         └─────────────────────────┘   │
│                                                   │                 │
│                                                   ▼                 │
│                                       Client runs with their key    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Export Package Structure

```
{customer}-rbac-deployment/
│
├── 📖 docs/                              # COMPREHENSIVE DOCUMENTATION
│   ├── RBAC-OVERVIEW.md                  # Executive summary
│   ├── TEAMS-AND-ROLES.md                # Detailed team/role breakdown
│   ├── PERMISSIONS-MATRIX.md             # Visual permission matrix
│   └── ENVIRONMENT-STRATEGY.md           # Environment access strategy
│
├── README.md                             # Quick start guide for client
│
├── config/
│   └── rbac-config.json                  # Full configuration (human-readable)
│
├── payloads/                             # API-ready JSON files (in sequence)
│   ├── 01-custom-roles/
│   │   ├── dev-team-production.json
│   │   ├── dev-team-staging.json
│   │   └── ...
│   │
│   └── 02-teams/
│       ├── dev-team.json
│       └── ...
│
├── scripts/
│   ├── deploy.py                         # Python script (recommended)
│   ├── deploy.sh                         # Bash alternative
│   └── rollback.py                       # Undo deployment
│
└── manifest.json                         # Deployment order & metadata
```

### Documentation Files

The export package includes comprehensive documentation explaining the entire RBAC setup:

| Document | Purpose | Audience |
|----------|---------|----------|
| `RBAC-OVERVIEW.md` | Executive summary, quick stats, glossary | Everyone |
| `TEAMS-AND-ROLES.md` | Detailed breakdown of each team's permissions | Team leads, managers |
| `PERMISSIONS-MATRIX.md` | Visual permission grid with legend | Everyone |
| `ENVIRONMENT-STRATEGY.md` | Why environments are configured this way | Architects, security |

### Documentation Content

#### RBAC-OVERVIEW.md
- Executive summary of what's being configured
- Resource counts (teams, roles, environments)
- Access philosophy explanation
- Quick stats for each team
- Glossary of RBAC terms

#### TEAMS-AND-ROLES.md
- For each team:
  - Team key, purpose, typical members
  - Permissions by environment (table format)
  - Rationale for each permission decision
- Role naming convention explanation

#### PERMISSIONS-MATRIX.md
- Visual ASCII matrix of all permissions
- Project-level permissions grid
- Environment-level permissions grid (per environment)
- Legend and color coding explanation
- Summary diagram with access levels (🟢 Full, 🟡 Limited, 🔴 View Only)

#### ENVIRONMENT-STRATEGY.md
- Three-environment model explanation
- Cost of mistakes by environment
- Real-world scenario examples
- Approval workflow diagram
- Best practices implemented (least privilege, separation of duties)
- Customization notes

### Manifest File

The `manifest.json` file defines the deployment order and metadata:

```json
{
  "version": "1.0",
  "customer": "Acme Corporation",
  "project": "acme-project",
  "generated": "2024-03-13T10:30:00Z",
  "generated_by": "RBAC Builder v1.0",
  "deployment_order": [
    {
      "step": 1,
      "type": "custom-roles",
      "description": "Create custom roles with permissions",
      "endpoint": "POST /api/v2/roles",
      "files": [
        "payloads/01-custom-roles/dev-team-production.json",
        "payloads/01-custom-roles/dev-team-staging.json"
      ]
    },
    {
      "step": 2,
      "type": "teams",
      "description": "Create teams and assign roles",
      "endpoint": "POST /api/v2/teams",
      "files": [
        "payloads/02-teams/dev-team.json"
      ]
    }
  ]
}
```

### Payload File Format

Each payload file includes metadata for clarity:

```json
{
  "_meta": {
    "description": "Dev Team permissions for Production environment",
    "api_endpoint": "POST /api/v2/roles",
    "created_by": "RBAC Builder v1.0",
    "team": "dev-team",
    "environment": "production"
  },
  "payload": {
    "key": "dev-team-production",
    "name": "Dev Team - Production",
    "description": "Auto-generated role for Dev Team in Production",
    "policy": [
      {
        "effect": "allow",
        "actions": ["viewProject"],
        "resources": ["proj/acme-project:env/production"]
      }
    ]
  }
}
```

### Deployment Scripts

#### deploy.py (Python)
```python
#!/usr/bin/env python3
"""
RBAC Deployment Script
Generated by RBAC Builder

Usage:
    python deploy.py --api-key YOUR_API_KEY [--dry-run]
"""
# Reads manifest.json
# Iterates through deployment_order
# Makes API calls in sequence
# Reports success/failure for each resource
```

#### deploy.sh (Bash)
```bash
#!/bin/bash
# Alternative for environments without Python
# Uses curl for API calls
# Reads from manifest.json using jq
```

#### rollback.py
```python
#!/usr/bin/env python3
"""
Rollback Script - Removes created resources

Usage:
    python rollback.py --api-key YOUR_API_KEY [--dry-run]
"""
# Deletes resources in reverse order
# Teams first (removes role assignments)
# Then custom roles
```

### UI in Deploy Tab

```
┌─────────────────────────────────────────────────────────┐
│  Deploy Tab                                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Deployment Mode:                                       │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │ ○ Direct Deploy │  │ ● Export Package │              │
│  └─────────────────┘  └─────────────────┘              │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Export Options:                                        │
│  ☑ Include comprehensive documentation                 │
│  ☑ Include Python deployment script                    │
│  ☑ Include Bash deployment script                      │
│  ☑ Include rollback script                             │
│  ☐ Include Terraform format (future)                   │
│                                                         │
│  ┌──────────────────────────────────────┐              │
│  │  📦 Download Deployment Package      │              │
│  └──────────────────────────────────────┘              │
│                                                         │
│  Package Preview:                                       │
│  ├── docs/ (4 files)                                   │
│  ├── payloads/ (12 files)                              │
│  ├── scripts/ (3 files)                                │
│  ├── manifest.json                                     │
│  └── README.md                                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Implementation Phases

| Phase | Component | Description |
|-------|-----------|-------------|
| Phase 3 | `PayloadBuilder` | Generate API-ready JSON payloads |
| Phase 3 | `DocumentationGenerator` | Generate docs from RBACConfig |
| Phase 7 | `ExportBuilder` | Package everything into ZIP |
| Phase 8 | Deploy UI | Add export mode toggle and options |

### DocumentationGenerator Class

```python
class DocumentationGenerator:
    """Generates human-readable documentation from RBACConfig."""

    def __init__(self, config: RBACConfig):
        self.config = config

    def generate_overview(self) -> str:
        """Generate RBAC-OVERVIEW.md content."""
        # Uses config.customer_name, counts teams/roles/envs

    def generate_teams_doc(self) -> str:
        """Generate TEAMS-AND-ROLES.md with actual permissions."""
        # Iterates through teams and their permissions

    def generate_matrix(self) -> str:
        """Generate visual permission matrix from actual data."""
        # Builds ASCII tables from permission data

    def generate_env_strategy(self) -> str:
        """Generate environment strategy doc."""
        # Uses environment groups and their settings

    def generate_all(self) -> dict[str, str]:
        """Generate all documentation files."""
        return {
            "docs/RBAC-OVERVIEW.md": self.generate_overview(),
            "docs/TEAMS-AND-ROLES.md": self.generate_teams_doc(),
            "docs/PERMISSIONS-MATRIX.md": self.generate_matrix(),
            "docs/ENVIRONMENT-STRATEGY.md": self.generate_env_strategy(),
        }
```

### Benefits of Export Package

| Benefit | Description |
|---------|-------------|
| **Security** | Clients don't share API keys with SAs |
| **Audit Trail** | Clients have exact files that will be deployed |
| **Review Process** | Clients can review before running |
| **Offline Work** | SAs can build configs without client API access |
| **Documentation** | Clients understand what's being deployed |
| **Repeatability** | Same package can be deployed to multiple environments |

---

## Terraform Export Format

### Overview

For clients using Infrastructure as Code (IaC), the RBAC Builder can generate Terraform HCL files using the official **LaunchDarkly Terraform Provider**. This enables GitOps workflows and enterprise-grade deployment practices.

### Terraform Package Structure

```
{customer}-rbac-terraform/
│
├── 📖 docs/                              # Same documentation as regular export
│   ├── RBAC-OVERVIEW.md
│   ├── TEAMS-AND-ROLES.md
│   ├── PERMISSIONS-MATRIX.md
│   └── ENVIRONMENT-STRATEGY.md
│
├── README.md                             # Terraform-specific instructions
│
├── terraform/
│   ├── main.tf                           # Provider configuration
│   ├── variables.tf                      # Input variables (API key, project)
│   ├── outputs.tf                        # Output values (created resource IDs)
│   ├── versions.tf                       # Terraform & provider versions
│   │
│   ├── roles.tf                          # All custom role definitions
│   ├── teams.tf                          # All team definitions
│   │
│   └── terraform.tfvars.example          # Example variable values
│
└── manifest.json                         # Metadata (same as regular export)
```

### Terraform Files

#### versions.tf - Provider Requirements

```hcl
terraform {
  required_version = ">= 1.0.0"

  required_providers {
    launchdarkly = {
      source  = "launchdarkly/launchdarkly"
      version = "~> 2.0"
    }
  }
}
```

#### variables.tf - Input Variables

```hcl
# =============================================================================
# VARIABLES
# =============================================================================
# These values are provided by the client during deployment

variable "launchdarkly_access_token" {
  description = "LaunchDarkly API access token with admin permissions"
  type        = string
  sensitive   = true
}

variable "project_key" {
  description = "LaunchDarkly project key"
  type        = string
  default     = "acme-project"
}
```

#### main.tf - Provider Configuration

```hcl
# =============================================================================
# PROVIDER CONFIGURATION
# =============================================================================
# Generated by RBAC Builder for: Acme Corporation
# Generated on: 2024-03-13

provider "launchdarkly" {
  access_token = var.launchdarkly_access_token
}
```

#### roles.tf - Custom Role Definitions

```hcl
# =============================================================================
# CUSTOM ROLES
# =============================================================================
# These roles define permission sets for each team/environment combination

# -----------------------------------------------------------------------------
# Dev Team - Production (View Only)
# -----------------------------------------------------------------------------
resource "launchdarkly_custom_role" "dev_team_production" {
  key         = "dev-team-production"
  name        = "Dev Team - Production"
  description = "Dev Team permissions for Production environment - View Only"

  # Project-level: View only
  policy_statements {
    effect    = "allow"
    actions   = ["viewProject"]
    resources = ["proj/${var.project_key}"]
  }

  # Environment-level: View only (no toggle, no changes)
  policy_statements {
    effect    = "allow"
    actions   = ["viewProject"]
    resources = ["proj/${var.project_key}:env/production"]
  }
}

# -----------------------------------------------------------------------------
# Dev Team - Staging (Limited Access)
# -----------------------------------------------------------------------------
resource "launchdarkly_custom_role" "dev_team_staging" {
  key         = "dev-team-staging"
  name        = "Dev Team - Staging"
  description = "Dev Team permissions for Staging environment - Limited Access"

  policy_statements {
    effect = "allow"
    actions = [
      "viewProject",
      "updateOn",           # Toggle flags
      "updateFlagVariations",
      "updateTargets",
    ]
    resources = ["proj/${var.project_key}:env/staging"]
  }
}

# -----------------------------------------------------------------------------
# Dev Team - Development (Full Access)
# -----------------------------------------------------------------------------
resource "launchdarkly_custom_role" "dev_team_development" {
  key         = "dev-team-development"
  name        = "Dev Team - Development"
  description = "Dev Team permissions for Development environment - Full Access"

  policy_statements {
    effect    = "allow"
    actions   = ["*"]  # Full access in dev
    resources = ["proj/${var.project_key}:env/development"]
  }
}

# -----------------------------------------------------------------------------
# QA Team - Production (Toggle Only)
# -----------------------------------------------------------------------------
resource "launchdarkly_custom_role" "qa_team_production" {
  key         = "qa-team-production"
  name        = "QA Team - Production"
  description = "QA Team permissions for Production - Can toggle flags"

  policy_statements {
    effect = "allow"
    actions = [
      "viewProject",
      "updateOn",  # Toggle only
    ]
    resources = ["proj/${var.project_key}:env/production"]
  }
}

# ... additional roles for each team/environment combination
```

#### teams.tf - Team Definitions

```hcl
# =============================================================================
# TEAMS
# =============================================================================
# Teams are assigned custom roles based on the permission matrix

# -----------------------------------------------------------------------------
# Dev Team
# -----------------------------------------------------------------------------
resource "launchdarkly_team" "dev_team" {
  key         = "dev-team"
  name        = "Dev Team"
  description = "Frontend and backend developers"

  # Assign all roles for this team
  custom_role_keys = [
    launchdarkly_custom_role.dev_team_production.key,
    launchdarkly_custom_role.dev_team_staging.key,
    launchdarkly_custom_role.dev_team_development.key,
  ]
}

# -----------------------------------------------------------------------------
# QA Team
# -----------------------------------------------------------------------------
resource "launchdarkly_team" "qa_team" {
  key         = "qa-team"
  name        = "QA Team"
  description = "Quality assurance engineers"

  custom_role_keys = [
    launchdarkly_custom_role.qa_team_production.key,
    launchdarkly_custom_role.qa_team_staging.key,
    launchdarkly_custom_role.qa_team_development.key,
  ]
}

# -----------------------------------------------------------------------------
# Release Managers
# -----------------------------------------------------------------------------
resource "launchdarkly_team" "release_managers" {
  key         = "release-managers"
  name        = "Release Managers"
  description = "Control production releases"

  custom_role_keys = [
    launchdarkly_custom_role.release_managers_production.key,
    launchdarkly_custom_role.release_managers_staging.key,
    launchdarkly_custom_role.release_managers_development.key,
  ]
}
```

#### outputs.tf - Output Values

```hcl
# =============================================================================
# OUTPUTS
# =============================================================================
# Useful information after deployment

output "created_roles" {
  description = "List of created custom role keys"
  value = [
    launchdarkly_custom_role.dev_team_production.key,
    launchdarkly_custom_role.dev_team_staging.key,
    launchdarkly_custom_role.dev_team_development.key,
    launchdarkly_custom_role.qa_team_production.key,
    # ... all roles
  ]
}

output "created_teams" {
  description = "List of created team keys"
  value = [
    launchdarkly_team.dev_team.key,
    launchdarkly_team.qa_team.key,
    launchdarkly_team.release_managers.key,
  ]
}

output "summary" {
  description = "Deployment summary"
  value = {
    customer     = "Acme Corporation"
    project      = var.project_key
    roles_count  = 9
    teams_count  = 3
  }
}
```

#### terraform.tfvars.example

```hcl
# =============================================================================
# EXAMPLE VARIABLES
# =============================================================================
# Copy this file to terraform.tfvars and fill in your values
# NEVER commit terraform.tfvars to version control!

launchdarkly_access_token = "api-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
project_key               = "acme-project"
```

### Terraform README.md

```markdown
# RBAC Deployment - Acme Corporation (Terraform)

## Prerequisites

1. [Terraform](https://www.terraform.io/downloads) >= 1.0.0
2. LaunchDarkly API key with Admin permissions

## Quick Start

# Navigate to terraform directory
cd terraform/

# 1. Copy example variables
cp terraform.tfvars.example terraform.tfvars

# 2. Edit terraform.tfvars with your API key
vim terraform.tfvars

# 3. Initialize Terraform
terraform init

# 4. Preview changes (see what will be created)
terraform plan

# 5. Apply changes (create resources)
terraform apply

## Rollback

To remove all created resources:
terraform destroy

## State Management

For production use, configure remote state (S3, Azure Blob, GCS, etc.)
```

### TerraformGenerator Class

```python
class TerraformGenerator:
    """Generates Terraform HCL files from RBACConfig."""

    def __init__(self, config: RBACConfig):
        self.config = config

    def generate_versions(self) -> str:
        """Generate versions.tf content."""
        # Terraform and provider version requirements

    def generate_variables(self) -> str:
        """Generate variables.tf content."""
        # API key, project key variables

    def generate_main(self) -> str:
        """Generate main.tf content."""
        # Provider configuration

    def generate_roles(self) -> str:
        """Generate roles.tf with all custom role resources."""
        # Iterate through permissions, create launchdarkly_custom_role resources

    def generate_teams(self) -> str:
        """Generate teams.tf with all team resources."""
        # Iterate through teams, create launchdarkly_team resources

    def generate_outputs(self) -> str:
        """Generate outputs.tf content."""
        # Output created resource keys

    def generate_tfvars_example(self) -> str:
        """Generate terraform.tfvars.example."""
        # Example variable values

    def generate_all(self) -> dict[str, str]:
        """Generate all Terraform files."""
        return {
            "terraform/versions.tf": self.generate_versions(),
            "terraform/variables.tf": self.generate_variables(),
            "terraform/main.tf": self.generate_main(),
            "terraform/roles.tf": self.generate_roles(),
            "terraform/teams.tf": self.generate_teams(),
            "terraform/outputs.tf": self.generate_outputs(),
            "terraform/terraform.tfvars.example": self.generate_tfvars_example(),
        }
```

### Comparison: Scripts vs Terraform

| Aspect | Python/Bash Scripts | Terraform |
|--------|---------------------|-----------|
| **Learning Curve** | Lower | Higher |
| **State Tracking** | Manual | Automatic |
| **Idempotent** | Must implement | Built-in |
| **Rollback** | Separate script | `terraform destroy` |
| **Drift Detection** | No | Yes (`terraform plan`) |
| **Version Control** | Basic | GitOps ready |
| **CI/CD Integration** | Custom scripts | Native support |
| **Enterprise Ready** | Basic | Production-grade |

### Benefits of Terraform Export

| Benefit | Description |
|---------|-------------|
| **GitOps** | Store RBAC config in version control |
| **State Management** | Terraform tracks what exists vs what's defined |
| **Plan Before Apply** | See exactly what will change before applying |
| **Rollback** | `terraform destroy` removes everything cleanly |
| **Drift Detection** | `terraform plan` shows if someone changed things manually |
| **Modules** | Can be imported into larger Terraform configurations |
| **CI/CD Integration** | Run via GitHub Actions, GitLab CI, etc. |
| **Compliance** | Audit trail of all infrastructure changes |

### Updated UI with Terraform Option

```
┌─────────────────────────────────────────────────────────┐
│  Deploy Tab                                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Deployment Mode:                                       │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │ ○ Direct Deploy │  │ ● Export Package │              │
│  └─────────────────┘  └─────────────────┘              │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Export Format:                                         │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ ● Scripts        │  │ ○ Terraform      │            │
│  │   (Python/Bash)  │  │   (HCL)          │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                         │
│  Export Options:                                        │
│  ☑ Include comprehensive documentation                 │
│  ☑ Include deployment scripts                          │
│  ☑ Include rollback capability                         │
│                                                         │
│  ┌──────────────────────────────────────┐              │
│  │  📦 Download Deployment Package      │              │
│  └──────────────────────────────────────┘              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Implementation Phases (Updated)

| Phase | Component | Description |
|-------|-----------|-------------|
| Phase 3 | `PayloadBuilder` | Generate API-ready JSON payloads |
| Phase 3 | `DocumentationGenerator` | Generate docs from RBACConfig |
| Phase 3 | `TerraformGenerator` | Generate Terraform HCL files |
| Phase 7 | `ExportBuilder` | Package everything into ZIP |
| Phase 8 | Deploy UI | Add export mode, format toggle, and options |

---

## Future Enhancements

1. **Multi-user Support** - Centralized deployment with user authentication
2. **Import from Excel** - Migrate existing XLS configurations
3. **Audit Trail** - Track who made what changes when
4. **Templates Library** - Pre-built RBAC patterns for common use cases
5. **Diff View** - Show what changed between deployments
6. **Rollback** - Revert to previous configuration
7. **Pulumi Export** - Alternative IaC format for TypeScript/Python users
