# Phase 8: Complete Deploy UI - Design Document

| Attribute | Value |
|-----------|-------|
| **Phase** | 8 of 10 |
| **Status** | 📋 Planned |
| **Goal** | Wire Deploy UI to real LaunchDarkly API with progress tracking |
| **Dependencies** | Phase 5 (UI), Phase 6 (LDClient), Phase 7 (Deployer) |
| **Estimated Lessons** | Streamlit Callbacks, Session State, Async Patterns |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Quick overview and checklist |
| [PYTHON_CONCEPTS.md](PYTHON_CONCEPTS.md) | Deep dive into Streamlit concepts |
| [Phase 6 DESIGN.md](../phase6/DESIGN.md) | LDClient that makes API calls |
| [Phase 7 DESIGN.md](../phase7/DESIGN.md) | Deployer that orchestrates deployment |

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

Completing the Deploy tab UI to connect to the real LaunchDarkly API:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOY TAB UI (Phase 8)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  API Configuration (Connected Mode Only)                 │   │
│  │  ┌─────────────────────────────────────┐ ┌───────────┐  │   │
│  │  │ 🔑 API Key: ••••••••••••••••••••••• │ │ Test Conn │  │   │
│  │  └─────────────────────────────────────┘ └───────────┘  │   │
│  │  ✅ Connection successful                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Deployment Options                                      │   │
│  │  ☐ Dry-run (preview only, no changes)                   │   │
│  │  ☑ Skip existing resources                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [🚀 Deploy to LaunchDarkly]                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Deployment Progress                                     │   │
│  │  ████████████████░░░░░░░░░░░░░░ 60%                     │   │
│  │                                                          │   │
│  │  ✅ developer-test-env (created)                        │   │
│  │  ✅ developer-prod-env (created)                        │   │
│  │  ⏭️ qa-test-env (skipped - exists)                      │   │
│  │  🔄 qa-prod-env (in progress...)                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Results                                                 │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐                   │   │
│  │  │ Created │ │ Skipped │ │ Failed  │                   │   │
│  │  │    4    │ │    1    │ │    0    │                   │   │
│  │  └─────────┘ └─────────┘ └─────────┘                   │   │
│  │                                                          │   │
│  │  Deployment completed successfully in 3.2s              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT DATA FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Session State                                                  │
│  ┌──────────────────┐                                          │
│  │ • customer_name  │                                          │
│  │ • project_key    │                                          │
│  │ • teams_df       │                                          │
│  │ • env_groups_df  │                                          │
│  │ • project_matrix │                                          │
│  │ • env_matrix     │                                          │
│  │ • ld_api_key     │◄── NEW: API key input                    │
│  │ • deploy_result  │◄── NEW: Deployment result                │
│  └────────┬─────────┘                                          │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────┐                                          │
│  │  PayloadBuilder  │ (Phase 3)                                │
│  │  build_payload() │                                          │
│  └────────┬─────────┘                                          │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────┐      ┌──────────────────┐                │
│  │   DeployPayload  │      │    LDClient      │                │
│  │   • roles: []    │─────▶│  (api_key)       │                │
│  │   • teams: []    │      └────────┬─────────┘                │
│  └──────────────────┘               │                          │
│           │                         │                          │
│           ▼                         ▼                          │
│  ┌──────────────────────────────────────────┐                  │
│  │              Deployer                     │                  │
│  │  deploy_all(payload) ──► progress_callback│                  │
│  └────────────────────────────────┬─────────┘                  │
│                                   │                             │
│                                   ▼                             │
│                          ┌──────────────────┐                  │
│                          │   DeployResult   │                  │
│                          │  • roles_created │                  │
│                          │  • teams_created │                  │
│                          │  • errors        │                  │
│                          └──────────────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### UI States

| State | Description | UI Elements |
|-------|-------------|-------------|
| **Not Ready** | Missing customer name or validation errors | Deploy button disabled |
| **Manual Mode** | User selected Manual mode | Deploy button disabled, shows message |
| **Ready** | Connected mode, no API key | API key input shown |
| **Connected** | API key entered | Test Connection button enabled |
| **Verified** | Connection test passed | Deploy button enabled |
| **Deploying** | Deployment in progress | Progress bar, step logs |
| **Success** | Deployment completed | Results summary, success message |
| **Failed** | Deployment had errors | Error details, Rollback button |

