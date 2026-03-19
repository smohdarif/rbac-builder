# RBAC Builder - Implementation Phases

> **This folder contains design documents for each implementation phase.**

---

## Phase Overview

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| **1** | [Data Models](./phase1/) | ✅ Complete | Python dataclasses for RBAC configuration |
| **2** | [Storage](./phase2/) | ✅ Complete | Save/load configs to JSON files |
| **3** | [Payload Builder](./phase3/) | ✅ Complete | Convert matrix → LaunchDarkly JSON |
| **4** | [Validation](./phase4/) | ✅ Complete | Validate configs before deployment |
| **5** | [UI Modules](./phase5/) | ✅ Complete | Split app.py into separate tab modules |
| **6** | [LD Client](./phase6/) | ✅ Complete | LaunchDarkly API integration |
| **7** | [Deployer](./phase7/) | ✅ Complete | Execute deployment to LaunchDarkly |
| **8** | [Deploy UI](./phase8/) | ✅ Complete | Complete deployment UI |
| **9** | Integration | ✅ Complete | Wire everything together |
| **10** | Testing | ✅ Complete | Testing and polish |
| **11** | [Role Attribute Pattern](./phase11/) | ✅ Complete | **Core pattern**: shared template roles + `${roleAttribute/...}` placeholders + team scoping |
| **12** | [Role Attribute Corrections](./phase12/) | ✅ Complete | Kebab-case attr keys, context kind statements, `base_permissions` fix |
| **13** | [Client Delivery Package](./phase13/) | ✅ Complete | ZIP with API-ready JSON + Python deploy script |
| **14** | [Observability Permissions](./phase14/) | ✅ Complete | Sessions, Logs, Errors, Traces, Alerts, Dashboards, Vega AI |
| **15** | [UI Grouping & Tab Layout](./phase15/) | ✅ Complete | Tab-based matrix grouped by feature domain (Flags, AI, Observability, etc.) |

---

## Upcoming Phases

| Phase | Name | Priority | Goal |
|-------|------|----------|------|
| **16** | [Terraform Export](./phase16/) | 🔴 High | Generate `.tf` files matching ps-terraform-private patterns |
| **17** | [Global / Account-Level Roles](./phase17/) | 🔴 High | `view_teams`, `manage_personal_access_tokens` — in every sa-demo team |
| **18** | [LD Views Support](./phase18/) | 🔴 High | RBAC for LaunchDarkly saved flag filter Views |
| **19** | [Manage Context Kinds](./phase19/) | 🔴 High | Missing Default=1 permission from S2 template |
| **20** | [Deny Lists](./phase20/) | 🟡 Medium | Explicit exclusions for environments/flags/projects |
| **21** | [Visible Teams](./phase21/) | 🟡 Medium | `visibleTeams` role attribute — in every sa-demo config |
| **22** | [Project Admin Roles](./phase22/) | 🟡 Medium | Destructive admin actions (delete project, rotate SDK keys) |
| **23** | [Environment Tag Specifiers](./phase23/) | 🟢 Lower | `env/*;tag1,tag2` tag-based environment filtering |
| **24** | [Flag / Segment Specifiers](./phase24/) | 🟢 Lower | `flags=["feature-*"]`, deny patterns |
| **25** | [Team Management Global Roles](./phase25/) | 🟢 Lower | `manage_members`, `manage_teams`, `manage_integrations` |

> Full details, rationale, and design notes: **[ROADMAP.md](../ROADMAP.md)**

---

## Status Legend

| Icon | Meaning |
|------|---------|
| ✅ | Complete |
| 🔄 | In Progress |
| 📋 | Planning (docs ready) |
| ⏳ | Pending |

---

## Phase Dependencies

```
Phase 1: Data Models
    │
    ▼
Phase 2: Storage ──────────────────────┐
    │                                   │
    ▼                                   │
Phase 3: Payload Builder               │
    │                                   │
    ▼                                   │
Phase 4: Validation                    │
    │                                   │
    ├───────────────────────────────────┤
    │                                   │
    ▼                                   ▼
Phase 5: UI Modules              Phase 6: LD Client
    │                                   │
    │                                   ▼
    │                            Phase 7: Deployer
    │                                   │
    └───────────────┬───────────────────┘
                    │
                    ▼
              Phase 8: Deploy UI
                    │
                    ▼
              Phase 9: Integration
                    │
                    ▼
              Phase 10: Testing
```

---

## Quick Start

### Next Phase Ready for Implementation

**[Phase 3: Payload Builder](./phase3/)** 📋

Documents available:
- [README.md](./phase3/README.md) - Quick overview
- [DESIGN.md](./phase3/DESIGN.md) - HLD, DLD, pseudo logic
- [PYTHON_CONCEPTS.md](./phase3/PYTHON_CONCEPTS.md) - Enums, mappings, transformations

### Completed Phases

**[Phase 2: Storage](./phase2/)** ✅
- StorageService with save/load/delete operations
- Automatic backup on save with history management
- Template support with standard-4-env and minimal-2-env
- Custom exceptions for error handling

**[Phase 1: Data Models](./phase1/)** ✅
- All dataclasses implemented in `models/` folder
- Team, EnvironmentGroup, ProjectPermission, EnvironmentPermission, RBACConfig

---

## Document Structure

Each phase folder contains:

```
phase{N}/
├── README.md           # Quick overview and checklist
├── DESIGN.md           # HLD, DLD, pseudo logic, implementation plan
├── {TOPIC}_CONCEPTS.md # Deep dive into relevant concepts
└── (other docs)        # Phase-specific documentation
```

---

## Other Implemented Features (no separate phase)

| Feature | Where | Notes |
|---------|-------|-------|
| Markdown Deployment Guide | `services/doc_generator.py` | Part of Phase 8 Deploy UI enhancements |
| `📄 Download Deployment Guide` button | `ui/deploy_tab.py` | Alongside existing payload download |

---

## Navigation

[← Back to Main Docs](../) | [Roadmap](../ROADMAP.md) | [Backlog](../BACKLOG.md)
