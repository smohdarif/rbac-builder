# Phase 7: Python Concepts - Callbacks, State Machines & Error Recovery

## Table of Contents

1. [Callbacks in Python](#1-callbacks-in-python)
2. [Enums for State Management](#2-enums-for-state-management)
3. [Dependency Injection](#3-dependency-injection)
4. [Error Recovery Patterns](#4-error-recovery-patterns)
5. [The Saga Pattern (Rollback)](#5-the-saga-pattern-rollback)
6. [Progress Tracking](#6-progress-tracking)
7. [Testing with Mocks](#7-testing-with-mocks)
8. [Quick Reference Card](#8-quick-reference-card)

---

## 1. Callbacks in Python

### What is a Callback?

A callback is a function you pass to another function, which will "call back" your function at certain points.

```python
# =============================================================================
# LESSON: Callbacks - Functions as Arguments
# =============================================================================
# In Python, functions are "first-class citizens" - you can pass them around
# like any other value

def greet(name):
    return f"Hello, {name}!"

def process_with_callback(data, callback):
    """Process data and call the callback with the result."""
    result = data.upper()
    callback(result)  # Call the function that was passed in

# Pass the function (without parentheses - we're passing the function itself)
process_with_callback("hello", print)  # Output: HELLO

# Custom callback
def my_callback(result):
    print(f"Got result: {result}")

process_with_callback("world", my_callback)  # Output: Got result: WORLD
```

### Callbacks for Progress Updates

```python
# =============================================================================
# LESSON: Progress Callbacks
# =============================================================================
# Callbacks let the caller decide what to do with progress updates

from typing import Callable, Optional

def deploy_items(
    items: list,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
):
    """
    Deploy items with optional progress callback.

    Args:
        items: Items to deploy
        progress_callback: Called with (item_name, current, total)
    """
    total = len(items)

    for i, item in enumerate(items, start=1):
        # Deploy the item...
        name = item["name"]

        # Notify progress if callback provided
        if progress_callback:
            progress_callback(name, i, total)


# Usage 1: Print progress
def print_progress(name, current, total):
    print(f"[{current}/{total}] Deploying: {name}")

deploy_items(items, progress_callback=print_progress)


# Usage 2: Update Streamlit UI
def streamlit_progress(name, current, total):
    st.progress(current / total)
    st.write(f"Deploying: {name}")

deploy_items(items, progress_callback=streamlit_progress)


# Usage 3: No callback (silent)
deploy_items(items)  # Works fine, no output
```

### Type Hints for Callbacks

```python
# =============================================================================
# LESSON: Typing Callbacks with Callable
# =============================================================================
# Use Callable to specify callback signatures

from typing import Callable, Optional

# Callable[[arg_types...], return_type]

# Callback that takes a string, returns nothing
StringCallback = Callable[[str], None]

# Callback that takes int, int, returns bool
CompareCallback = Callable[[int, int], bool]

# Callback with multiple args
ProgressCallback = Callable[[str, int, int], None]

def process(callback: Optional[ProgressCallback] = None):
    """Function with typed callback parameter."""
    if callback:
        callback("item", 1, 10)
```

### Safe Callback Invocation

```python
# =============================================================================
# LESSON: Handling Callback Errors
# =============================================================================
# Never let callback errors crash your main logic

def deploy_with_safe_callback(items, callback=None):
    for item in items:
        # Do the actual work
        result = deploy_item(item)

        # Call callback safely
        if callback:
            try:
                callback(item, result)
            except Exception as e:
                # Log but don't crash
                print(f"Warning: Callback error: {e}")
                # Continue processing other items
```

---

## 2. Enums for State Management

### What is an Enum?

An Enum (enumeration) is a set of named values. Perfect for states that have a fixed set of options.

```python
# =============================================================================
# LESSON: Enum Basics
# =============================================================================
# Enums are better than strings for fixed sets of values

from enum import Enum

# BAD: Using strings (typo-prone)
status = "in_progres"  # Typo! Will cause bugs

# GOOD: Using Enum
class DeployStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

status = DeployStatus.IN_PROGRESS  # IDE autocomplete, no typos
```

### Enum Benefits

```python
# =============================================================================
# LESSON: Why Use Enums?
# =============================================================================

from enum import Enum

class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

# 1. Autocompletion - IDE helps you
color = Color.RED  # IDE shows options

# 2. Type checking
def paint(color: Color):
    print(f"Painting {color.value}")

paint(Color.RED)  # ✅ Works
paint("red")      # ⚠️ Type checker warns

# 3. Comparison
if color == Color.RED:
    print("It's red!")

# 4. Iteration
for c in Color:
    print(c.name, c.value)
# Output:
# RED red
# GREEN green
# BLUE blue

# 5. Access value and name
print(Color.RED.value)  # "red"
print(Color.RED.name)   # "RED"
```

### Enum for Deployment States

```python
# =============================================================================
# LESSON: Deployment State Machine
# =============================================================================

from enum import Enum
from dataclasses import dataclass

class DeployStep(Enum):
    """Possible states for a deployment step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class DeployStepResult:
    """Result of a deployment step."""
    resource_type: str
    resource_key: str
    status: DeployStep
    message: str = ""
    error: str = None

    def is_success(self) -> bool:
        """Check if step was successful."""
        return self.status in (DeployStep.COMPLETED, DeployStep.SKIPPED)


# Usage
result = DeployStepResult(
    resource_type="role",
    resource_key="developer-role",
    status=DeployStep.COMPLETED,
    message="Created successfully"
)

if result.is_success():
    print("Step succeeded!")
```

---

## 3. Dependency Injection

### What is Dependency Injection?

Instead of creating dependencies inside a class, you pass them in from outside. This makes code testable and flexible.

```python
# =============================================================================
# LESSON: Without Dependency Injection (Hard to Test)
# =============================================================================

# BAD: Class creates its own dependency
class Deployer:
    def __init__(self):
        self.client = RealLDClient()  # Hard-coded! Can't swap for testing

    def deploy(self, data):
        self.client.create_role(data)  # Always uses real API


# Testing is hard - you'd make real API calls!
deployer = Deployer()
deployer.deploy(data)  # Actually calls LaunchDarkly API
```

```python
# =============================================================================
# LESSON: With Dependency Injection (Testable)
# =============================================================================

# GOOD: Class receives its dependency
class Deployer:
    def __init__(self, client: LDClientInterface):  # Injected!
        self.client = client

    def deploy(self, data):
        self.client.create_role(data)


# In production - use real client
real_client = RealLDClient(api_key="...")
deployer = Deployer(client=real_client)

# In tests - use mock client
mock_client = MockLDClient()
deployer = Deployer(client=mock_client)
deployer.deploy(data)  # No real API calls!
```

### Interface Pattern

```python
# =============================================================================
# LESSON: Programming to an Interface
# =============================================================================
# Both real and mock clients implement the same interface

from abc import ABC, abstractmethod

class LDClientInterface(ABC):
    """Interface that both clients must implement."""

    @abstractmethod
    def create_role(self, data: dict) -> dict:
        pass

    @abstractmethod
    def create_team(self, data: dict) -> dict:
        pass


class RealLDClient(LDClientInterface):
    """Real implementation - calls actual API."""

    def create_role(self, data: dict) -> dict:
        response = requests.post(API_URL, json=data)
        return response.json()

    def create_team(self, data: dict) -> dict:
        response = requests.post(API_URL, json=data)
        return response.json()


class MockLDClient(LDClientInterface):
    """Mock implementation - no API calls."""

    def __init__(self):
        self.roles = []
        self.teams = []

    def create_role(self, data: dict) -> dict:
        self.roles.append(data)
        return data

    def create_team(self, data: dict) -> dict:
        self.teams.append(data)
        return data


# Deployer works with ANY implementation
class Deployer:
    def __init__(self, client: LDClientInterface):
        self.client = client  # Could be real or mock!
```

---

## 4. Error Recovery Patterns

### Continue on Error

```python
# =============================================================================
# LESSON: Collect Errors, Don't Stop
# =============================================================================
# For batch operations, collect all errors instead of stopping on first

def deploy_all_roles(roles: list) -> dict:
    """Deploy all roles, collecting errors along the way."""

    results = {
        "created": [],
        "failed": [],
        "errors": []
    }

    for role in roles:
        try:
            client.create_role(role)
            results["created"].append(role["key"])

        except LDConflictError:
            # Not really an error - just skip
            results["skipped"].append(role["key"])

        except LDClientError as e:
            # Real error - record it but continue
            results["failed"].append(role["key"])
            results["errors"].append(f"{role['key']}: {str(e)}")

    return results


# All roles processed, errors collected
results = deploy_all_roles(roles)
print(f"Created: {len(results['created'])}")
print(f"Failed: {len(results['failed'])}")
for error in results["errors"]:
    print(f"  - {error}")
```

### Error Classification

```python
# =============================================================================
# LESSON: Handle Different Errors Differently
# =============================================================================

def deploy_role(role: dict) -> DeployStepResult:
    try:
        client.create_role(role)
        return DeployStepResult(status=DeployStep.COMPLETED)

    except LDConflictError:
        # Expected - resource exists, skip it
        return DeployStepResult(
            status=DeployStep.SKIPPED,
            message="Already exists"
        )

    except LDValidationError as e:
        # User error - bad data
        return DeployStepResult(
            status=DeployStep.FAILED,
            error=f"Invalid data: {e.message}"
        )

    except LDRateLimitError as e:
        # Temporary - could retry
        return DeployStepResult(
            status=DeployStep.FAILED,
            error=f"Rate limited, retry after {e.retry_after}s"
        )

    except LDClientError as e:
        # Unknown error
        return DeployStepResult(
            status=DeployStep.FAILED,
            error=str(e)
        )
```

---

## 5. The Saga Pattern (Rollback)

### What is the Saga Pattern?

When a multi-step operation fails, you need to undo the completed steps. This is the "saga" pattern.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SAGA PATTERN                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Create Role A  ───────────────────────────────────►   │
│  Step 2: Create Role B  ───────────────────────────────────►   │
│  Step 3: Create Team    ───────────── ✗ FAILS                  │
│                                                                 │
│  ROLLBACK:                                                      │
│  ◄─────────────────────────────────── Delete Role B            │
│  ◄─────────────────────────────────── Delete Role A            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tracking Created Resources

```python
# =============================================================================
# LESSON: Track What You Create (for Rollback)
# =============================================================================

class Deployer:
    def __init__(self, client):
        self.client = client
        # Track created resources for potential rollback
        self.created_roles = []
        self.created_teams = []

    def deploy_role(self, role):
        result = self.client.create_role(role)

        # Track it so we can delete if needed
        self.created_roles.append(role["key"])

        return result

    def rollback(self):
        """Delete all resources created in this session."""
        # Delete in reverse order (teams before roles)
        for team_key in reversed(self.created_teams):
            try:
                self.client.delete_team(team_key)
            except Exception as e:
                print(f"Failed to delete team {team_key}: {e}")

        for role_key in reversed(self.created_roles):
            try:
                self.client.delete_role(role_key)
            except Exception as e:
                print(f"Failed to delete role {role_key}: {e}")

        # Clear tracking
        self.created_roles = []
        self.created_teams = []
```

### Using Rollback

```python
# =============================================================================
# LESSON: Rollback on Critical Failure
# =============================================================================

def deploy_all(payload):
    deployer = Deployer(client)

    try:
        # Deploy roles
        for role in payload.roles:
            deployer.deploy_role(role)

        # Deploy teams
        for team in payload.teams:
            deployer.deploy_team(team)

        return {"success": True}

    except CriticalError as e:
        # Something went very wrong - undo everything
        print(f"Critical error: {e}")
        print("Rolling back...")
        deployer.rollback()
        return {"success": False, "error": str(e)}
```

---

## 6. Progress Tracking

### Progress with Dataclasses

```python
# =============================================================================
# LESSON: Structured Progress Tracking
# =============================================================================

from dataclasses import dataclass, field
from typing import List
import time

@dataclass
class DeployResult:
    """Track deployment progress and results."""
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

    def add_step(self, step: DeployStepResult):
        """Add a step and update counters."""
        self.steps.append(step)

        # Update appropriate counter
        if step.resource_type == "role":
            if step.status == DeployStep.COMPLETED:
                self.roles_created += 1
            elif step.status == DeployStep.SKIPPED:
                self.roles_skipped += 1
            elif step.status == DeployStep.FAILED:
                self.roles_failed += 1
                self.success = False  # Mark overall as failed

        # Same for teams...

        # Collect errors
        if step.error:
            self.errors.append(f"{step.resource_key}: {step.error}")
```

### Using Progress Callbacks with Streamlit

```python
# =============================================================================
# LESSON: Streamlit Progress Integration
# =============================================================================

import streamlit as st
from services.deployer import Deployer

def deploy_with_progress(payload):
    """Deploy with Streamlit progress bar."""

    # Create progress elements
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(step, current, total):
        """Callback to update Streamlit UI."""
        progress = current / total
        progress_bar.progress(progress)

        if step.status == DeployStep.COMPLETED:
            status_text.success(f"✅ {step.resource_key}")
        elif step.status == DeployStep.SKIPPED:
            status_text.info(f"⏭️ {step.resource_key} (skipped)")
        elif step.status == DeployStep.FAILED:
            status_text.error(f"❌ {step.resource_key}: {step.error}")

    # Deploy with callback
    deployer = Deployer(client, progress_callback=update_progress)
    result = deployer.deploy_all(payload)

    # Final status
    if result.success:
        st.success(f"Deployed {result.roles_created} roles and {result.teams_created} teams!")
    else:
        st.error(f"Deployment failed with {len(result.errors)} errors")

    return result
```

---

## 7. Testing with Mocks

### Testing the Deployer

```python
# =============================================================================
# LESSON: Testing with Mock Client
# =============================================================================

import pytest
from unittest.mock import Mock, MagicMock

@pytest.fixture
def mock_client():
    """Create a mock client for testing."""
    client = MagicMock()
    return client

@pytest.fixture
def deployer(mock_client):
    """Create deployer with mock client."""
    return Deployer(client=mock_client)


def test_deploy_role_calls_client(deployer, mock_client):
    """Test that deployer calls client.create_role."""
    role = {"key": "test-role", "name": "Test", "policy": []}

    mock_client.create_role.return_value = {"key": "test-role"}

    deployer.deploy_roles([role])

    mock_client.create_role.assert_called_once_with(role)


def test_deploy_handles_conflict(deployer, mock_client):
    """Test that conflicts are handled gracefully."""
    from services.ld_exceptions import LDConflictError

    role = {"key": "existing-role", "name": "Existing", "policy": []}

    mock_client.create_role.side_effect = LDConflictError("exists")

    result = deployer.deploy_roles([role])

    assert result.roles_skipped == 1
    assert result.success is True  # Skipped is not a failure
```

### Testing Callbacks

```python
# =============================================================================
# LESSON: Testing Callbacks
# =============================================================================

def test_progress_callback_called(mock_client):
    """Test that progress callback is called for each step."""
    callback = Mock()
    deployer = Deployer(client=mock_client, progress_callback=callback)

    roles = [
        {"key": "role1", "name": "Role 1", "policy": []},
        {"key": "role2", "name": "Role 2", "policy": []}
    ]
    mock_client.create_role.return_value = {}

    deployer.deploy_roles(roles)

    # Callback should be called twice (once per role)
    assert callback.call_count == 2


def test_progress_callback_receives_correct_args(mock_client):
    """Test callback receives correct arguments."""
    callback = Mock()
    deployer = Deployer(client=mock_client, progress_callback=callback)

    roles = [{"key": "role1", "name": "Role 1", "policy": []}]
    mock_client.create_role.return_value = {}

    deployer.deploy_roles(roles)

    # Check the call arguments
    step, current, total = callback.call_args[0]
    assert current == 1
    assert total == 1
    assert step.resource_key == "role1"
```

### Testing Rollback

```python
# =============================================================================
# LESSON: Testing Rollback
# =============================================================================

def test_rollback_deletes_created_resources(mock_client):
    """Test rollback deletes what was created."""
    deployer = Deployer(client=mock_client)

    roles = [
        {"key": "role1", "name": "Role 1", "policy": []},
        {"key": "role2", "name": "Role 2", "policy": []}
    ]
    mock_client.create_role.return_value = {}

    # Deploy some roles
    deployer.deploy_roles(roles)

    # Rollback
    deployer.rollback()

    # Should delete both roles
    assert mock_client.delete_role.call_count == 2

    # In reverse order
    calls = mock_client.delete_role.call_args_list
    assert calls[0][0][0] == "role2"  # Last created, first deleted
    assert calls[1][0][0] == "role1"
```

---

## 8. Quick Reference Card

### Callback Pattern

```python
from typing import Callable, Optional

# Define callback type
ProgressCallback = Callable[[str, int, int], None]

# Accept optional callback
def process(items, callback: Optional[ProgressCallback] = None):
    for i, item in enumerate(items):
        result = do_work(item)
        if callback:
            try:
                callback(item, i + 1, len(items))
            except Exception:
                pass  # Don't let callback crash main logic
```

### Enum Pattern

```python
from enum import Enum

class Status(Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"

# Usage
status = Status.PENDING
if status == Status.COMPLETE:
    print("Done!")
```

### Dependency Injection

```python
class Service:
    def __init__(self, client: ClientInterface):
        self.client = client  # Injected, not created

# Production
service = Service(client=RealClient())

# Testing
service = Service(client=MockClient())
```

### Error Collection Pattern

```python
results = {"success": [], "failed": [], "errors": []}

for item in items:
    try:
        process(item)
        results["success"].append(item)
    except SkippableError:
        results["skipped"].append(item)
    except Exception as e:
        results["failed"].append(item)
        results["errors"].append(str(e))
```

### Rollback Pattern

```python
created = []

try:
    for item in items:
        create(item)
        created.append(item)  # Track for rollback
except CriticalError:
    for item in reversed(created):
        delete(item)  # Undo in reverse order
```

---

## Next Steps

Now that you understand the Python concepts for Phase 7, proceed to:
- [DESIGN.md](DESIGN.md) - Implementation details and test cases
- [README.md](README.md) - Quick overview and checklist

---

[← Back to Phase 7 README](README.md) | [Phase 7 DESIGN →](DESIGN.md)
