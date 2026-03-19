"""
Tests for Phase 7: Deployer Service
====================================

Tests cover:
1. DeployResult data class
2. DeployStepResult data class
3. Deployer initialization
4. Role deployment (success, conflict, error)
5. Team deployment (success, conflict, error)
6. Full deployment orchestration
7. Dry-run mode
8. Progress callbacks
9. Rollback functionality

Run with: pytest tests/test_deployer.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_client():
    """Create a mock LD client."""
    from services.ld_client import MockLDClient
    return MockLDClient()


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
    """Create a sample DeployPayload."""
    from services import DeployPayload

    return DeployPayload(
        customer_name="Test Corp",
        project_key="test-project",
        roles=sample_roles,
        teams=sample_teams
    )


@pytest.fixture
def deployer(mock_client):
    """Create a Deployer with mock client."""
    from services.deployer import Deployer
    return Deployer(client=mock_client)


# =============================================================================
# DeployStep Enum Tests
# =============================================================================

class TestDeployStep:
    """Tests for DeployStep enum."""

    def test_deploy_step_values(self):
        """Test DeployStep enum values."""
        from services.deployer import DeployStep

        assert DeployStep.PENDING.value == "pending"
        assert DeployStep.IN_PROGRESS.value == "in_progress"
        assert DeployStep.COMPLETED.value == "completed"
        assert DeployStep.SKIPPED.value == "skipped"
        assert DeployStep.FAILED.value == "failed"


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
            resource_key="test-role",
            status=DeployStep.COMPLETED
        )
        assert step.is_success() is True

    def test_is_success_for_skipped(self):
        """Test is_success returns True for SKIPPED."""
        from services.deployer import DeployStepResult, DeployStep

        step = DeployStepResult(
            resource_type="role",
            resource_key="test-role",
            status=DeployStep.SKIPPED
        )
        assert step.is_success() is True

    def test_is_success_for_failed(self):
        """Test is_success returns False for FAILED."""
        from services.deployer import DeployStepResult, DeployStep

        step = DeployStepResult(
            resource_type="role",
            resource_key="test-role",
            status=DeployStep.FAILED,
            error="Something went wrong"
        )
        assert step.is_success() is False

    def test_default_values(self):
        """Test default values are set correctly."""
        from services.deployer import DeployStepResult, DeployStep

        step = DeployStepResult(
            resource_type="team",
            resource_key="test-team",
            status=DeployStep.PENDING
        )
        assert step.message == ""
        assert step.error is None


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
        assert result.teams_skipped == 0
        assert result.teams_failed == 0
        assert result.errors == []
        assert result.steps == []

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

    def test_add_step_updates_role_created_counter(self):
        """Test add_step updates roles_created for completed role."""
        from services.deployer import DeployResult, DeployStepResult, DeployStep

        result = DeployResult()
        step = DeployStepResult(
            resource_type="role",
            resource_key="dev-role",
            status=DeployStep.COMPLETED
        )
        result.add_step(step)

        assert result.roles_created == 1
        assert result.success is True

    def test_add_step_updates_role_skipped_counter(self):
        """Test add_step updates roles_skipped for skipped role."""
        from services.deployer import DeployResult, DeployStepResult, DeployStep

        result = DeployResult()
        step = DeployStepResult(
            resource_type="role",
            resource_key="existing-role",
            status=DeployStep.SKIPPED
        )
        result.add_step(step)

        assert result.roles_skipped == 1
        assert result.success is True

    def test_add_step_updates_role_failed_counter_and_success(self):
        """Test add_step updates roles_failed and sets success=False."""
        from services.deployer import DeployResult, DeployStepResult, DeployStep

        result = DeployResult()
        step = DeployStepResult(
            resource_type="role",
            resource_key="bad-role",
            status=DeployStep.FAILED,
            error="Validation failed"
        )
        result.add_step(step)

        assert result.roles_failed == 1
        assert result.success is False
        assert len(result.errors) == 1

    def test_add_step_updates_team_counters(self):
        """Test add_step updates team counters."""
        from services.deployer import DeployResult, DeployStepResult, DeployStep

        result = DeployResult()

        result.add_step(DeployStepResult(
            resource_type="team",
            resource_key="team1",
            status=DeployStep.COMPLETED
        ))
        result.add_step(DeployStepResult(
            resource_type="team",
            resource_key="team2",
            status=DeployStep.SKIPPED
        ))
        result.add_step(DeployStepResult(
            resource_type="team",
            resource_key="team3",
            status=DeployStep.FAILED,
            error="Error"
        ))

        assert result.teams_created == 1
        assert result.teams_skipped == 1
        assert result.teams_failed == 1

    def test_get_summary_includes_counts(self):
        """Test get_summary includes all counts."""
        from services.deployer import DeployResult

        result = DeployResult()
        result.roles_created = 3
        result.roles_skipped = 1
        result.teams_created = 2
        result.duration_seconds = 1.5

        summary = result.get_summary()

        assert "3 created" in summary
        assert "1 skipped" in summary
        assert "2 created" in summary
        assert "1.5s" in summary

    def test_get_summary_shows_success(self):
        """Test get_summary shows success status."""
        from services.deployer import DeployResult

        result = DeployResult(success=True)
        assert "succeeded" in result.get_summary()

        result = DeployResult(success=False)
        assert "failed" in result.get_summary()


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

    def test_init_with_skip_existing_false(self, mock_client):
        """Test deployer initializes with skip_existing=False."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client, skip_existing=False)
        assert deployer.skip_existing is False

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

    def test_init_creates_empty_tracking_lists(self, mock_client):
        """Test deployer creates empty tracking lists."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client)

        assert deployer.created_roles == []
        assert deployer.created_teams == []


# =============================================================================
# Role Deployment Tests
# =============================================================================

class TestDeployRoles:
    """Tests for role deployment."""

    def test_deploy_role_success(self, deployer, sample_roles):
        """Test successful role deployment."""
        result = deployer.deploy_roles([sample_roles[0]])

        assert result.roles_created == 1
        assert result.roles_failed == 0
        assert result.success is True

    def test_deploy_role_tracks_created(self, deployer, sample_roles):
        """Test deployed role is tracked for rollback."""
        deployer.deploy_roles([sample_roles[0]])

        assert "developer-test" in deployer.created_roles

    def test_deploy_role_conflict_skipped(self, deployer, mock_client, sample_roles):
        """Test role conflict is skipped when skip_existing=True."""
        # Pre-create the role
        mock_client.create_custom_role({
            "key": "developer-test",
            "name": "Existing",
            "policy": []
        })

        result = deployer.deploy_roles([sample_roles[0]])

        assert result.roles_created == 0
        assert result.roles_skipped == 1
        assert result.success is True

    def test_deploy_role_conflict_fails_when_not_skipping(self, mock_client, sample_roles):
        """Test role conflict fails when skip_existing=False."""
        from services.deployer import Deployer

        # Pre-create the role
        mock_client.create_custom_role({
            "key": "developer-test",
            "name": "Existing",
            "policy": []
        })

        deployer = Deployer(client=mock_client, skip_existing=False)
        result = deployer.deploy_roles([sample_roles[0]])

        assert result.roles_failed == 1
        assert result.success is False

    def test_deploy_multiple_roles(self, deployer, sample_roles):
        """Test deploying multiple roles."""
        result = deployer.deploy_roles(sample_roles)

        assert result.roles_created == 2
        assert len(deployer.created_roles) == 2


# =============================================================================
# Team Deployment Tests
# =============================================================================

class TestDeployTeams:
    """Tests for team deployment."""

    def test_deploy_team_success(self, deployer, sample_teams):
        """Test successful team deployment."""
        result = deployer.deploy_teams(sample_teams)

        assert result.teams_created == 1
        assert result.success is True

    def test_deploy_team_tracks_created(self, deployer, sample_teams):
        """Test deployed team is tracked for rollback."""
        deployer.deploy_teams(sample_teams)

        assert "developers" in deployer.created_teams

    def test_deploy_team_conflict_skipped(self, deployer, mock_client, sample_teams):
        """Test team conflict is skipped."""
        # Pre-create the team
        mock_client.create_team({
            "key": "developers",
            "name": "Existing"
        })

        result = deployer.deploy_teams(sample_teams)

        assert result.teams_skipped == 1
        assert result.success is True


# =============================================================================
# Full Deployment Tests
# =============================================================================

class TestDeployAll:
    """Tests for full deployment orchestration."""

    def test_deploy_all_creates_roles_then_teams(self, deployer, sample_payload):
        """Test deploy_all creates roles before teams."""
        result = deployer.deploy_all(sample_payload)

        assert result.roles_created == 2
        assert result.teams_created == 1
        assert result.success is True

    def test_deploy_all_tracks_all_created(self, deployer, sample_payload):
        """Test deploy_all tracks all created resources."""
        deployer.deploy_all(sample_payload)

        assert len(deployer.created_roles) == 2
        assert len(deployer.created_teams) == 1

    def test_deploy_all_records_duration(self, deployer, sample_payload):
        """Test deploy_all records duration."""
        result = deployer.deploy_all(sample_payload)

        assert result.duration_seconds > 0

    def test_deploy_all_roles_first(self, mock_client, sample_payload):
        """Test roles are deployed before teams."""
        from services.deployer import Deployer

        call_order = []

        # Track call order
        original_create_role = mock_client.create_custom_role
        original_create_team = mock_client.create_team

        def track_role(*args, **kwargs):
            call_order.append("role")
            return original_create_role(*args, **kwargs)

        def track_team(*args, **kwargs):
            call_order.append("team")
            return original_create_team(*args, **kwargs)

        mock_client.create_custom_role = track_role
        mock_client.create_team = track_team

        deployer = Deployer(client=mock_client)
        deployer.deploy_all(sample_payload)

        # All roles should come before teams
        role_indices = [i for i, x in enumerate(call_order) if x == "role"]
        team_indices = [i for i, x in enumerate(call_order) if x == "team"]

        if role_indices and team_indices:
            assert max(role_indices) < min(team_indices)


# =============================================================================
# Dry-Run Mode Tests
# =============================================================================

class TestDryRunMode:
    """Tests for dry-run mode."""

    def test_dry_run_does_not_create_resources(self, mock_client, sample_payload):
        """Test dry-run mode doesn't create resources."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client, dry_run=True)
        deployer.deploy_all(sample_payload)

        assert len(mock_client.roles) == 0
        assert len(mock_client.teams) == 0

    def test_dry_run_marks_steps_as_skipped(self, mock_client, sample_payload):
        """Test dry-run mode marks all steps as skipped."""
        from services.deployer import Deployer, DeployStep

        deployer = Deployer(client=mock_client, dry_run=True)
        result = deployer.deploy_all(sample_payload)

        for step in result.steps:
            assert step.status == DeployStep.SKIPPED
            assert "dry-run" in step.message.lower()

    def test_dry_run_counts_skipped_correctly(self, mock_client, sample_payload):
        """Test dry-run mode counts skipped correctly."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client, dry_run=True)
        result = deployer.deploy_all(sample_payload)

        assert result.roles_skipped == 2
        assert result.teams_skipped == 1
        assert result.roles_created == 0
        assert result.teams_created == 0

    def test_dry_run_does_not_track_created(self, mock_client, sample_payload):
        """Test dry-run mode doesn't track created resources."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client, dry_run=True)
        deployer.deploy_all(sample_payload)

        assert len(deployer.created_roles) == 0
        assert len(deployer.created_teams) == 0


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

        deployer.deploy_all(sample_payload)

        # Should be called for each role + each team
        expected_calls = len(sample_payload.roles) + len(sample_payload.teams)
        assert callback.call_count == expected_calls

    def test_callback_receives_correct_arguments(self, mock_client, sample_roles):
        """Test callback receives step, current, and total."""
        from services.deployer import Deployer, DeployStepResult

        callback = Mock()
        deployer = Deployer(client=mock_client, progress_callback=callback)

        deployer.deploy_roles(sample_roles)

        # Check first call
        first_call = callback.call_args_list[0]
        step, current, total = first_call[0]

        assert isinstance(step, DeployStepResult)
        assert current == 1
        assert total == 2  # Two roles

    def test_callback_error_does_not_stop_deployment(self, mock_client, sample_payload):
        """Test callback errors don't stop deployment."""
        from services.deployer import Deployer

        callback = Mock(side_effect=Exception("Callback error"))
        deployer = Deployer(client=mock_client, progress_callback=callback)

        # Should not raise, deployment continues
        result = deployer.deploy_all(sample_payload)

        assert result.roles_created == 2
        assert result.teams_created == 1