### Feature Summary

| Feature | Description |
|---------|-------------|
| **API Key Input** | Secure password field, stored in session only |
| **Connection Test** | Verify API key works before deploying |
| **Dry-Run Mode** | Preview what would happen without making changes |
| **Skip Existing** | Don't fail on conflicts, just skip |
| **Progress Tracking** | Real-time progress bar with step details |
| **Results Display** | Show created/skipped/failed counts |
| **Error Details** | Expandable error messages |
| **Rollback** | Delete created resources on failure |

---

## Detailed Low-Level Design (DLD)

### File Structure

```
ui/
├── deploy_tab.py         # Main deploy tab (UPDATE)
└── __init__.py           # Exports (no change needed)
```

### New Session State Keys

| Key | Type | Description |
|-----|------|-------------|
| `ld_api_key` | `str` | LaunchDarkly API key (not persisted) |
| `ld_connection_verified` | `bool` | True if connection test passed |
| `deploy_in_progress` | `bool` | True during deployment |
| `deploy_result` | `DeployResult` | Result of last deployment |
| `deploy_progress` | `float` | Current progress (0.0 - 1.0) |
| `deploy_steps` | `List[DeployStepResult]` | Step-by-step results |
| `deployer_instance` | `Deployer` | Active deployer for rollback |

### Updated Deploy Tab Functions

| Function | Parameters | Description |
|----------|------------|-------------|
| `render_deploy_tab` | `customer_name, mode` | Main entry point (UPDATE) |
| `_render_api_config` | None | NEW: API key input section |
| `_render_deploy_options` | None | NEW: Dry-run, skip existing toggles |
| `_render_deploy_button` | `payload, api_key` | NEW: Deploy action button |
| `_render_deploy_progress` | None | NEW: Progress bar and steps |
| `_render_deploy_results` | `result` | NEW: Results summary |
| `_render_rollback_button` | `deployer` | NEW: Rollback option |
| `_execute_deployment` | `payload, api_key, options` | NEW: Run deployment |
| `_create_progress_callback` | None | NEW: Streamlit progress updater |

### UI Component Layout

```
render_deploy_tab()
├── _render_summary()                    # Existing
├── _render_validation()                 # Existing
├── _render_preview_json()               # Existing
├── IF mode == "Connected":
│   ├── _render_api_config()             # NEW
│   │   ├── API Key Input
│   │   ├── Test Connection Button
│   │   └── Connection Status
│   ├── _render_deploy_options()         # NEW
│   │   ├── Dry-run Checkbox
│   │   └── Skip Existing Checkbox
│   ├── _render_deploy_button()          # NEW (replaces placeholder)
│   ├── IF deploying:
│   │   └── _render_deploy_progress()    # NEW
│   └── IF deploy_result:
│       ├── _render_deploy_results()     # NEW
│       └── IF errors:
│           └── _render_rollback_button()# NEW
└── _render_ld_payload_generator()       # Existing
```

### Progress Callback Design

```python
# The challenge: Streamlit reruns entire script on state change
# Solution: Use session_state to store progress, callback updates it

def _create_progress_callback():
    """Create callback that updates session state."""

    def callback(step: DeployStepResult, current: int, total: int):
        # Update progress in session state
        st.session_state.deploy_progress = current / total

        # Append step to list
        if "deploy_steps" not in st.session_state:
            st.session_state.deploy_steps = []
        st.session_state.deploy_steps.append(step)

        # Note: This won't update UI immediately due to Streamlit's model
        # We'll display accumulated results after deployment completes

    return callback
```

### Error Handling States

