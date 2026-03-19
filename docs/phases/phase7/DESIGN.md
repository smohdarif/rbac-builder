# Phase 7: Deployer Service - Design Document

| Attribute | Value |
|-----------|-------|
| **Phase** | 7 of 10 |
| **Status** | 📋 Planned |
| **Goal** | Execute deployment of custom roles and teams to LaunchDarkly |
| **Dependencies** | Phase 3 (Payload Builder), Phase 6 (LD Client Interface) |
| **Estimated Lessons** | Callbacks, State Machines, Error Recovery, Dry-Run Pattern |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Quick overview and checklist |
| [PYTHON_CONCEPTS.md](PYTHON_CONCEPTS.md) | Deep dive into Python concepts |
| [Phase 6 DESIGN.md](../phase6/DESIGN.md) | LD Client interface used by Deployer |
| [Phase 3 DESIGN.md](../phase3/DESIGN.md) | Payload Builder that creates input |

---

## Table of Contents

1. [High-Level Design (HLD)](#high-level-design-hld)
2. [Detailed Low-Level Design (DLD)](#detailed-low-level-design-dld)
3. [Pseudo Logic](#pseudo-logic)
4. [Test Cases](#test-cases)
5. [Implementation Plan](#implementation-plan)

---

## High-Level Design (HLD)

### What Are We Building?

A deployment orchestrator that takes a generated payload and executes API calls to create resources in LaunchDarkly.

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  LDPayload   │    │   Deployer   │    │  LaunchDarkly    │  │
│  │  (Phase 3)   │───▶│  (Phase 7)   │───▶│  API (Phase 6)   │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│                      ┌──────────────┐                          │
│                      │ DeployResult │                          │
│                      │ • roles_created │                        │
│                      │ • teams_created │                        │
│                      │ • errors        │                        │
│                      └──────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why Separate Deployer from Client?

| Concern | Handled By |
|---------|------------|
| HTTP requests, auth, retries | LD Client (Phase 6) |
| Orchestration, ordering, error recovery | Deployer (Phase 7) |
| Payload structure, policy generation | Payload Builder (Phase 3) |

**Separation of Concerns:**
- Client handles "how to call API"
- Deployer handles "what to deploy and in what order"

### Deployment Order (Critical!)

Resources must be created in a specific order:

```
┌─────────────────────────────────────────────────────────────────┐
│                  DEPLOYMENT ORDER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STEP 1: Create Custom Roles                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • developer-test-env                                     │   │
│  │ • developer-production-env                               │   │
│  │ • qa-test-env                                            │   │
│  │ • qa-production-env                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼ Roles must exist before teams        │
│  STEP 2: Create Teams (with role assignments)                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • developers (roles: [developer-test, developer-prod])  │   │
│  │ • qa-engineers (roles: [qa-test, qa-prod])              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Core Features

| Feature | Description |
|---------|-------------|
| **Ordered Deployment** | Roles first, then teams |
| **Conflict Handling** | Skip existing resources (don't fail) |
| **Progress Tracking** | Callback for UI updates |
| **Dry-Run Mode** | Validate without making changes |
| **Error Collection** | Continue on error, report all at end |
| **Rollback Support** | Delete created resources on failure (optional) |

### Deployment Modes

| Mode | Behavior |
|------|----------|
| **Normal** | Create all resources, skip existing |
| **Dry-Run** | Validate only, no API calls |
| **Force** | Delete and recreate existing (dangerous) |
| **Rollback-On-Error** | Delete created resources if any step fails |

---

## Detailed Low-Level Design (DLD)

### File Structure

```
services/
├── __init__.py              # Export Deployer, DeployResult
└── deployer.py              # Deployer implementation
```

### Class Diagram

```
┌─────────────────────────────────────────┐
│            DeployStep (Enum)            │
├─────────────────────────────────────────┤
│ PENDING                                 │
│ IN_PROGRESS                             │
│ COMPLETED                               │
│ SKIPPED                                 │
│ FAILED                                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         DeployStepResult                │
├─────────────────────────────────────────┤
│ + resource_type: str                    │
│ + resource_key: str                     │
│ + status: DeployStep                    │
│ + message: str                          │
│ + error: Optional[str]                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│            DeployResult                 │
├─────────────────────────────────────────┤
│ + success: bool                         │
│ + roles_created: int                    │
│ + roles_skipped: int                    │
│ + roles_failed: int                     │
│ + teams_created: int                    │
│ + teams_skipped: int                    │
│ + teams_failed: int                     │
│ + steps: List[DeployStepResult]         │
│ + errors: List[str]                     │
│ + duration_seconds: float               │
├─────────────────────────────────────────┤
│ + get_summary() -> str                  │
│ + has_errors() -> bool                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│              Deployer                   │
├─────────────────────────────────────────┤
│ - client: LDClientInterface             │
│ - dry_run: bool                         │
│ - skip_existing: bool                   │
│ - progress_callback: Optional[Callable] │
│ - created_roles: List[str]              │
│ - created_teams: List[str]              │
├─────────────────────────────────────────┤
│ + deploy_all(payload) -> DeployResult   │
│ + deploy_roles(roles) -> DeployResult   │
│ + deploy_teams(teams) -> DeployResult   │
│ + rollback() -> bool                    │
│ - _deploy_role(role) -> DeployStepResult│
│ - _deploy_team(team) -> DeployStepResult│
│ - _notify_progress(step)                │
└─────────────────────────────────────────┘
```

### Data Classes

```python
# services/deployer.py

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Callable, Any
import time


class DeployStep(Enum):
    """Status of a deployment step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class DeployStepResult:
    """Result of a single deployment step."""
    resource_type: str  # "role" or "team"
    resource_key: str   # e.g., "developer-test-env"
    status: DeployStep
    message: str = ""
    error: Optional[str] = None

    def is_success(self) -> bool:
        return self.status in (DeployStep.COMPLETED, DeployStep.SKIPPED)


@dataclass
class DeployResult:
    """Overall deployment result."""
    success: bool = True
    roles_created: int = 0
    roles_skipped: int = 0
    roles_failed: int = 0
    teams_created: int = 0
    teams_skipped: int = 0
    teams_failed: int = 0
    steps: List[DeployStepResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def get_summary(self) -> str:
        lines = [
            f"Deployment {'succeeded' if self.success else 'failed'}",
            f"  Roles: {self.roles_created} created, {self.roles_skipped} skipped, {self.roles_failed} failed",
            f"  Teams: {self.teams_created} created, {self.teams_skipped} skipped, {self.teams_failed} failed",
            f"  Duration: {self.duration_seconds:.1f}s"
        ]
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        return "\n".join(lines)

    def add_step(self, step: DeployStepResult) -> None:
        """Add a step result and update counters."""
        self.steps.append(step)

        if step.resource_type == "role":
            if step.status == DeployStep.COMPLETED:
                self.roles_created += 1
            elif step.status == DeployStep.SKIPPED:
                self.roles_skipped += 1
            elif step.status == DeployStep.FAILED:
                self.roles_failed += 1
                self.success = False

        elif step.resource_type == "team":
            if step.status == DeployStep.COMPLETED:
                self.teams_created += 1
            elif step.status == DeployStep.SKIPPED:
                self.teams_skipped += 1
            elif step.status == DeployStep.FAILED:
                self.teams_failed += 1
                self.success = False

        if step.error:
            self.errors.append(f"{step.resource_type}/{step.resource_key}: {step.error}")
```

### Deployer Class Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `client` | `LDClientInterface` | API client (real or mock) |
| `dry_run` | `bool` | If True, validate only |
| `skip_existing` | `bool` | If True, skip conflicts |
| `progress_callback` | `Callable` | Called on each step |
| `created_roles` | `List[str]` | Keys of created roles (for rollback) |
| `created_teams` | `List[str]` | Keys of created teams (for rollback) |

### Deployer Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `client, dry_run, skip_existing, progress_callback` | `None` | Initialize deployer |
| `deploy_all` | `payload: LDPayload` | `DeployResult` | Deploy roles then teams |
| `deploy_roles` | `roles: List[Dict]` | `DeployResult` | Deploy only roles |
| `deploy_teams` | `teams: List[Dict]` | `DeployResult` | Deploy only teams |
| `rollback` | None | `bool` | Delete created resources |
| `_deploy_role` | `role: Dict` | `DeployStepResult` | Deploy single role |
| `_deploy_team` | `team: Dict` | `DeployStepResult` | Deploy single team |
| `_notify_progress` | `step: DeployStepResult` | `None` | Call progress callback |

### Progress Callback Interface

```python
# Callback signature
def progress_callback(
    step: DeployStepResult,
    current: int,
    total: int
) -> None:
    """
    Called after each deployment step.

    Args:
        step: Result of the current step
        current: Current step number (1-based)
        total: Total number of steps
    """
    pass


# Example usage in Streamlit
def update_progress(step, current, total):
    progress = current / total
    st.progress(progress)
    st.write(f"{step.resource_type}: {step.resource_key} - {step.status.value}")
```

---

## Pseudo Logic

### 1. Deployer Initialization

```
FUNCTION __init__(client, dry_run=False, skip_existing=True, progress_callback=None):
    1. VALIDATE client is not None
       IF client is None:
           RAISE ValueError("client is required")

    2. STORE configuration
       self.client = client
       self.dry_run = dry_run
       self.skip_existing = skip_existing
       self.progress_callback = progress_callback

    3. INITIALIZE tracking lists (for rollback)
       self.created_roles = []
       self.created_teams = []

    4. RETURN initialized deployer
```

### 2. Deploy All (Main Orchestrator)

```
FUNCTION deploy_all(payload: LDPayload) -> DeployResult:
    1. START timer
       start_time = time.time()

    2. INITIALIZE result
       result = DeployResult()

    3. CALCULATE total steps
       total_steps = len(payload.roles) + len(payload.teams)
       current_step = 0

    4. PHASE 1: Deploy all roles first
       FOR role IN payload.roles:
           current_step += 1

           step_result = _deploy_role(role)
           result.add_step(step_result)

           _notify_progress(step_result, current_step, total_steps)

           # Track created roles for potential rollback
           IF step_result.status == COMPLETED:
               self.created_roles.append(role["key"])

    5. PHASE 2: Deploy all teams (roles must exist first)
       FOR team IN payload.teams:
           current_step += 1

           step_result = _deploy_team(team)
           result.add_step(step_result)

           _notify_progress(step_result, current_step, total_steps)

           # Track created teams for potential rollback
           IF step_result.status == COMPLETED:
               self.created_teams.append(team["key"])

    6. CALCULATE duration
       result.duration_seconds = time.time() - start_time

    7. RETURN result
```

### 3. Deploy Single Role

```
FUNCTION _deploy_role(role: Dict) -> DeployStepResult:
    role_key = role["key"]
    role_name = role["name"]

    1. CHECK if dry-run mode
       IF self.dry_run:
           RETURN DeployStepResult(
               resource_type="role",
               resource_key=role_key,
               status=SKIPPED,
               message="Dry-run mode - not created"
           )

    2. TRY to create role
       TRY:
           self.client.create_custom_role(role)

           RETURN DeployStepResult(
               resource_type="role",
               resource_key=role_key,
               status=COMPLETED,
               message=f"Created role: {role_name}"
           )

       EXCEPT LDConflictError:
           # Role already exists
           IF self.skip_existing:
               RETURN DeployStepResult(
                   resource_type="role",
                   resource_key=role_key,
                   status=SKIPPED,
                   message=f"Role already exists: {role_name}"
               )
           ELSE:
               RETURN DeployStepResult(
                   resource_type="role",
                   resource_key=role_key,
                   status=FAILED,
                   error=f"Role already exists: {role_name}"
               )

       EXCEPT LDValidationError AS e:
           RETURN DeployStepResult(
               resource_type="role",
               resource_key=role_key,
               status=FAILED,
               error=f"Validation error: {e.message}"
           )

       EXCEPT LDClientError AS e:
           RETURN DeployStepResult(
               resource_type="role",
               resource_key=role_key,
               status=FAILED,
               error=str(e)
           )
```

### 4. Deploy Single Team

```
FUNCTION _deploy_team(team: Dict) -> DeployStepResult:
    team_key = team["key"]
    team_name = team["name"]

    1. CHECK if dry-run mode
       IF self.dry_run:
           RETURN DeployStepResult(
               resource_type="team",
               resource_key=team_key,
               status=SKIPPED,
               message="Dry-run mode - not created"
           )

    2. TRY to create team
       TRY:
           self.client.create_team(team)

           RETURN DeployStepResult(
               resource_type="team",
               resource_key=team_key,
               status=COMPLETED,
               message=f"Created team: {team_name}"
           )

       EXCEPT LDConflictError:
           # Team already exists - might need to update roles
           IF self.skip_existing:
               RETURN DeployStepResult(
                   resource_type="team",
                   resource_key=team_key,
                   status=SKIPPED,
                   message=f"Team already exists: {team_name}"
               )
           ELSE:
               RETURN DeployStepResult(
                   resource_type="team",
                   resource_key=team_key,
                   status=FAILED,
                   error=f"Team already exists: {team_name}"
               )

       EXCEPT LDValidationError AS e:
           # Check for "role not found" error
           IF "role" IN e.message.lower() AND "not found" IN e.message.lower():
               RETURN DeployStepResult(
                   resource_type="team",
                   resource_key=team_key,
                   status=FAILED,
                   error=f"Referenced role not found. Ensure roles are created first."
               )

           RETURN DeployStepResult(
               resource_type="team",
               resource_key=team_key,
               status=FAILED,
               error=f"Validation error: {e.message}"
           )

       EXCEPT LDClientError AS e:
           RETURN DeployStepResult(
               resource_type="team",
               resource_key=team_key,
               status=FAILED,
               error=str(e)
           )
```

### 5. Progress Notification

```
FUNCTION _notify_progress(step: DeployStepResult, current: int, total: int):
    1. CHECK if callback exists
       IF self.progress_callback is None:
           RETURN

    2. CALL callback safely
       TRY:
           self.progress_callback(step, current, total)
       EXCEPT Exception AS e:
           # Don't let callback errors stop deployment
           LOG warning: f"Progress callback error: {e}"
```

### 6. Rollback

```
FUNCTION rollback() -> bool:
    """Delete all resources created in this deployment session."""

    success = True

    1. ROLLBACK teams first (reverse order)
       FOR team_key IN reversed(self.created_teams):
           TRY:
               self.client.delete_team(team_key)
           EXCEPT LDClientError AS e:
               LOG error: f"Failed to delete team {team_key}: {e}"
               success = False

    2. ROLLBACK roles
       FOR role_key IN reversed(self.created_roles):
           TRY:
               self.client.delete_role(role_key)
           EXCEPT LDClientError AS e:
               LOG error: f"Failed to delete role {role_key}: {e}"
               success = False

    3. CLEAR tracking lists
       self.created_roles = []
       self.created_teams = []

    4. RETURN success
```

### 7. Deploy Roles Only

```
FUNCTION deploy_roles(roles: List[Dict]) -> DeployResult:
    """Deploy only roles (useful for partial deployment)."""

    start_time = time.time()
    result = DeployResult()
    total_steps = len(roles)

    FOR i, role IN enumerate(roles):
        step_result = _deploy_role(role)
        result.add_step(step_result)
        _notify_progress(step_result, i + 1, total_steps)

        IF step_result.status == COMPLETED:
            self.created_roles.append(role["key"])

    result.duration_seconds = time.time() - start_time
    RETURN result
```

### 8. Deploy Teams Only

```
FUNCTION deploy_teams(teams: List[Dict]) -> DeployResult:
    """Deploy only teams (assumes roles already exist)."""

    start_time = time.time()
    result = DeployResult()
    total_steps = len(teams)

    FOR i, team IN enumerate(teams):
        step_result = _deploy_team(team)
        result.add_step(step_result)
        _notify_progress(step_result, i + 1, total_steps)

        IF step_result.status == COMPLETED:
            self.created_teams.append(team["key"])

    result.duration_seconds = time.time() - start_time
    RETURN result
```

---

## Test Cases

### Test File: `tests/test_deployer.py`

```python
"""
Tests for Phase 7: Deployer Service
====================================

Tests cover:
1. DeployResult data class
2. Deployer initialization
3. Role deployment (success, conflict, error)
4. Team deployment (success, conflict, error)
5. Full deployment orchestration
6. Dry-run mode
7. Progress callbacks
8. Rollback functionality

Run with: pytest tests/test_deployer.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock
from dataclasses import asdict


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_client():
    """Create a mock LD client."""
    from services.ld_client_interface import LDClientInterface

    client = MagicMock(spec=LDClientInterface)
    return client


@pytest.fixture
def sample_roles():
    """Sample role payloads for testing."""
    return [
        {
            "key": "developer-test",
            "name": "Developer - Test",
            "description": "Developer access for test environments",
            "policy": [{"effect": "allow", "actions": ["*"], "resources": ["proj/*:env/test:*"]}]
        },
        {
            "key": "developer-prod",
            "name": "Developer - Prod",
            "description": "Developer access for production environments",
            "policy": [{"effect": "allow", "actions": ["viewProject"], "resources": ["proj/*:env/prod:*"]}]
        }
    ]


@pytest.fixture
def sample_teams():
    """Sample team payloads for testing."""
    return [
        {
            "key": "developers",
            "name": "Developers",
            "description": "Development team",
            "customRoleKeys": ["developer-test", "developer-prod"]
        }
    ]


@pytest.fixture
def sample_payload(sample_roles, sample_teams):
    """Create a sample LDPayload."""
    from services import LDPayload

    payload = LDPayload()
    payload.roles = sample_roles
    payload.teams = sample_teams
    return payload


@pytest.fixture
def deployer(mock_client):
    """Create a Deployer with mock client."""
    from services.deployer import Deployer

    return Deployer(client=mock_client)


# =============================================================================
# DeployResult Tests
# =============================================================================

class TestDeployResult:
    """Tests for DeployResult data class."""

    def test_default_values(self):
        """Test DeployResult default values."""
        from services.deployer import DeployResult

        result = DeployResult()

        assert result.success is True
        assert result.roles_created == 0
        assert result.roles_skipped == 0
        assert result.roles_failed == 0
        assert result.teams_created == 0
        assert result.errors == []

    def test_has_errors_false_when_empty(self):
        """Test has_errors returns False when no errors."""
        from services.deployer import DeployResult

        result = DeployResult()
        assert result.has_errors() is False

    def test_has_errors_true_when_errors_exist(self):
        """Test has_errors returns True when errors exist."""
        from services.deployer import DeployResult

        result = DeployResult()
        result.errors.append("Some error")

        assert result.has_errors() is True

    def test_add_step_updates_counters(self):
        """Test add_step updates the correct counters."""
        from services.deployer import DeployResult, DeployStepResult, DeployStep

        result = DeployResult()

        # Add completed role
        step1 = DeployStepResult(
            resource_type="role",
            resource_key="dev-role",
            status=DeployStep.COMPLETED
        )
        result.add_step(step1)
        assert result.roles_created == 1

        # Add skipped role
        step2 = DeployStepResult(
            resource_type="role",
            resource_key="existing-role",
            status=DeployStep.SKIPPED
        )
        result.add_step(step2)
        assert result.roles_skipped == 1

        # Add failed team
        step3 = DeployStepResult(
            resource_type="team",
            resource_key="bad-team",
            status=DeployStep.FAILED,
            error="Some error"
        )
        result.add_step(step3)
        assert result.teams_failed == 1
        assert result.success is False  # Should flip to False on failure

    def test_get_summary_includes_counts(self):
        """Test get_summary includes all counts."""
        from services.deployer import DeployResult

        result = DeployResult()
        result.roles_created = 3
        result.roles_skipped = 1
        result.teams_created = 2

        summary = result.get_summary()

        assert "3 created" in summary
        assert "1 skipped" in summary
        assert "2 created" in summary


# =============================================================================
# DeployStepResult Tests
# =============================================================================

class TestDeployStepResult:
    """Tests for DeployStepResult data class."""

    def test_is_success_for_completed(self):
        """Test is_success returns True for COMPLETED."""
        from services.deployer import DeployStepResult, DeployStep

        step = DeployStepResult(
            resource_type="role",
            resource_key="test",
            status=DeployStep.COMPLETED
        )
        assert step.is_success() is True

    def test_is_success_for_skipped(self):
        """Test is_success returns True for SKIPPED."""
        from services.deployer import DeployStepResult, DeployStep

        step = DeployStepResult(
            resource_type="role",
            resource_key="test",
            status=DeployStep.SKIPPED
        )
        assert step.is_success() is True

    def test_is_success_for_failed(self):
        """Test is_success returns False for FAILED."""
        from services.deployer import DeployStepResult, DeployStep

        step = DeployStepResult(
            resource_type="role",
            resource_key="test",
            status=DeployStep.FAILED
        )
        assert step.is_success() is False


# =============================================================================
# Deployer Initialization Tests
# =============================================================================

class TestDeployerInit:
    """Tests for Deployer initialization."""

    def test_init_with_client(self, mock_client):
        """Test deployer initializes with client."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client)

        assert deployer.client is mock_client
        assert deployer.dry_run is False
        assert deployer.skip_existing is True

    def test_init_with_dry_run(self, mock_client):
        """Test deployer initializes with dry_run mode."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client, dry_run=True)

        assert deployer.dry_run is True

    def test_init_with_progress_callback(self, mock_client):
        """Test deployer accepts progress callback."""
        from services.deployer import Deployer

        callback = Mock()
        deployer = Deployer(client=mock_client, progress_callback=callback)

        assert deployer.progress_callback is callback

    def test_init_without_client_raises_error(self):
        """Test deployer raises error without client."""
        from services.deployer import Deployer

        with pytest.raises(ValueError, match="client"):
            Deployer(client=None)


# =============================================================================
# Role Deployment Tests
# =============================================================================

class TestDeployRoles:
    """Tests for role deployment."""

    def test_deploy_role_success(self, deployer, mock_client, sample_roles):
        """Test successful role deployment."""
        from services.deployer import DeployStep

        mock_client.create_custom_role.return_value = {"key": "developer-test"}

        result = deployer.deploy_roles([sample_roles[0]])

        assert result.roles_created == 1
        assert result.roles_failed == 0
        mock_client.create_custom_role.assert_called_once()

    def test_deploy_role_conflict_skipped(self, deployer, mock_client, sample_roles):
        """Test role conflict is skipped when skip_existing=True."""
        from services.ld_exceptions import LDConflictError

        mock_client.create_custom_role.side_effect = LDConflictError("exists")

        result = deployer.deploy_roles([sample_roles[0]])

        assert result.roles_created == 0
        assert result.roles_skipped == 1
        assert result.success is True

    def test_deploy_role_conflict_fails_when_not_skipping(self, mock_client, sample_roles):
        """Test role conflict fails when skip_existing=False."""
        from services.deployer import Deployer
        from services.ld_exceptions import LDConflictError

        deployer = Deployer(client=mock_client, skip_existing=False)
        mock_client.create_custom_role.side_effect = LDConflictError("exists")

        result = deployer.deploy_roles([sample_roles[0]])

        assert result.roles_failed == 1
        assert result.success is False

    def test_deploy_role_validation_error(self, deployer, mock_client, sample_roles):
        """Test role validation error is handled."""
        from services.ld_exceptions import LDValidationError

        mock_client.create_custom_role.side_effect = LDValidationError("Invalid policy")

        result = deployer.deploy_roles([sample_roles[0]])

        assert result.roles_failed == 1
        assert "Invalid policy" in result.errors[0]

    def test_deploy_multiple_roles(self, deployer, mock_client, sample_roles):
        """Test deploying multiple roles."""
        mock_client.create_custom_role.return_value = {"key": "test"}

        result = deployer.deploy_roles(sample_roles)

        assert result.roles_created == 2
        assert mock_client.create_custom_role.call_count == 2


# =============================================================================
# Team Deployment Tests
# =============================================================================

class TestDeployTeams:
    """Tests for team deployment."""

    def test_deploy_team_success(self, deployer, mock_client, sample_teams):
        """Test successful team deployment."""
        mock_client.create_team.return_value = {"key": "developers"}

        result = deployer.deploy_teams(sample_teams)

        assert result.teams_created == 1
        mock_client.create_team.assert_called_once()

    def test_deploy_team_conflict_skipped(self, deployer, mock_client, sample_teams):
        """Test team conflict is skipped."""
        from services.ld_exceptions import LDConflictError

        mock_client.create_team.side_effect = LDConflictError("exists")

        result = deployer.deploy_teams(sample_teams)

        assert result.teams_skipped == 1
        assert result.success is True

    def test_deploy_team_role_not_found_error(self, deployer, mock_client, sample_teams):
        """Test team fails when role doesn't exist."""
        from services.ld_exceptions import LDValidationError

        mock_client.create_team.side_effect = LDValidationError(
            "Role 'developer-test' not found"
        )

        result = deployer.deploy_teams(sample_teams)

        assert result.teams_failed == 1
        assert "role" in result.errors[0].lower()


# =============================================================================
# Full Deployment Tests
# =============================================================================

class TestDeployAll:
    """Tests for full deployment orchestration."""

    def test_deploy_all_roles_before_teams(self, deployer, mock_client, sample_payload):
        """Test roles are deployed before teams."""
        call_order = []

        def track_role(*args, **kwargs):
            call_order.append("role")
            return {"key": "test"}

        def track_team(*args, **kwargs):
            call_order.append("team")
            return {"key": "test"}

        mock_client.create_custom_role.side_effect = track_role
        mock_client.create_team.side_effect = track_team

        deployer.deploy_all(sample_payload)

        # All roles should come before teams
        role_indices = [i for i, x in enumerate(call_order) if x == "role"]
        team_indices = [i for i, x in enumerate(call_order) if x == "team"]

        if role_indices and team_indices:
            assert max(role_indices) < min(team_indices)

    def test_deploy_all_returns_combined_result(self, deployer, mock_client, sample_payload):
        """Test deploy_all returns combined results."""
        mock_client.create_custom_role.return_value = {"key": "test"}
        mock_client.create_team.return_value = {"key": "test"}

        result = deployer.deploy_all(sample_payload)

        assert result.roles_created == 2  # Two roles in sample_payload
        assert result.teams_created == 1  # One team in sample_payload
        assert result.success is True

    def test_deploy_all_tracks_duration(self, deployer, mock_client, sample_payload):
        """Test deploy_all tracks duration."""
        mock_client.create_custom_role.return_value = {"key": "test"}
        mock_client.create_team.return_value = {"key": "test"}

        result = deployer.deploy_all(sample_payload)

        assert result.duration_seconds > 0


# =============================================================================
# Dry-Run Mode Tests
# =============================================================================

class TestDryRunMode:
    """Tests for dry-run mode."""

    def test_dry_run_does_not_call_api(self, mock_client, sample_payload):
        """Test dry-run mode doesn't make API calls."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client, dry_run=True)

        result = deployer.deploy_all(sample_payload)

        mock_client.create_custom_role.assert_not_called()
        mock_client.create_team.assert_not_called()

    def test_dry_run_marks_steps_as_skipped(self, mock_client, sample_payload):
        """Test dry-run mode marks all steps as skipped."""
        from services.deployer import Deployer, DeployStep

        deployer = Deployer(client=mock_client, dry_run=True)

        result = deployer.deploy_all(sample_payload)

        for step in result.steps:
            assert step.status == DeployStep.SKIPPED
            assert "dry-run" in step.message.lower()

    def test_dry_run_still_counts_steps(self, mock_client, sample_payload):
        """Test dry-run mode counts skipped steps."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client, dry_run=True)

        result = deployer.deploy_all(sample_payload)

        # All should be skipped
        assert result.roles_skipped == 2
        assert result.teams_skipped == 1
        assert result.roles_created == 0
        assert result.teams_created == 0


# =============================================================================
# Progress Callback Tests
# =============================================================================

class TestProgressCallback:
    """Tests for progress callback functionality."""

    def test_callback_called_for_each_step(self, mock_client, sample_payload):
        """Test callback is called for each deployment step."""
        from services.deployer import Deployer

        callback = Mock()
        deployer = Deployer(client=mock_client, progress_callback=callback)
        mock_client.create_custom_role.return_value = {"key": "test"}
        mock_client.create_team.return_value = {"key": "test"}

        deployer.deploy_all(sample_payload)

        # Should be called for each role + each team
        expected_calls = len(sample_payload.roles) + len(sample_payload.teams)
        assert callback.call_count == expected_calls

    def test_callback_receives_correct_arguments(self, mock_client, sample_roles):
        """Test callback receives step, current, and total."""
        from services.deployer import Deployer, DeployStepResult

        callback = Mock()
        deployer = Deployer(client=mock_client, progress_callback=callback)
        mock_client.create_custom_role.return_value = {"key": "test"}

        deployer.deploy_roles(sample_roles)

        # Check first call
        first_call = callback.call_args_list[0]
        step, current, total = first_call[0]

        assert isinstance(step, DeployStepResult)
        assert current == 1
        assert total == 2  # Two roles in sample

    def test_callback_error_does_not_stop_deployment(self, mock_client, sample_payload):
        """Test callback errors don't stop deployment."""
        from services.deployer import Deployer

        callback = Mock(side_effect=Exception("Callback error"))
        deployer = Deployer(client=mock_client, progress_callback=callback)
        mock_client.create_custom_role.return_value = {"key": "test"}
        mock_client.create_team.return_value = {"key": "test"}

        # Should not raise, deployment continues
        result = deployer.deploy_all(sample_payload)

        assert result.roles_created == 2
        assert result.teams_created == 1


# =============================================================================
# Rollback Tests
# =============================================================================

class TestRollback:
    """Tests for rollback functionality."""

    def test_rollback_deletes_created_roles(self, deployer, mock_client, sample_roles):
        """Test rollback deletes created roles."""
        mock_client.create_custom_role.return_value = {"key": "test"}

        deployer.deploy_roles(sample_roles)
        deployer.rollback()

        # Should call delete for each created role
        assert mock_client.delete_role.call_count == 2

    def test_rollback_deletes_in_reverse_order(self, deployer, mock_client, sample_roles):
        """Test rollback deletes in reverse order."""
        mock_client.create_custom_role.return_value = {"key": "test"}

        deployer.deploy_roles(sample_roles)

        delete_order = []
        mock_client.delete_role.side_effect = lambda key: delete_order.append(key)

        deployer.rollback()

        # Should be reversed
        expected_order = [r["key"] for r in reversed(sample_roles)]
        assert delete_order == expected_order

    def test_rollback_clears_tracking_lists(self, deployer, mock_client, sample_roles):
        """Test rollback clears created_roles and created_teams lists."""
        mock_client.create_custom_role.return_value = {"key": "test"}

        deployer.deploy_roles(sample_roles)
        assert len(deployer.created_roles) == 2

        deployer.rollback()

        assert len(deployer.created_roles) == 0
        assert len(deployer.created_teams) == 0

    def test_rollback_returns_false_on_delete_error(self, deployer, mock_client, sample_roles):
        """Test rollback returns False when delete fails."""
        from services.ld_exceptions import LDClientError

        mock_client.create_custom_role.return_value = {"key": "test"}
        mock_client.delete_role.side_effect = LDClientError("Delete failed")

        deployer.deploy_roles(sample_roles)
        success = deployer.rollback()

        assert success is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestDeployerIntegration:
    """Integration tests with MockLDClient."""

    def test_full_deployment_with_mock_client(self, sample_payload):
        """Test full deployment using MockLDClient."""
        from services.ld_client import MockLDClient
        from services.deployer import Deployer

        mock_client = MockLDClient()
        deployer = Deployer(client=mock_client)

        result = deployer.deploy_all(sample_payload)

        assert result.success is True
        assert result.roles_created == 2
        assert result.teams_created == 1
        assert len(mock_client.roles) == 2
        assert len(mock_client.teams) == 1

    def test_deployment_fails_gracefully_on_error(self, sample_payload):
        """Test deployment continues after individual failures."""
        from services.ld_client import MockLDClient
        from services.deployer import Deployer
        from services.ld_exceptions import LDConflictError

        mock_client = MockLDClient()
        # Pre-add one role to cause conflict
        mock_client.create_custom_role({
            "key": "developer-test",
            "name": "Existing",
            "policy": []
        })

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(sample_payload)

        # Should skip the existing role but create the other
        assert result.roles_created == 1
        assert result.roles_skipped == 1
        assert result.success is True  # Still succeeds overall


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_payload(self, deployer):
        """Test deploying empty payload."""
        from services import LDPayload

        payload = LDPayload()
        payload.roles = []
        payload.teams = []

        result = deployer.deploy_all(payload)

        assert result.success is True
        assert result.roles_created == 0
        assert result.teams_created == 0

    def test_payload_with_only_roles(self, deployer, mock_client, sample_roles):
        """Test deploying payload with only roles."""
        from services import LDPayload

        mock_client.create_custom_role.return_value = {"key": "test"}

        payload = LDPayload()
        payload.roles = sample_roles
        payload.teams = []

        result = deployer.deploy_all(payload)

        assert result.roles_created == 2
        assert result.teams_created == 0
        mock_client.create_team.assert_not_called()

    def test_payload_with_only_teams(self, deployer, mock_client, sample_teams):
        """Test deploying payload with only teams (assumes roles exist)."""
        from services import LDPayload

        mock_client.create_team.return_value = {"key": "test"}

        payload = LDPayload()
        payload.roles = []
        payload.teams = sample_teams

        result = deployer.deploy_all(payload)

        assert result.roles_created == 0
        assert result.teams_created == 1
        mock_client.create_custom_role.assert_not_called()
```

---

## Implementation Plan

### Step-by-Step Implementation

| Step | Task | File | Est. Lines |
|------|------|------|------------|
| 1 | Create DeployStep enum | `services/deployer.py` | ~10 |
| 2 | Create DeployStepResult dataclass | `services/deployer.py` | ~20 |
| 3 | Create DeployResult dataclass | `services/deployer.py` | ~50 |
| 4 | Create Deployer class init | `services/deployer.py` | ~20 |
| 5 | Implement `_deploy_role` | `services/deployer.py` | ~40 |
| 6 | Implement `_deploy_team` | `services/deployer.py` | ~40 |
| 7 | Implement `deploy_roles` | `services/deployer.py` | ~20 |
| 8 | Implement `deploy_teams` | `services/deployer.py` | ~20 |
| 9 | Implement `deploy_all` | `services/deployer.py` | ~30 |
| 10 | Implement `rollback` | `services/deployer.py` | ~25 |
| 11 | Update exports | `services/__init__.py` | +5 |
| 12 | Create tests | `tests/test_deployer.py` | ~400 |

### Python Concepts Used

| Concept | Where Used |
|---------|------------|
| Enum | `DeployStep` status values |
| Dataclasses | `DeployStepResult`, `DeployResult` |
| Callbacks | `progress_callback` parameter |
| Dependency Injection | `LDClientInterface` in `__init__` |
| Exception Handling | Try/except in `_deploy_role`, `_deploy_team` |
| List Tracking | `created_roles`, `created_teams` for rollback |
| Time Tracking | `time.time()` for duration |

---

## Learning Resources

| Topic | Resource |
|-------|----------|
| Python Enum | [Enum Docs](https://docs.python.org/3/library/enum.html) |
| Callbacks in Python | [Callback Pattern](https://realpython.com/python-callback-function/) |
| State Machines | [State Pattern](https://refactoring.guru/design-patterns/state) |
| Rollback Patterns | [Saga Pattern](https://microservices.io/patterns/data/saga.html) |

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [← Phase 6: LD Client](../phase6/) | [📋 All Phases](../) | [Phase 8: Deploy UI →](../phase8/) |
