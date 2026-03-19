# Phase 7: Deployer Service

## Quick Overview

| Attribute | Value |
|-----------|-------|
| **Phase** | 7 of 10 |
| **Status** | 📋 Planned |
| **Goal** | Execute deployment of custom roles and teams to LaunchDarkly |
| **Dependencies** | Phase 3 (Payload Builder), Phase 6 (LD Client Interface) |
| **Dependents** | Phase 8 (Deploy UI) |

## What We're Building

A deployment service that:
- Takes an `LDPayload` (from Phase 3)
- Creates custom roles via LD API
- Creates teams with role assignments
- Tracks deployment progress
- Handles errors and rollback

## Files to Create

```
services/
├── deployer.py           # Main deployer service (NEW)
└── __init__.py           # Update exports
```

## Checklist

### Documentation
- [ ] README.md (this file)
- [ ] DESIGN.md (HLD, DLD, pseudo logic)
- [ ] PYTHON_CONCEPTS.md (deployment concepts)

### Implementation
- [ ] Create `DeployResult` dataclass
- [ ] Create `DeployStep` enum/dataclass
- [ ] Create `Deployer` class
- [ ] Implement `deploy_roles()` method
- [ ] Implement `deploy_teams()` method
- [ ] Implement `deploy_all()` orchestrator
- [ ] Add progress callback support
- [ ] Add dry-run mode
- [ ] Add rollback capability

### Testing
- [ ] Create `tests/test_deployer.py`
- [ ] Test deploy roles (success)
- [ ] Test deploy teams (success)
- [ ] Test conflict handling (skip existing)
- [ ] Test error handling
- [ ] Test dry-run mode
- [ ] Test progress callbacks
- [ ] Test rollback on failure

## Quick Start

```python
from services import Deployer, MockLDClient
from services import build_payload_from_session

# Build payload from UI session state
payload = build_payload_from_session(
    customer_name="Acme Corp",
    project_key="mobile-app",
    session_state=st.session_state
)

# Create deployer with client (mock for testing, real for production)
client = MockLDClient()  # or LDClient(api_key="...")
deployer = Deployer(client)

# Deploy everything
result = deployer.deploy_all(payload)

# Check results
print(f"Created {result.roles_created} roles")
print(f"Created {result.teams_created} teams")
print(f"Skipped {result.roles_skipped} existing roles")

if result.errors:
    for error in result.errors:
        print(f"Error: {error}")
```

## Related Documents

| Document | Description |
|----------|-------------|
| [DESIGN.md](DESIGN.md) | HLD, DLD, pseudo logic |
| [PYTHON_CONCEPTS.md](PYTHON_CONCEPTS.md) | Callbacks, state machines |
| [Phase 6](../phase6/) | LD Client (provides API access) |
| [Phase 3](../phase3/) | Payload Builder (provides payload) |

---
[← Phase 6](../phase6/) | [Phase 8 →](../phase8/)