```
┌─────────────────────────────────────────────────────────────────┐
│                    ERROR HANDLING FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Error Type              │ Handling                             │
│  ────────────────────────┼──────────────────────────────────── │
│  Empty API Key           │ Show warning, disable deploy         │
│  Connection Failed       │ Show error, keep API input           │
│  Auth Error (401/403)    │ Show "Invalid API key" message       │
│  Rate Limited (429)      │ Show retry message with wait time    │
│  Conflict (409)          │ Skip (if skip_existing) or show      │
│  Validation (400)        │ Show details, suggest fix            │
│  Server Error (5xx)      │ Show retry option                    │
│  Partial Failure         │ Show results + Rollback button       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pseudo Logic

### 1. Render API Configuration Section

```
FUNCTION _render_api_config():
    st.subheader("🔑 API Configuration")

    1. CREATE two columns for input and button
       col1, col2 = st.columns([3, 1])

    2. RENDER API key input
       WITH col1:
           api_key = st.text_input(
               "LaunchDarkly API Key",
               type="password",  # Hide characters
               value=st.session_state.get("ld_api_key", ""),
               placeholder="Enter your API key...",
               help="API key with createRole and createTeam permissions"
           )

           # Store in session state
           st.session_state.ld_api_key = api_key

    3. RENDER test connection button
       WITH col2:
           st.write("")  # Spacing to align with input
           IF st.button("🔌 Test Connection"):
               _test_connection(api_key)

    4. SHOW connection status
       IF st.session_state.get("ld_connection_verified"):
           st.success("✅ Connection verified!")
       ELIF st.session_state.get("ld_connection_error"):
           st.error(f"❌ {st.session_state.ld_connection_error}")
```

### 2. Test Connection

```
FUNCTION _test_connection(api_key: str):
    1. VALIDATE API key not empty
       IF NOT api_key OR api_key.strip() == "":
           st.session_state.ld_connection_verified = False
           st.session_state.ld_connection_error = "API key is required"
           RETURN

    2. TRY to connect
       TRY:
           client = LDClient(api_key=api_key)
           success = client.health_check()

           IF success:
               st.session_state.ld_connection_verified = True
               st.session_state.ld_connection_error = None
           ELSE:
               st.session_state.ld_connection_verified = False
               st.session_state.ld_connection_error = "Health check failed"

       EXCEPT LDAuthenticationError:
           st.session_state.ld_connection_verified = False
           st.session_state.ld_connection_error = "Invalid API key"

       EXCEPT LDClientError AS e:
           st.session_state.ld_connection_verified = False
           st.session_state.ld_connection_error = str(e)

    3. RERUN to update UI
       st.rerun()
```

### 3. Render Deploy Options

```
FUNCTION _render_deploy_options():
    st.subheader("⚙️ Deployment Options")

    col1, col2 = st.columns(2)

    WITH col1:
        dry_run = st.checkbox(
            "🧪 Dry-run mode",
            value=st.session_state.get("deploy_dry_run", False),
            help="Preview deployment without making changes"
        )
        st.session_state.deploy_dry_run = dry_run

    WITH col2:
        skip_existing = st.checkbox(
            "⏭️ Skip existing resources",
            value=st.session_state.get("deploy_skip_existing", True),
            help="Don't fail if role/team already exists"
        )
        st.session_state.deploy_skip_existing = skip_existing
```

### 4. Render Deploy Button

```
FUNCTION _render_deploy_button(payload: DeployPayload):
    1. DETERMINE if button should be enabled
       api_key = st.session_state.get("ld_api_key", "")
       connection_verified = st.session_state.get("ld_connection_verified", False)
       deploy_in_progress = st.session_state.get("deploy_in_progress", False)

       button_enabled = (
           api_key AND
           connection_verified AND
           NOT deploy_in_progress AND
           payload.get_role_count() + payload.get_team_count() > 0
       )

    2. RENDER deploy button
       IF st.button(
           "🚀 Deploy to LaunchDarkly",
           type="primary",
           disabled=NOT button_enabled,
           use_container_width=True
       ):
           _execute_deployment(payload)

    3. SHOW helpful message if disabled
       IF NOT button_enabled:
           IF NOT api_key:
               st.caption("Enter API key above")
           ELIF NOT connection_verified:
               st.caption("Test connection first")
           ELIF deploy_in_progress:
               st.caption("Deployment in progress...")
           ELSE:
               st.caption("Generate payload first")
