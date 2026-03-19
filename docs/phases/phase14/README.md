# Phase 14: Observability Permissions

| Field | Value |
|-------|-------|
| **Phase** | 14 |
| **Status** | ✅ Complete |
| **Goal** | Add LaunchDarkly Observability permissions (Sessions, Logs, Errors, Traces, Alerts, Dashboards, Vega) to the rbac-builder matrix |
| **Depends on** | Phase 11 (Role Attribute Pattern), Phase 12 (Env Scoping) |

---

## Background

A College Board SA engagement surfaced a gap: customers using LD Observability features cannot currently configure RBAC for them using rbac-builder. The permissions were validated against Gonfalon `internal/roles/action.go` and `resource_identifier.go`.

**Key finding from validation:** All observability resources are **project-scoped only** — no `env/*` in the path. This differs from flags/segments which are `proj/*:env/*:flag/*`.

---

## What This Phase Adds

### New Project-Level Permissions (7 total)

| UI Name | Actions | Resource Path |
|---------|---------|--------------|
| View Sessions | `viewSession` | `proj/${roleAttribute/projects}:session/*` |
| View Errors | `viewError`, `updateErrorStatus` | `proj/${roleAttribute/projects}:error/*` |
| View Logs | `viewLog` | `proj/${roleAttribute/projects}:log/*` |
| View Traces | `viewTrace` | `proj/${roleAttribute/projects}:trace/*` |
| Manage Alerts | `viewAlert`, `createAlert`, `deleteAlert`, `updateAlertOn`, `updateAlertConfiguration` | `proj/${roleAttribute/projects}:alert/*` |
| Manage Observability Dashboards | `viewObservabilityDashboard`, `createObservabilityDashboard`, `deleteObservabilityDashboard`, `addObservabilityGraphToDashboard`, `removeObservabilityGraphFromDashboard`, `updateObservabilityDashboardConfiguration`, `updateObservabilityGraphConfiguration`, `updateObservabilitySettings` | `proj/${roleAttribute/projects}:observability-dashboard/*` |
| Talk to Vega | `talkToVega` | `proj/${roleAttribute/projects}:vega/*` |

> **Source:** Verified against `gonfalon/internal/roles/action.go` and `gonfalon/internal/roles/resource_identifier.go`

### UI Placement

- **Default matrix** (show by default): `View Sessions`, `View Errors`, `View Logs`, `View Traces`
- **Optional expander**: `Manage Alerts`, `Manage Observability Dashboards`, `Talk to Vega`

---

## Key Technical Challenge

All existing project-level permissions use:
```
proj/${roleAttribute/projects}:env/*:flag/*
```

Observability resources don't have an `env` segment:
```
proj/${roleAttribute/projects}:session/*
```

A new resource builder function is required: `build_project_type_resource()`.

---

## Design Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Python concepts: sets as lookup tables, enum extension |
| [EXAMPLES.md](./EXAMPLES.md) | Real output JSON explained line by line — role object, team object, how they connect |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `core/ld_actions.py` | ADD `ObservabilityAction` enum, `OBSERVABILITY_RESOURCE_MAP`, `build_project_type_resource()`, update permission maps |
| `ui/matrix_tab.py` | ADD 4 default + 3 optional observability columns |
| `services/payload_builder.py` | UPDATE `_build_project_template_role()` to detect observability resources |
| `tests/test_observability_permissions.py` | CREATE — all test cases |

---

## Implementation Checklist

- [ ] `DESIGN.md` complete
- [ ] `PYTHON_CONCEPTS.md` complete
- [x] `core/ld_actions.py` updated
- [x] `ui/matrix_tab.py` updated
- [x] `services/payload_builder.py` updated
- [x] `tests/test_observability_permissions.py` created — 26 tests passing
- [x] All 371 tests passing
- [x] Output JSON verified: no `:env/` in observability resources

---

## Source of Truth

Actions verified against:
- `gonfalon/internal/roles/action.go` — action identifiers
- `gonfalon/internal/roles/resource_identifier.go` — `TraceResourceIdentifier`, `VegaResourceIdentifier` etc. all embed `ProjectResourceIdentifier` (not `EnvironmentResourceIdentifier`)