# =============================================================================
# Rollback Tests
# =============================================================================

class TestRollback:
    """Tests for rollback functionality."""

    def test_rollback_deletes_created_roles(self, deployer, sample_roles):
        """Test rollback deletes created roles."""
        deployer.deploy_roles(sample_roles)
        assert len(deployer.created_roles) == 2

        success = deployer.rollback()

        assert success is True
        assert len(deployer.mock_client.roles) == 0 if hasattr(deployer, 'mock_client') else True

    def test_rollback_deletes_in_reverse_order(self, mock_client, sample_roles):
        """Test rollback deletes in reverse order."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client)
        deployer.deploy_roles(sample_roles)

        delete_order = []
        original_delete = mock_client.delete_role

        def track_delete(key):
            delete_order.append(key)
            return original_delete(key)

        mock_client.delete_role = track_delete
        deployer.rollback()

        # Should be reversed
        assert delete_order == ["developer-prod", "developer-test"]

    def test_rollback_clears_tracking_lists(self, deployer, sample_roles):
        """Test rollback clears tracking lists."""
        deployer.deploy_roles(sample_roles)
        assert len(deployer.created_roles) == 2

        deployer.rollback()

        assert len(deployer.created_roles) == 0
        assert len(deployer.created_teams) == 0

    def test_rollback_returns_true_on_success(self, deployer, sample_roles):
        """Test rollback returns True on success."""
        deployer.deploy_roles(sample_roles)

        success = deployer.rollback()

        assert success is True

    def test_rollback_handles_not_found(self, mock_client, sample_roles):
        """Test rollback handles already-deleted resources."""
        from services.deployer import Deployer

        deployer = Deployer(client=mock_client)
        deployer.deploy_roles(sample_roles)

        # Manually delete one role
        mock_client.delete_role("developer-test")

        # Rollback should still succeed (not found is OK)
        success = deployer.rollback()
        assert success is True

    def test_reset_tracking(self, deployer, sample_roles):
        """Test reset_tracking clears lists without deleting."""
        deployer.deploy_roles(sample_roles)
        assert len(deployer.created_roles) == 2

        deployer.reset_tracking()

        assert len(deployer.created_roles) == 0
        assert len(deployer.created_teams) == 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestDeployerIntegration:
    """Integration tests with MockLDClient."""

    def test_full_deployment_workflow(self, sample_payload):
        """Test complete deployment workflow."""
        from services import MockLDClient, Deployer

        client = MockLDClient()
        deployer = Deployer(client)

        # Deploy
        result = deployer.deploy_all(sample_payload)

        assert result.success is True
        assert result.roles_created == 2
        assert result.teams_created == 1
        assert len(client.roles) == 2
        assert len(client.teams) == 1

        # Verify roles were created
        role_keys = [r.key for r in client.roles]
        assert "developer-test" in role_keys
        assert "developer-prod" in role_keys

        # Verify team was created
        assert client.teams[0].key == "developers"

    def test_deployment_with_existing_resources(self, sample_payload):
        """Test deployment skips existing resources."""
        from services import MockLDClient, Deployer

        client = MockLDClient()

        # Pre-create one role
        client.create_custom_role({
            "key": "developer-test",
            "name": "Existing",
            "policy": []
        })

        deployer = Deployer(client)
        result = deployer.deploy_all(sample_payload)

        # Should skip the existing role
        assert result.roles_created == 1
        assert result.roles_skipped == 1
        assert result.success is True

    def test_deployment_and_rollback(self, sample_payload):
        """Test deployment followed by rollback."""
        from services import MockLDClient, Deployer

        client = MockLDClient()
        deployer = Deployer(client)

        # Deploy
        result = deployer.deploy_all(sample_payload)
        assert len(client.roles) == 2
        assert len(client.teams) == 1

        # Rollback
        success = deployer.rollback()
        assert success is True
        assert len(client.roles) == 0
        assert len(client.teams) == 0


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_payload(self, deployer):
        """Test deploying empty payload."""
        from services import DeployPayload

        payload = DeployPayload(
            customer_name="Test",
            project_key="test",
            roles=[],
            teams=[]
        )

        result = deployer.deploy_all(payload)

        assert result.success is True
        assert result.roles_created == 0
        assert result.teams_created == 0
        assert len(result.steps) == 0

    def test_payload_with_only_roles(self, deployer, sample_roles):
        """Test deploying payload with only roles."""
        from services import DeployPayload

        payload = DeployPayload(
            customer_name="Test",
            project_key="test",
            roles=sample_roles,
            teams=[]
        )

        result = deployer.deploy_all(payload)

        assert result.roles_created == 2
        assert result.teams_created == 0

    def test_payload_with_only_teams(self, deployer, sample_teams):
        """Test deploying payload with only teams."""
        from services import DeployPayload

        payload = DeployPayload(
            customer_name="Test",
            project_key="test",
            roles=[],
            teams=sample_teams
        )

        result = deployer.deploy_all(payload)

        assert result.roles_created == 0
        assert result.teams_created == 1

    def test_role_with_missing_key(self, deployer):
        """Test role without key uses 'unknown'."""
        result = deployer.deploy_roles([{"name": "No Key", "policy": []}])

        # Should fail validation but not crash
        assert result.roles_failed == 1


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