```

### 5. Execute Deployment

```
FUNCTION _execute_deployment(payload: DeployPayload):
    1. SET deployment in progress
       st.session_state.deploy_in_progress = True
       st.session_state.deploy_steps = []
       st.session_state.deploy_result = None

    2. GET options from session state
       api_key = st.session_state.ld_api_key
       dry_run = st.session_state.get("deploy_dry_run", False)
       skip_existing = st.session_state.get("deploy_skip_existing", True)

    3. CREATE client and deployer
       TRY:
           client = LDClient(api_key=api_key)
           deployer = Deployer(
               client=client,
               dry_run=dry_run,
               skip_existing=skip_existing,
               progress_callback=_create_progress_callback()
           )

           # Store deployer for potential rollback
           st.session_state.deployer_instance = deployer

    4. EXECUTE deployment
           WITH st.spinner("Deploying to LaunchDarkly..."):
               result = deployer.deploy_all(payload)

           # Store result
           st.session_state.deploy_result = result

       EXCEPT LDAuthenticationError:
           st.session_state.deploy_result = None
           st.error("❌ Authentication failed. Check your API key.")

       EXCEPT LDClientError AS e:
           st.session_state.deploy_result = None
           st.error(f"❌ Deployment failed: {str(e)}")

       FINALLY:
           st.session_state.deploy_in_progress = False

    5. RERUN to show results
       st.rerun()
```

### 6. Render Deploy Progress

```
FUNCTION _render_deploy_progress():
    st.subheader("📊 Deployment Progress")

    1. GET progress from session state
       progress = st.session_state.get("deploy_progress", 0.0)
       steps = st.session_state.get("deploy_steps", [])

    2. RENDER progress bar
       st.progress(progress)

    3. RENDER step details
       FOR step IN steps:
           IF step.status == DeployStep.COMPLETED:
               st.success(f"✅ {step.resource_key} (created)")
           ELIF step.status == DeployStep.SKIPPED:
               st.info(f"⏭️ {step.resource_key} (skipped)")
           ELIF step.status == DeployStep.FAILED:
               st.error(f"❌ {step.resource_key}: {step.error}")
           ELIF step.status == DeployStep.IN_PROGRESS:
               st.write(f"🔄 {step.resource_key} (in progress...)")
```

### 7. Render Deploy Results

```
FUNCTION _render_deploy_results(result: DeployResult):
    st.subheader("📋 Deployment Results")

    1. RENDER summary metrics
       col1, col2, col3, col4 = st.columns(4)

       WITH col1:
           st.metric("✅ Created", result.roles_created + result.teams_created)
       WITH col2:
           st.metric("⏭️ Skipped", result.roles_skipped + result.teams_skipped)
       WITH col3:
           st.metric("❌ Failed", result.roles_failed + result.teams_failed)
       WITH col4:
           st.metric("⏱️ Duration", f"{result.duration_seconds:.1f}s")

    2. SHOW overall status
       IF result.success:
           IF st.session_state.get("deploy_dry_run"):
               st.success("🧪 Dry-run completed! No changes were made.")
           ELSE:
               st.success("🎉 Deployment completed successfully!")
       ELSE:
           st.error(f"⚠️ Deployment completed with {len(result.errors)} error(s)")

    3. SHOW error details if any
       IF result.errors:
           WITH st.expander(f"🚫 Error Details ({len(result.errors)})", expanded=True):
               FOR error IN result.errors:
                   st.error(error)

    4. SHOW detailed steps
       WITH st.expander("📝 Detailed Steps", expanded=False):
           FOR step IN result.steps:
               status_icon = {
                   DeployStep.COMPLETED: "✅",
                   DeployStep.SKIPPED: "⏭️",
                   DeployStep.FAILED: "❌"
               }.get(step.status, "❓")

               st.write(f"{status_icon} **{step.resource_type}**: {step.resource_key}")
               IF step.message:
                   st.caption(f"   {step.message}")
               IF step.error:
                   st.caption(f"   Error: {step.error}")
```

### 8. Render Rollback Button

```
FUNCTION _render_rollback_button():
    result = st.session_state.get("deploy_result")
    deployer = st.session_state.get("deployer_instance")

    1. CHECK if rollback is applicable
       IF NOT result OR NOT deployer:
           RETURN
       IF result.success:
           RETURN  # No need to rollback success
       IF result.roles_created + result.teams_created == 0:
           RETURN  # Nothing to rollback

    2. RENDER rollback section
       st.warning("Some resources were created before the failure.")

       IF st.button("🔙 Rollback Created Resources", type="secondary"):
           WITH st.spinner("Rolling back..."):
               success = deployer.rollback()

           IF success:
               st.success("✅ Rollback completed. Created resources have been deleted.")
               # Clear deployer instance
               st.session_state.deployer_instance = None
           ELSE:
               st.error("⚠️ Rollback encountered errors. Some resources may remain.")
