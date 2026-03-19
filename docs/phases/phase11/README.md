# Phase 11: Role Attribute Pattern

| Field | Value |
|-------|-------|
| **Phase** | 11 |
| **Status** | ✅ Complete |
| **Goal** | Generate template roles with `${roleAttribute/...}` placeholders and teams with `roleAttributes` — the core architectural pattern of the entire rbac-builder |
| **Depends on** | Phase 3 (Payload Builder), Phase 5 (UI Modules) |

---

## Why This Phase Matters

This is the **most important architectural decision in the entire project**.

Instead of creating separate roles for every team × environment combination, the role attribute pattern creates:
1. **ONE shared role template per permission** — with `${roleAttribute/...}` placeholders
2. **Teams that fill in the placeholders** — with `roleAttributes` blocks containing exact env/project values

This is the pattern used in `ps-terraform-private-customer-sa-demo` (the SA delivery standard) and validated against real customer accounts.

---

## Documents

### Canonical Reference (complete pattern, sa-demo aligned)

| Document | Description |
|----------|-------------|
| [ROLE_ATTRIBUTE_HLD.md](./ROLE_ATTRIBUTE_HLD.md) | Why the pattern, architecture diagram, data flow, design decisions |
| [ROLE_ATTRIBUTE_DLD.md](./ROLE_ATTRIBUTE_DLD.md) | Role structure, team structure, resource string construction, full example |
| [ROLE_ATTRIBUTE_PSEUDOLOGIC_AND_TESTS.md](./ROLE_ATTRIBUTE_PSEUDOLOGIC_AND_TESTS.md) | Pseudo logic + 15 test cases (role gen, team assignment, policy evaluation) |

### Implementation Reference

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | Original implementation design (Phase 11 initial) |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Python concepts: f-string escaping, dict lookup, Builder pattern |
| [PROJECT_PREFIXED_TEAMS.md](./PROJECT_PREFIXED_TEAMS.md) | Project isolation via prefixed team keys |
| [TERRAFORM_PATTERNS.md](./TERRAFORM_PATTERNS.md) | All patterns from ps-terraform-private |

> **Corrections made in Phase 12:** Kebab-case attribute keys, context kind statements, `base_permissions` field. See [Phase 12](../phase12/) for detail.

---

## Pattern in One Sentence

> One shared role template per permission + teams that fill in `${roleAttribute/projects}` and `${roleAttribute/<perm>-environments}` with exact values.

## Key Files

| File | Role |
|------|------|
| `core/ld_actions.py` | `PERMISSION_ATTRIBUTE_MAP`, `build_env_role_attribute_resource()` |
| `services/payload_builder.py` | `RoleAttributePayloadBuilder` class |
| `tests/test_role_attributes.py` | 33 tests covering the pattern |
| `tests/test_critical_environments.py` | 20 tests covering env scoping (post-Phase 12) |

---

## Checklist

- [x] ROLE_ATTRIBUTE_HLD.md complete
- [x] ROLE_ATTRIBUTE_DLD.md complete
- [x] ROLE_ATTRIBUTE_PSEUDOLOGIC_AND_TESTS.md complete
- [x] DESIGN.md complete
- [x] PYTHON_CONCEPTS.md complete
- [x] Implementation complete (`RoleAttributePayloadBuilder`)
- [x] 33 tests passing (`test_role_attributes.py`)
- [x] Pattern validated against sa-demo (`ps-terraform-private-customer-sa-demo`)
