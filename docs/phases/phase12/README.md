# Phase 12: Role Attribute Env Scoping + Role Correctness

| Field | Value |
|-------|-------|
| **Phase** | 12 |
| **Status** | ✅ Complete |
| **Goal** | Correct and harden the Phase 11 role attribute pattern: kebab-case attribute keys, context kind statements, `base_permissions` field |
| **Base** | Builds on [Phase 11 — Role Attribute Pattern](../phase11/) |

---

## What This Phase Actually Implemented

> ⚠️ **Note:** This phase was originally designed around `{critical:true}` environment wildcards.
> After analysis of the sa-demo and validation concerns, we switched to the **role attribute
> env scoping pattern**. The original design is preserved in `CRITICAL_ENVIRONMENTS_DESIGN.md`.

### Three changes shipped in this phase

### 1. Role Attribute Env Scoping (replaces {critical:true})

Each env role uses its own `${roleAttribute/<perm>-environments}` placeholder:

```
# Before (original plan — NOT implemented)
proj/${roleAttribute/projects}:env/*;{critical:true}:flag/*

# After (actual implementation)
proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*
```

Teams fill in exact env keys via `roleAttributes`:
```json
{ "key": "update-targeting-environments", "values": ["production", "staging"] }
```

**Attribute key convention:** kebab-case (`update-targeting-environments`) matching the sa-demo exactly.

### 2. Context Kind Statements in Flag Roles

Matching ps-terraform's default `create_context_kind = coalesce(null, !false) = true`:

| Role | Extra statement added |
|------|-----------------------|
| `create-flags` | `createContextKind` on `context-kind/*` |
| `update-flags` | `updateContextKind`, `updateAvailabilityForExperiments` on `context-kind/*` |

This matches what already exists in LD accounts created via ps-terraform.

### 3. `base_permissions: "no_access"` on All Roles

Every generated role now includes this required LD API field. Without it the API rejects the request or defaults to `reader` (unintended access).

---

## Files Changed

| File | Change |
|------|--------|
| `core/ld_actions.py` | `PERMISSION_ATTRIBUTE_MAP` keys → kebab-case |
| `core/ld_actions.py` | `CONTEXT_KIND_ACTIONS_FOR_PERMISSION` dict added |
| `core/ld_actions.py` | `build_context_kind_role_attribute_resource()` added |
| `services/payload_builder.py` | Removed `use_criticality` branching → always role attribute |
| `services/payload_builder.py` | Context kind policy statement added to project roles |
| `services/payload_builder.py` | `base_permissions: "no_access"` added to all roles |
| `tests/test_critical_environments.py` | Rewritten to test role attribute pattern |

---

## Design Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic for this phase |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Python concepts used in this phase |
| [CRITICAL_ENVIRONMENTS_DESIGN.md](./CRITICAL_ENVIRONMENTS_DESIGN.md) | Original design (preserved as reference, superseded) |
| [Role Attribute Pattern docs](../../role-attribute-pattern/) | Full HLD/DLD/tests for the env scoping pattern |

---

## Checklist

- [x] `PERMISSION_ATTRIBUTE_MAP` converted to kebab-case
- [x] `_uses_criticality_pattern()` branching removed — always role attribute
- [x] Per-permission env attributes always generated on teams
- [x] Context kind statements added to `create-flags` and `update-flags`
- [x] `base_permissions: "no_access"` on all roles
- [x] `test_critical_environments.py` rewritten — 20 tests passing
- [x] All 313 tests passing