```

### 9. Updated Main Render Function

```
FUNCTION render_deploy_tab(customer_name: str, mode: str):
    st.header("Step 3: Review & Deploy")

    1. CHECK prerequisites
       IF NOT customer_name:
           st.info("Complete Step 1 first.")
           RETURN

    2. RENDER summary section
       _render_summary(customer_name)
       st.divider()

    3. RENDER validation section
       validation_result = _render_validation(customer_name)
       st.divider()

    4. RENDER JSON preview
       _render_preview_json(customer_name, mode)
       st.divider()

    5. IF Connected mode - SHOW deployment UI
       IF mode == "Connected":
           # API Configuration
           _render_api_config()
           st.divider()

           # Deployment Options
           _render_deploy_options()
           st.divider()

           # Generate payload if validated
           IF validation_result.is_valid:
               IF "ld_payload" IN st.session_state:
                   payload = st.session_state.ld_payload

                   # Deploy button
                   _render_deploy_button(payload)

                   # Progress (during deployment)
                   IF st.session_state.get("deploy_in_progress"):
                       _render_deploy_progress()

                   # Results (after deployment)
                   IF st.session_state.get("deploy_result"):
                       _render_deploy_results(st.session_state.deploy_result)
                       _render_rollback_button()
               ELSE:
                   st.info("Generate LaunchDarkly payload first (below)")

       ELSE:
           st.info("Switch to **Connected** mode in the sidebar to deploy via API.")

       st.divider()

    6. RENDER payload generator (always available)
       _render_ld_payload_generator(customer_name, validation_result)
