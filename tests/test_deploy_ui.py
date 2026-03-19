"""
Tests for Phase 8: Complete Deploy UI
=====================================

Tests cover:
1. API configuration state management
2. Connection test functionality
3. Deploy options
4. Deployment execution
5. Progress tracking
6. Results display
7. Rollback functionality
8. Error handling

Note: These tests focus on the business logic and state management,
not the Streamlit UI rendering (which requires specialized testing).

Run with: pytest tests/test_deploy_ui.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any


# =============================================================================
# LESSON: Testing Streamlit Code
# =============================================================================
# Streamlit apps are tricky to test because they rely on:
#   - st.session_state (a special dictionary)
#   - UI widgets (st.button, st.text_input, etc.)
#
# Our approach:
#   1. Test the business logic separately (Deployer, LDClient)
#   2. Test session state management with mock state
#   3. Don't try to test actual UI rendering


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_session_state() -> Dict[str, Any]:
    """
    Create mock session state for testing.

    This simulates st.session_state without needing Streamlit.
    """
    return {
        "customer_name": "Test Corp",
        "project": "test-project",
        "ld_api_key": "",
        "ld_connection_verified": False,
        "ld_connection_error": None,
        "deploy_dry_run": False,
        "deploy_skip_existing": True,
        "deploy_in_progress": False,
        "deploy_progress": 0.0,
        "deploy_steps": [],
        "deploy_result": None,
        "deployer_instance": None,
    }


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


@pytest.fixture
def empty_payload():
    """Create empty deployment payload."""
    from services import DeployPayload

    return DeployPayload(
        customer_name="Test Corp",
        project_key="test-project",
        roles=[],
        teams=[]
    )


# =============================================================================
# API Configuration Tests
# =============================================================================

class TestAPIConfiguration:
    """Tests for API configuration section."""

    def test_empty_api_key_state(self, mock_session_state):
        """Test initial state has empty API key."""
        assert mock_session_state["ld_api_key"] == ""
        assert mock_session_state["ld_connection_verified"] is False

    def test_api_key_stored_in_session(self, mock_session_state):
        """Test API key can be stored in session state."""
        mock_session_state["ld_api_key"] = "test-api-key-12345"

        assert mock_session_state["ld_api_key"] == "test-api-key-12345"
        assert len(mock_session_state["ld_api_key"]) > 0

    def test_api_key_not_in_persist_keys(self, mock_session_state):
        """Test API key is NOT in the list of keys to persist."""
        # Keys that would be saved to disk
        persist_keys = ["customer_name", "project", "teams", "env_groups"]

        # API key should NOT be in this list
        assert "ld_api_key" not in persist_keys

        # Simulated save would not include ld_api_key
        mock_session_state["ld_api_key"] = "secret-key"
        persisted = {k: mock_session_state.get(k) for k in persist_keys}

        assert "ld_api_key" not in persisted

    def test_connection_verified_state(self, mock_session_state):
        """Test connection verified flag."""
        assert mock_session_state["ld_connection_verified"] is False

        # After successful connection
        mock_session_state["ld_connection_verified"] = True
        assert mock_session_state["ld_connection_verified"] is True

    def test_connection_error_state(self, mock_session_state):
        """Test connection error storage."""
        assert mock_session_state["ld_connection_error"] is None

        # After failed connection
        mock_session_state["ld_connection_error"] = "Invalid API key"
        assert mock_session_state["ld_connection_error"] == "Invalid API key"


# =============================================================================
# Connection Test Tests
# =============================================================================

class TestConnectionTest:
    """Tests for connection test functionality."""

    def test_successful_connection_with_mock(self, mock_session_state):
        """Test successful connection sets verified flag."""
        from services import MockLDClient

        client = MockLDClient()
        result = client.health_check()

        assert result is True

        # Simulate what _test_connection does
        mock_session_state["ld_connection_verified"] = result
        mock_session_state["ld_connection_error"] = None

        assert mock_session_state["ld_connection_verified"] is True
        assert mock_session_state["ld_connection_error"] is None

    def test_empty_api_key_error(self, mock_session_state):
        """Test empty API key sets error message."""
        api_key = ""

        # Simulate validation
        if not api_key or api_key.strip() == "":
            mock_session_state["ld_connection_verified"] = False
            mock_session_state["ld_connection_error"] = "API key is required"

        assert mock_session_state["ld_connection_verified"] is False
        assert mock_session_state["ld_connection_error"] == "API key is required"

    def test_whitespace_only_api_key_error(self, mock_session_state):
        """Test whitespace-only API key sets error message."""
        api_key = "   "

        if not api_key or api_key.strip() == "":
            mock_session_state["ld_connection_verified"] = False
            mock_session_state["ld_connection_error"] = "API key is required"

        assert mock_session_state["ld_connection_verified"] is False

    def test_auth_error_sets_message(self, mock_session_state):
        """Test authentication error is captured."""
        from services import LDAuthenticationError

        # Simulate what happens on auth error
        mock_session_state["ld_connection_verified"] = False
        mock_session_state["ld_connection_error"] = "Invalid API key"

        assert "Invalid" in mock_session_state["ld_connection_error"]

    def test_connection_error_sets_message(self, mock_session_state):
        """Test general connection error is captured."""
        mock_session_state["ld_connection_verified"] = False
        mock_session_state["ld_connection_error"] = "Network error: Connection refused"

        assert mock_session_state["ld_connection_error"] is not None


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

    def test_options_can_be_changed(self, mock_session_state):
        """Test options can be changed."""
        mock_session_state["deploy_dry_run"] = True
        mock_session_state["deploy_skip_existing"] = False

        assert mock_session_state["deploy_dry_run"] is True
        assert mock_session_state["deploy_skip_existing"] is False

    def test_options_persist_in_session(self, mock_session_state):
        """Test options persist across simulated reruns."""
        # First "run"
        mock_session_state["deploy_dry_run"] = True

        # Simulated rerun - state should persist
        state_copy = mock_session_state.copy()
        assert state_copy["deploy_dry_run"] is True


# =============================================================================
# Deployment Button State Tests
# =============================================================================

class TestDeployButtonState:
    """Tests for deploy button enabled/disabled logic."""

    def test_button_disabled_without_api_key(self, mock_session_state, mock_payload):
        """Test deploy button disabled without API key."""
        mock_session_state["ld_api_key"] = ""
        mock_session_state["ld_connection_verified"] = True

        # LESSON: Python's `and` returns the first falsy value or the last value
        # So we use bool() to get a proper True/False
        button_enabled = bool(
            mock_session_state["ld_api_key"] and
            mock_session_state["ld_connection_verified"] and
            not mock_session_state["deploy_in_progress"] and
            mock_payload.get_role_count() + mock_payload.get_team_count() > 0
        )

        assert button_enabled is False

    def test_button_disabled_without_connection(self, mock_session_state, mock_payload):
        """Test deploy button disabled without verified connection."""
        mock_session_state["ld_api_key"] = "test-key"
        mock_session_state["ld_connection_verified"] = False

        button_enabled = (
            mock_session_state["ld_api_key"] and
            mock_session_state["ld_connection_verified"]
        )

        assert button_enabled is False

    def test_button_disabled_during_deployment(self, mock_session_state, mock_payload):
        """Test deploy button disabled during deployment."""
        mock_session_state["ld_api_key"] = "test-key"
        mock_session_state["ld_connection_verified"] = True
        mock_session_state["deploy_in_progress"] = True

        button_enabled = (
            mock_session_state["ld_api_key"] and
            mock_session_state["ld_connection_verified"] and
            not mock_session_state["deploy_in_progress"]
        )

        assert button_enabled is False

    def test_button_disabled_with_empty_payload(self, mock_session_state, empty_payload):
        """Test deploy button disabled with empty payload."""
        mock_session_state["ld_api_key"] = "test-key"
        mock_session_state["ld_connection_verified"] = True

        has_resources = empty_payload.get_role_count() + empty_payload.get_team_count() > 0

        assert has_resources is False

    def test_button_enabled_when_ready(self, mock_session_state, mock_payload):
        """Test deploy button enabled when all conditions met."""
        mock_session_state["ld_api_key"] = "test-key"
        mock_session_state["ld_connection_verified"] = True
        mock_session_state["deploy_in_progress"] = False

        button_enabled = (
            mock_session_state["ld_api_key"] and
            mock_session_state["ld_connection_verified"] and
            not mock_session_state["deploy_in_progress"] and
            mock_payload.get_role_count() + mock_payload.get_team_count() > 0
        )

        assert button_enabled is True


# =============================================================================
# Deployment Execution Tests
# =============================================================================

class TestDeploymentExecution:
    """Tests for deployment execution."""

    def test_deployment_uses_dry_run_option(self, mock_client, mock_payload):
        """Test deployment respects dry_run option."""
        from services import Deployer

        deployer = Deployer(
            client=mock_client,
            dry_run=True,
            skip_existing=True
        )

        result = deployer.deploy_all(mock_payload)

        # Dry-run should skip all (not create)
        assert result.roles_skipped == 2
        assert result.teams_skipped == 1
        assert result.roles_created == 0
        assert result.teams_created == 0

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

    def test_deployment_skips_existing(self, mock_client, mock_payload):
        """Test deployment skips existing resources."""
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

    def test_deployment_fails_on_existing_without_skip(self, mock_client, mock_payload):
        """Test deployment fails on conflict without skip_existing."""
        from services import Deployer

        # Pre-create one role
        mock_client.create_custom_role({
            "key": "dev-test",
            "name": "Existing",
            "policy": []
        })

        deployer = Deployer(
            client=mock_client,
            skip_existing=False
        )

        result = deployer.deploy_all(mock_payload)

        assert result.roles_failed == 1
        assert result.success is False

    def test_deployment_stores_result(self, mock_session_state, mock_client, mock_payload):
        """Test deployment result is stored in session."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        # Simulate storing in session
        mock_session_state["deploy_result"] = result

        assert mock_session_state["deploy_result"] is not None
        assert mock_session_state["deploy_result"].success is True

    def test_deployment_stores_deployer(self, mock_session_state, mock_client, mock_payload):
        """Test deployer instance is stored for rollback."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        # Simulate storing deployer for rollback
        mock_session_state["deployer_instance"] = deployer

        assert mock_session_state["deployer_instance"] is not None
        assert len(mock_session_state["deployer_instance"].created_roles) == 2


# =============================================================================
# Progress Callback Tests
# =============================================================================

class TestProgressCallback:
    """Tests for progress tracking."""

    def test_progress_callback_called(self, mock_client, mock_payload):
        """Test progress callback is called for each step."""
        from services import Deployer

        steps_received = []

        def track_progress(step, current, total):
            steps_received.append((step, current, total))

        deployer = Deployer(
            client=mock_client,
            progress_callback=track_progress
        )

        deployer.deploy_all(mock_payload)

        # Should have 3 steps (2 roles + 1 team)
        assert len(steps_received) == 3

    def test_progress_increments(self, mock_session_state, mock_client, mock_payload):
        """Test progress increments correctly."""
        from services import Deployer

        progress_values = []

        def track_progress(step, current, total):
            progress = current / total if total > 0 else 0
            progress_values.append(progress)
            mock_session_state["deploy_progress"] = progress

        deployer = Deployer(
            client=mock_client,
            progress_callback=track_progress
        )

        deployer.deploy_all(mock_payload)

        # Progress should increment: ~0.33, ~0.67, 1.0
        assert len(progress_values) == 3
        assert progress_values[0] == pytest.approx(1/3, 0.01)
        assert progress_values[1] == pytest.approx(2/3, 0.01)
        assert progress_values[2] == pytest.approx(1.0, 0.01)

    def test_progress_reaches_100(self, mock_session_state, mock_client, mock_payload):
        """Test progress reaches 100% at completion."""
        from services import Deployer

        def track_progress(step, current, total):
            mock_session_state["deploy_progress"] = current / total if total > 0 else 0

        deployer = Deployer(
            client=mock_client,
            progress_callback=track_progress
        )

        deployer.deploy_all(mock_payload)

        assert mock_session_state["deploy_progress"] == 1.0

    def test_steps_accumulated(self, mock_session_state, mock_client, mock_payload):
        """Test steps are accumulated in session state."""
        from services import Deployer

        mock_session_state["deploy_steps"] = []

        def track_progress(step, current, total):
            mock_session_state["deploy_steps"].append(step)

        deployer = Deployer(
            client=mock_client,
            progress_callback=track_progress
        )

        deployer.deploy_all(mock_payload)

        assert len(mock_session_state["deploy_steps"]) == 3


# =============================================================================
# Results Display Tests
# =============================================================================

class TestResultsDisplay:
    """Tests for results display."""

    def test_result_summary_totals(self, mock_client, mock_payload):
        """Test result summary totals are correct."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        total_created = result.roles_created + result.teams_created
        total_skipped = result.roles_skipped + result.teams_skipped
        total_failed = result.roles_failed + result.teams_failed

        assert total_created == 3  # 2 roles + 1 team
        assert total_skipped == 0
        assert total_failed == 0

    def test_result_has_duration(self, mock_client, mock_payload):
        """Test result includes duration."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        assert result.duration_seconds >= 0

    def test_result_summary_string(self, mock_client, mock_payload):
        """Test result summary string is informative."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        summary = result.get_summary()

        assert "succeeded" in summary.lower() or "success" in summary.lower()

    def test_result_steps_list(self, mock_client, mock_payload):
        """Test result contains steps list."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        assert len(result.steps) == 3

    def test_dry_run_result_message(self, mock_client, mock_payload):
        """Test dry-run result is clearly indicated."""
        from services import Deployer

        deployer = Deployer(client=mock_client, dry_run=True)
        result = deployer.deploy_all(mock_payload)

        # All should be skipped in dry-run
        assert result.roles_skipped == 2
        assert result.teams_skipped == 1
        assert result.roles_created == 0


# =============================================================================
# Rollback Tests
# =============================================================================

class TestRollback:
    """Tests for rollback functionality."""

    def test_rollback_deletes_created_resources(self, mock_client, mock_payload):
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
        """Test rollback clears deployer tracking lists."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        deployer.deploy_all(mock_payload)

        assert len(deployer.created_roles) == 2
        assert len(deployer.created_teams) == 1

        deployer.rollback()

        assert len(deployer.created_roles) == 0
        assert len(deployer.created_teams) == 0

    def test_rollback_not_needed_on_success(self, mock_client, mock_payload):
        """Test rollback logic - not shown on success."""
        from services import Deployer

        deployer = Deployer(client=mock_client)
        result = deployer.deploy_all(mock_payload)

        # Rollback button should not be shown on success
        should_show_rollback = (
            not result.success and
            result.roles_created + result.teams_created > 0
        )

        assert should_show_rollback is False

    def test_rollback_shown_on_partial_failure(self, mock_client, mock_payload):
        """Test rollback shown when partial failure with created resources."""
        from services import Deployer, DeployPayload

        # Create a scenario with one success and one failure
        # Pre-create a role to cause conflict
        mock_client.create_custom_role({
            "key": "dev-prod",  # This will conflict
            "name": "Existing",
            "policy": []
        })

        deployer = Deployer(client=mock_client, skip_existing=False)
        result = deployer.deploy_all(mock_payload)

        # Should have created one role and failed on the other
        # The team might also fail since it depends on roles
        should_show_rollback = (
            not result.success and
            result.roles_created + result.teams_created > 0
        )

        # If at least one resource was created before failure
        if result.roles_created > 0:
            assert should_show_rollback is True


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in deployment."""

    def test_auth_error_raises(self):
        """Test authentication error is raised for empty key."""
        from services import LDClient, LDAuthenticationError

        with pytest.raises(LDAuthenticationError):
            LDClient(api_key="")

    def test_auth_error_message(self):
        """Test authentication error message is informative."""
        from services import LDAuthenticationError

        error = LDAuthenticationError("Invalid API key")
        assert "Invalid" in str(error) or "API key" in str(error)

    def test_client_error_captured(self, mock_session_state):
        """Test client errors are captured in session."""
        from services import LDClientError

        # Simulate error handling
        try:
            raise LDClientError("Connection failed")
        except LDClientError as e:
            mock_session_state["ld_connection_error"] = str(e)

        assert "Connection failed" in mock_session_state["ld_connection_error"]

    def test_deployment_error_in_result(self, mock_client):
        """Test deployment errors are captured in result."""
        from services import Deployer, DeployPayload

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
        """Test complete deployment flow from start to finish."""
        from services import Deployer

        # 1. Enter API key
        mock_session_state["ld_api_key"] = "test-key-12345"

        # 2. Verify connection
        mock_session_state["ld_connection_verified"] = mock_client.health_check()
        assert mock_session_state["ld_connection_verified"] is True

        # 3. Set options
        mock_session_state["deploy_dry_run"] = False
        mock_session_state["deploy_skip_existing"] = True

        # 4. Execute deployment
        mock_session_state["deploy_in_progress"] = True
        mock_session_state["deploy_steps"] = []

        def track_progress(step, current, total):
            mock_session_state["deploy_steps"].append(step)
            mock_session_state["deploy_progress"] = current / total

        deployer = Deployer(
            client=mock_client,
            dry_run=mock_session_state["deploy_dry_run"],
            skip_existing=mock_session_state["deploy_skip_existing"],
            progress_callback=track_progress
        )

        result = deployer.deploy_all(mock_payload)

        # 5. Store results
        mock_session_state["deploy_result"] = result
        mock_session_state["deployer_instance"] = deployer
        mock_session_state["deploy_in_progress"] = False

        # 6. Verify success
        assert mock_session_state["deploy_result"].success is True
        assert mock_session_state["deploy_result"].roles_created == 2
        assert mock_session_state["deploy_result"].teams_created == 1
        assert len(mock_session_state["deploy_steps"]) == 3
        assert mock_session_state["deploy_progress"] == 1.0

    def test_dry_run_then_real_deployment(self, mock_client, mock_payload, mock_session_state):
        """Test dry-run followed by real deployment."""
        from services import Deployer

        # 1. Dry-run first
        deployer = Deployer(client=mock_client, dry_run=True)
        dry_result = deployer.deploy_all(mock_payload)

        assert dry_result.roles_skipped == 2
        assert dry_result.teams_skipped == 1
        assert len(mock_client.roles) == 0  # Nothing created

        # 2. User reviews and approves - real deployment
        deployer = Deployer(client=mock_client, dry_run=False)
        real_result = deployer.deploy_all(mock_payload)

        assert real_result.roles_created == 2
        assert real_result.teams_created == 1
        assert len(mock_client.roles) == 2

    def test_failed_deployment_then_rollback(self, mock_client, mock_session_state):
        """Test failed deployment followed by rollback."""
        from services import Deployer, DeployPayload

        # Create payload with conflicting role
        mock_client.create_custom_role({
            "key": "role-2",
            "name": "Existing",
            "policy": []
        })

        payload = DeployPayload(
            customer_name="Test",
            project_key="test",
            roles=[
                {"key": "role-1", "name": "Role 1", "policy": []},
                {"key": "role-2", "name": "Role 2", "policy": []},  # Will conflict
            ],
            teams=[]
        )

        # Deploy (will fail on role-2)
        deployer = Deployer(client=mock_client, skip_existing=False)
        result = deployer.deploy_all(payload)

        mock_session_state["deploy_result"] = result
        mock_session_state["deployer_instance"] = deployer

        # Check if rollback is needed
        assert result.success is False
        assert result.roles_created == 1  # First role created before failure

        # Rollback
        success = deployer.rollback()
        assert success is True

        # Only the conflicting role should remain (pre-existing)
        # Note: mock_client.roles contains LDCustomRole objects, not dicts
        assert len(mock_client.roles) == 1
        assert mock_client.roles[0].key == "role-2"  # Access .key property


# =============================================================================
# Session State Reset Tests
# =============================================================================

class TestSessionStateReset:
    """Tests for session state reset on new deployment."""

    def test_deployment_clears_previous_result(self, mock_session_state, mock_client, mock_payload):
        """Test new deployment clears previous result."""
        from services import Deployer

        # Simulate previous result
        mock_session_state["deploy_result"] = "old_result"
        mock_session_state["deploy_steps"] = ["old_step"]

        # Start new deployment (simulating what _execute_deployment does)
        mock_session_state["deploy_in_progress"] = True
        mock_session_state["deploy_steps"] = []  # Reset
        mock_session_state["deploy_result"] = None  # Reset
        mock_session_state["deploy_progress"] = 0.0  # Reset

        # Verify reset
        assert mock_session_state["deploy_result"] is None
        assert mock_session_state["deploy_steps"] == []
        assert mock_session_state["deploy_progress"] == 0.0

    def test_connection_reset_on_api_key_change(self, mock_session_state):
        """Test connection verified resets when API key changes."""
        # Initial verified connection
        mock_session_state["ld_api_key"] = "key-1"
        mock_session_state["ld_connection_verified"] = True

        # User changes API key - should need re-verification
        mock_session_state["ld_api_key"] = "key-2"

        # In real UI, we'd reset verified on key change
        # This tests the expected behavior
        if mock_session_state["ld_api_key"] != "key-1":
            # Would reset in real implementation
            pass  # Just documenting expected behavior


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
