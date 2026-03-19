# Phase 11: Role Attributes Support

## Overview

Add support for generating role attribute-based roles and teams, matching the enterprise pattern used in ps-terraform-private.

## Status: ✅ Complete

## Goals

1. Generate template roles with `${roleAttribute/...}` placeholders
2. Generate teams with `roleAttributes` that fill in the placeholders
3. Support multi-project deployments from a single configuration
4. Maintain backward compatibility with current hardcoded approach

## Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, implementation plan |
| [PROJECT_PREFIXED_TEAMS.md](./PROJECT_PREFIXED_TEAMS.md) | Project isolation via prefixed team keys |
| [TERRAFORM_PATTERNS.md](./TERRAFORM_PATTERNS.md) | All patterns from ps-terraform-private (TODO list) |
| [ROLE_ATTRIBUTES_EXPLAINED.md](../ROLE_ATTRIBUTES_EXPLAINED.md) | Concept explanation |

## Checklist

- [x] Design document complete
- [x] Test cases defined (33 tests in test_role_attributes.py)
- [x] Implementation complete
- [x] All tests passing (293 total tests)
- [x] Documentation updated

## Implementation Summary

### Files Modified

| File | Changes |
|------|---------|
| `core/ld_actions.py` | Added role attribute resource builders, permission-to-attribute mapping |
| `services/payload_builder.py` | Added `RoleAttributePayloadBuilder` class |
| `services/__init__.py` | Exported new builder and convenience function |
| `ui/setup_tab.py` | Added generation mode toggle and default projects input |
| `ui/deploy_tab.py` | Updated to handle both modes, mode-aware summary |
| `tests/test_role_attributes.py` | Comprehensive test suite (33 tests) |

### New Functions Added

```python
# core/ld_actions.py
build_role_attribute_resource(project_attr, resource_type) -> str
build_env_role_attribute_resource(project_attr, env_attr, resource_type) -> str
build_project_only_role_attribute_resource(project_attr) -> str
get_attribute_name(permission_name) -> str
is_project_level_permission(permission_name) -> bool
is_env_level_permission(permission_name) -> bool
get_resource_type_for_permission(permission_name) -> str

# services/payload_builder.py
class RoleAttributePayloadBuilder
build_role_attribute_payload_from_session(...)
slugify(text) -> str
```

## Dependencies

- Phase 3: Payload Builder (services/payload_builder.py)
- Phase 5: UI Modules (ui/matrix_tab.py, ui/deploy_tab.py)