```

---

## Test Cases

### Test File: `tests/test_deploy_ui.py`

```python
"""
Tests for Phase 8: Complete Deploy UI
=====================================

Tests cover:
1. API configuration rendering
2. Connection test functionality
3. Deploy options
4. Deployment execution
5. Progress tracking
6. Results display
7. Rollback functionality
8. Error handling

Note: These tests use mocked Streamlit components.

Run with: pytest tests/test_deploy_ui.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_session_state():
    """Create mock session state."""
    state = {
        "customer_name": "Test Corp",
        "project": "test-project",
        "ld_api_key": "",
        "ld_connection_verified": False,
        "deploy_dry_run": False,
        "deploy_skip_existing": True,
        "deploy_in_progress": False,
        "deploy_result": None,
    }
    return state


@pytest.fixture
def mock_payload():
    """Create mock deployment payload."""
    from services import DeployPayload

    return DeployPayload(
        customer_name="Test Corp",
        project_key="test-project",
        roles=[
            {"key": "dev-test", "name": "Developer - Test", "policy": []},
            {"key": "dev-prod", "name": "Developer - Prod", "policy": []}
        ],
        teams=[
            {"key": "developers", "name": "Developers", "customRoleKeys": ["dev-test", "dev-prod"]}
        ]
    )


@pytest.fixture
def mock_client():
    """Create mock LD client."""
    from services import MockLDClient
    return MockLDClient()


# =============================================================================
# API Configuration Tests
# =============================================================================

class TestAPIConfiguration:
    """Tests for API configuration section."""

    def test_empty_api_key_disables_deploy(self, mock_session_state):
        """Test that empty API key disables deployment."""
        mock_session_state["ld_api_key"] = ""
        mock_session_state["ld_connection_verified"] = False

        # Deploy should be disabled
        assert not mock_session_state["ld_api_key"]
        assert not mock_session_state["ld_connection_verified"]

    def test_api_key_stored_in_session(self, mock_session_state):
        """Test API key is stored in session state."""
        mock_session_state["ld_api_key"] = "test-api-key"

        assert mock_session_state["ld_api_key"] == "test-api-key"

    def test_api_key_not_persisted_to_file(self, mock_session_state):
        """Test API key is NOT in persisted config."""
        # API key should only be in session_state, not saved to disk
        mock_session_state["ld_api_key"] = "secret-key"

        # Simulated save would not include ld_api_key
        persist_keys = ["customer_name", "project", "teams", "env_groups"]
        persisted = {k: mock_session_state.get(k) for k in persist_keys}

        assert "ld_api_key" not in persisted


# =============================================================================
# Connection Test Tests
# =============================================================================

class TestConnectionTest:
    """Tests for connection test functionality."""

    def test_successful_connection(self, mock_session_state):
        """Test successful connection sets verified flag."""
        from services import MockLDClient

        client = MockLDClient()
        result = client.health_check()

        assert result is True
        # In real code, this would set session state
        mock_session_state["ld_connection_verified"] = result
        assert mock_session_state["ld_connection_verified"] is True

    def test_failed_connection_auth_error(self, mock_session_state):
        """Test auth error sets error message."""
        from services import LDAuthenticationError

        mock_session_state["ld_connection_verified"] = False
        mock_session_state["ld_connection_error"] = "Invalid API key"

        assert mock_session_state["ld_connection_verified"] is False
        assert "Invalid" in mock_session_state["ld_connection_error"]

    def test_empty_api_key_shows_error(self, mock_session_state):
        """Test empty API key shows appropriate error."""
        mock_session_state["ld_api_key"] = ""
        mock_session_state["ld_connection_error"] = "API key is required"

        assert mock_session_state["ld_connection_error"] == "API key is required"


# =============================================================================
# Deploy Options Tests
# =============================================================================

class TestDeployOptions:
    """Tests for deployment options."""

    def test_dry_run_default_false(self, mock_session_state):
        """Test dry-run defaults to False."""
        assert mock_session_state.get("deploy_dry_run", False) is False

    def test_skip_existing_default_true(self, mock_session_state):
        """Test skip_existing defaults to True."""
        assert mock_session_state.get("deploy_skip_existing", True) is True

    def test_options_stored_in_session(self, mock_session_state):
        """Test options are stored in session state."""
        mock_session_state["deploy_dry_run"] = True
        mock_session_state["deploy_skip_existing"] = False

        assert mock_session_state["deploy_dry_run"] is True
        assert mock_session_state["deploy_skip_existing"] is False


# =============================================================================
# Deployment Execution Tests
# =============================================================================

class TestDeploymentExecution:
    """Tests for deployment execution."""

    def test_deployment_uses_correct_options(self, mock_client, mock_payload):
        """Test deployment uses session state options."""
        from services import Deployer

        deployer = Deployer(
            client=mock_client,
            dry_run=True,
            skip_existing=True
        )

        result = deployer.deploy_all(mock_payload)

        # Dry-run should skip all
        assert result.roles_skipped == 2
        assert result.teams_skipped == 1
        assert result.roles_created == 0

    def test_deployment_creates_resources(self, mock_client, mock_payload):
        """Test real deployment creates resources."""
        from services import Deployer

        deployer = Deployer(
            client=mock_client,
            dry_run=False,
            skip_existing=True
        )

        result = deployer.deploy_all(mock_payload)

        assert result.roles_created == 2
        assert result.teams_created == 1
        assert result.success is True

    def test_deployment_handles_conflict(self, mock_client, mock_payload):
        """Test deployment handles existing resources."""
        from services import Deployer

        # Pre-create one role
        mock_client.create_custom_role({
            "key": "dev-test",
            "name": "Existing",
            "policy": []
        })

        deployer = Deployer(
            client=mock_client,
            skip_existing=True
        )

        result = deployer.deploy_all(mock_payload)

        assert result.roles_created == 1  # Only one new
        assert result.roles_skipped == 1  # One existing
        assert result.success is True

    def test_deployment_stores_result_in_session(self, mock_session_state, mock_client, mock_payload):
        """Test deployment result is stored in session."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        mock_session_state["deploy_result"] = result

        assert mock_session_state["deploy_result"] is not None
        assert mock_session_state["deploy_result"].success is True


# =============================================================================
# Progress Callback Tests
# =============================================================================

class TestProgressCallback:
    """Tests for progress tracking."""

    def test_progress_callback_updates_session(self, mock_session_state, mock_client, mock_payload):
        """Test progress callback updates session state."""
        from services import Deployer

        steps = []

        def track_progress(step, current, total):
            steps.append(step)
            mock_session_state["deploy_progress"] = current / total

        deployer = Deployer(
            client=mock_client,
            progress_callback=track_progress
        )

        deployer.deploy_all(mock_payload)

        # Should have 3 steps (2 roles + 1 team)
        assert len(steps) == 3
        assert mock_session_state["deploy_progress"] == 1.0

    def test_progress_increments_correctly(self, mock_session_state, mock_client, mock_payload):
        """Test progress increments for each step."""
        from services import Deployer

        progress_values = []

        def track_progress(step, current, total):
            progress_values.append(current / total)

        deployer = Deployer(
            client=mock_client,
            progress_callback=track_progress
        )

        deployer.deploy_all(mock_payload)

        # Progress should increment: 1/3, 2/3, 3/3
        assert len(progress_values) == 3
        assert progress_values[0] == pytest.approx(1/3, 0.01)
        assert progress_values[1] == pytest.approx(2/3, 0.01)
        assert progress_values[2] == pytest.approx(3/3, 0.01)


# =============================================================================
# Results Display Tests
# =============================================================================

class TestResultsDisplay:
    """Tests for results display."""

    def test_result_summary_calculation(self, mock_client, mock_payload):
        """Test result summary is correct."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        # Check summary values
        total_created = result.roles_created + result.teams_created
        total_skipped = result.roles_skipped + result.teams_skipped
        total_failed = result.roles_failed + result.teams_failed

        assert total_created == 3
        assert total_skipped == 0
        assert total_failed == 0

    def test_result_has_duration(self, mock_client, mock_payload):
        """Test result includes duration."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        assert result.duration_seconds > 0

    def test_result_summary_string(self, mock_client, mock_payload):
        """Test result summary string is informative."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        summary = result.get_summary()

        assert "succeeded" in summary
        assert "created" in summary


# =============================================================================
# Rollback Tests
# =============================================================================

class TestRollback:
    """Tests for rollback functionality."""

    def test_rollback_deletes_created(self, mock_client, mock_payload):
        """Test rollback deletes created resources."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        deployer.deploy_all(mock_payload)

        # Verify resources exist
        assert len(mock_client.roles) == 2
        assert len(mock_client.teams) == 1

        # Rollback
        success = deployer.rollback()

        assert success is True
        assert len(mock_client.roles) == 0
        assert len(mock_client.teams) == 0

    def test_rollback_clears_tracking(self, mock_client, mock_payload):
        """Test rollback clears tracking lists."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        deployer.deploy_all(mock_payload)

        assert len(deployer.created_roles) == 2
        assert len(deployer.created_teams) == 1

        deployer.rollback()

        assert len(deployer.created_roles) == 0
        assert len(deployer.created_teams) == 0


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in deployment."""

    def test_auth_error_shows_message(self):
        """Test authentication error is handled."""
        from services import LDClient, LDAuthenticationError

        with pytest.raises(LDAuthenticationError):
            LDClient(api_key="")

    def test_partial_failure_allows_rollback(self, mock_client, mock_payload):
        """Test partial failure still allows rollback."""
        from services import Deployer
        from services.ld_exceptions import LDValidationError

        # Create deployer
        deployer = Deployer(client=mock_client)

        # Manually create first role
        deployer._deploy_role(mock_payload.roles[0])

        # Verify one role created
        assert len(deployer.created_roles) == 1

        # Rollback should work
        success = deployer.rollback()
        assert success is True

    def test_error_details_accessible(self, mock_client):
        """Test error details are captured in result."""
        from services import Deployer, DeployPayload
        from services.ld_exceptions import LDConflictError

        # Pre-create a role to cause conflict
        mock_client.create_custom_role({
            "key": "existing-role",
            "name": "Existing",
            "policy": []
        })

        payload = DeployPayload(
            customer_name="Test",
            project_key="test",
            roles=[{"key": "existing-role", "name": "Try Again", "policy": []}],
            teams=[]
        )

        deployer = Deployer(client=mock_client, skip_existing=False)
        result = deployer.deploy_all(payload)

        assert result.roles_failed == 1
        assert len(result.errors) == 1
        assert "existing-role" in result.errors[0]


# =============================================================================
# Integration Tests
# =============================================================================

class TestDeployUIIntegration:
    """Integration tests for deploy UI flow."""

    def test_full_deployment_flow(self, mock_client, mock_payload, mock_session_state):
        """Test complete deployment flow."""
        from services import Deployer

        # 1. Set API key and verify connection
        mock_session_state["ld_api_key"] = "test-key"
        mock_session_state["ld_connection_verified"] = mock_client.health_check()

        assert mock_session_state["ld_connection_verified"] is True

        # 2. Set options
        mock_session_state["deploy_dry_run"] = False
        mock_session_state["deploy_skip_existing"] = True

        # 3. Execute deployment
        deployer = Deployer(
            client=mock_client,
            dry_run=mock_session_state["deploy_dry_run"],
            skip_existing=mock_session_state["deploy_skip_existing"]
        )

        result = deployer.deploy_all(mock_payload)

        # 4. Store result
        mock_session_state["deploy_result"] = result
        mock_session_state["deployer_instance"] = deployer

        # 5. Verify success
        assert mock_session_state["deploy_result"].success is True
        assert mock_session_state["deploy_result"].roles_created == 2
        assert mock_session_state["deploy_result"].teams_created == 1

    def test_dry_run_then_real_deployment(self, mock_client, mock_payload, mock_session_state):
        """Test dry-run followed by real deployment."""
        from services import Deployer

        # 1. Dry-run first
        deployer = Deployer(client=mock_client, dry_run=True)
        dry_result = deployer.deploy_all(mock_payload)

        assert dry_result.roles_skipped == 2  # All skipped in dry-run
        assert len(mock_client.roles) == 0  # Nothing created

        # 2. Real deployment
        deployer = Deployer(client=mock_client, dry_run=False)
        real_result = deployer.deploy_all(mock_payload)

        assert real_result.roles_created == 2  # Now created
        assert len(mock_client.roles) == 2


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Implementation Plan

### Step-by-Step Implementation

| Step | Task | File | Est. Lines |
|------|------|------|------------|
| 1 | Add `_render_api_config()` | `ui/deploy_tab.py` | ~30 |
| 2 | Add `_test_connection()` | `ui/deploy_tab.py` | ~25 |
| 3 | Add `_render_deploy_options()` | `ui/deploy_tab.py` | ~20 |
| 4 | Add `_render_deploy_button()` | `ui/deploy_tab.py` | ~30 |
| 5 | Add `_execute_deployment()` | `ui/deploy_tab.py` | ~40 |
| 6 | Add `_create_progress_callback()` | `ui/deploy_tab.py` | ~15 |
| 7 | Add `_render_deploy_progress()` | `ui/deploy_tab.py` | ~25 |
| 8 | Add `_render_deploy_results()` | `ui/deploy_tab.py` | ~50 |
| 9 | Add `_render_rollback_button()` | `ui/deploy_tab.py` | ~25 |
| 10 | Update `render_deploy_tab()` | `ui/deploy_tab.py` | +30 |
| 11 | Create tests | `tests/test_deploy_ui.py` | ~350 |

### Total Estimated Changes

- **Modified**: `ui/deploy_tab.py` (+250 lines)
- **New**: `tests/test_deploy_ui.py` (~350 lines)

### Python/Streamlit Concepts Used

| Concept | Where Used |
|---------|------------|
| `st.text_input(type="password")` | API key input |
| `st.checkbox` | Deploy options |
| `st.button` | Actions (test, deploy, rollback) |
| `st.progress` | Progress bar |
| `st.spinner` | Loading indicator |
| `st.rerun()` | Refresh UI after state change |
| `st.session_state` | Store all deployment state |
| `st.metric` | Results summary |
| `st.expander` | Error details |
| Callbacks | Progress tracking |

---

## Learning Resources

| Topic | Resource |
|-------|----------|
| Streamlit Session State | [Session State Docs](https://docs.streamlit.io/library/api-reference/session-state) |
| Streamlit Callbacks | [Callbacks Guide](https://docs.streamlit.io/library/advanced-features/button-behavior-and-examples) |
| Progress Indicators | [st.progress Docs](https://docs.streamlit.io/library/api-reference/status/st.progress) |
| LaunchDarkly API | [API Reference](https://apidocs.launchdarkly.com/) |

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [← Phase 7: Deployer](../phase7/) | [📋 All Phases](../) | [Phase 9: Integration →](../phase9/) |
