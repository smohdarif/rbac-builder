"""
Tests for Phase 3: Payload Builder
==================================

Tests for PayloadBuilder and DeployPayload classes.

Run with: pytest tests/test_payload_builder.py -v
"""

import pytest
import pandas as pd
import json

from services import PayloadBuilder, DeployPayload
from core.ld_actions import (
    get_project_actions,
    get_env_actions,
    build_flag_resource,
    build_segment_resource,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def teams_df():
    """Create sample teams DataFrame."""
    return pd.DataFrame({
        "Key": ["dev", "qa", "admin"],
        "Name": ["Developer", "QA Engineer", "Administrator"],
        "Description": ["Dev team", "QA team", "Admin team"]
    })


@pytest.fixture
def env_groups_df():
    """Create sample environment groups DataFrame."""
    return pd.DataFrame({
        "Key": ["Test", "Production"],
        "Critical": [False, True]
    })


@pytest.fixture
def project_matrix_df():
    """Create sample project permissions matrix."""
    return pd.DataFrame({
        "Team": ["Developer", "QA Engineer", "Administrator"],
        "Create Flags": [True, False, True],
        "Update Flags": [True, True, True],
        "Archive Flags": [False, False, True],
        "View Project": [True, True, True]
    })


@pytest.fixture
def env_matrix_df():
    """Create sample environment permissions matrix."""
    return pd.DataFrame({
        "Team": [
            "Developer", "Developer",
            "QA Engineer", "QA Engineer",
            "Administrator", "Administrator"
        ],
        "Environment": [
            "Test", "Production",
            "Test", "Production",
            "Test", "Production"
        ],
        "Update Targeting": [True, False, True, False, True, True],
        "Review Changes": [False, False, True, True, True, True],
        "Apply Changes": [True, False, True, False, True, True],
        "Manage Segments": [True, False, False, False, True, True]
    })


@pytest.fixture
def payload_builder(teams_df, env_groups_df, project_matrix_df, env_matrix_df):
    """Create a PayloadBuilder instance."""
    return PayloadBuilder(
        customer_name="Test Corp",
        project_key="test-project",
        teams_df=teams_df,
        env_groups_df=env_groups_df,
        project_matrix_df=project_matrix_df,
        env_matrix_df=env_matrix_df
    )


# =============================================================================
# Action Mapping Tests
# =============================================================================

class TestActionMappings:
    """Tests for LaunchDarkly action mappings."""

    def test_get_project_actions_create_flags(self):
        """Test mapping Create Flags to LD actions."""
        actions = get_project_actions("Create Flags")

        assert "createFlag" in actions

    def test_get_project_actions_update_flags(self):
        """Test mapping Update Flags to LD actions."""
        actions = get_project_actions("Update Flags")

        assert "updateName" in actions
        assert "updateDescription" in actions
        assert "updateTags" in actions

    def test_get_env_actions_update_targeting(self):
        """Test mapping Update Targeting to LD actions."""
        actions = get_env_actions("Update Targeting")

        assert "updateOn" in actions
        assert "updateFallthrough" in actions
        assert "updateTargets" in actions
        assert "updateRules" in actions

    def test_get_env_actions_review_changes(self):
        """Test mapping Review Changes to LD actions."""
        actions = get_env_actions("Review Changes")

        assert "reviewApprovalRequest" in actions

    def test_get_unknown_permission_returns_empty(self):
        """Test that unknown permission returns empty list."""
        actions = get_project_actions("Unknown Permission")

        assert actions == []


# =============================================================================
# Resource String Tests
# =============================================================================

class TestResourceStrings:
    """Tests for resource string builders."""

    def test_build_flag_resource_project_only(self):
        """Test building flag resource for project level (all environments)."""
        resource = build_flag_resource("mobile-app")

        # LaunchDarkly requires env/* in the path even for project-level flag actions
        assert resource == "proj/mobile-app:env/*:flag/*"

    def test_build_flag_resource_with_env(self):
        """Test building flag resource with environment."""
        resource = build_flag_resource("mobile-app", "production")

        assert resource == "proj/mobile-app:env/production:flag/*"

    def test_build_segment_resource(self):
        """Test building segment resource."""
        resource = build_segment_resource("mobile-app", "production")

        assert resource == "proj/mobile-app:env/production:segment/*"


# =============================================================================
# PayloadBuilder Tests
# =============================================================================

class TestPayloadBuilder:
    """Tests for PayloadBuilder class."""

    def test_build_returns_deploy_payload(self, payload_builder):
        """Test that build returns DeployPayload."""
        payload = payload_builder.build()

        assert isinstance(payload, DeployPayload)

    def test_build_generates_roles(self, payload_builder):
        """Test that build generates custom roles."""
        payload = payload_builder.build()

        # New architecture: separate project and environment roles
        # 3 project roles + 5 env roles = 8 total
        # (dev has no prod env perms, so only 5 env roles not 6)
        assert len(payload.roles) == 8

    def test_build_generates_teams(self, payload_builder):
        """Test that build generates teams."""
        payload = payload_builder.build()

        # 3 teams
        assert len(payload.teams) == 3

    def test_role_has_correct_structure(self, payload_builder):
        """Test that generated roles have correct structure."""
        payload = payload_builder.build()
        role = payload.roles[0]

        assert "key" in role
        assert "name" in role
        assert "description" in role
        assert "policy" in role
        assert isinstance(role["policy"], list)

    def test_role_key_format(self, payload_builder):
        """Test that role keys follow expected format."""
        payload = payload_builder.build()

        role_keys = [r["key"] for r in payload.roles]

        # Should have project roles: {team_key}-project
        assert "dev-project" in role_keys
        assert "qa-project" in role_keys
        assert "admin-project" in role_keys

        # Should have env roles: {team_key}-{env_key}
        assert "dev-test" in role_keys
        assert "qa-test" in role_keys
        assert "admin-production" in role_keys

    def test_policy_has_effect_actions_resources(self, payload_builder):
        """Test that policy statements have required fields."""
        payload = payload_builder.build()
        role = payload.roles[0]
        policy = role["policy"][0]

        assert policy["effect"] == "allow"
        assert "actions" in policy
        assert "resources" in policy
        assert isinstance(policy["actions"], list)
        assert isinstance(policy["resources"], list)

    def test_team_has_role_assignments(self, payload_builder):
        """Test that teams have customRoleKeys."""
        payload = payload_builder.build()
        team = payload.teams[0]

        assert "customRoleKeys" in team
        assert isinstance(team["customRoleKeys"], list)
        assert len(team["customRoleKeys"]) > 0


# =============================================================================
# DeployPayload Tests
# =============================================================================

class TestDeployPayload:
    """Tests for DeployPayload class."""

    def test_deploy_payload_to_dict(self, payload_builder):
        """Test DeployPayload serialization."""
        payload = payload_builder.build()
        data = payload.to_dict()

        assert "metadata" in data
        assert "custom_roles" in data
        assert "teams" in data
        assert "deployment_order" in data

    def test_deploy_payload_to_json(self, payload_builder):
        """Test DeployPayload JSON serialization."""
        payload = payload_builder.build()
        json_str = payload.to_json()

        # Should be valid JSON
        data = json.loads(json_str)

        assert data["metadata"]["customer_name"] == "Test Corp"
        assert data["metadata"]["project_key"] == "test-project"

    def test_get_role_count(self, payload_builder):
        """Test role count method."""
        payload = payload_builder.build()

        # 3 project roles + 5 env roles = 8
        assert payload.get_role_count() == 8

    def test_get_team_count(self, payload_builder):
        """Test team count method."""
        payload = payload_builder.build()

        assert payload.get_team_count() == 3


# =============================================================================
# Edge Cases
# =============================================================================

class TestPayloadBuilderEdgeCases:
    """Tests for edge cases."""

    def test_team_with_no_permissions_excluded(self):
        """Test that teams with no permissions don't generate roles with policies."""
        teams_df = pd.DataFrame({
            "Key": ["dev"],
            "Name": ["Developer"],
            "Description": [""]
        })
        env_groups_df = pd.DataFrame({
            "Key": ["Test"],
            "Critical": [False]
        })
        # All permissions False
        project_matrix_df = pd.DataFrame({
            "Team": ["Developer"],
            "Create Flags": [False],
            "Update Flags": [False],
            "View Project": [False]
        })
        env_matrix_df = pd.DataFrame({
            "Team": ["Developer"],
            "Environment": ["Test"],
            "Update Targeting": [False],
            "Apply Changes": [False]
        })

        builder = PayloadBuilder(
            customer_name="Test",
            project_key="test",
            teams_df=teams_df,
            env_groups_df=env_groups_df,
            project_matrix_df=project_matrix_df,
            env_matrix_df=env_matrix_df
        )
        payload = builder.build()

        # Should still generate team but role may have empty policy
        # or be excluded entirely
        assert payload.get_team_count() == 1

    def test_empty_dataframes(self):
        """Test handling of empty DataFrames."""
        # Create minimal DataFrames with required columns
        builder = PayloadBuilder(
            customer_name="Test",
            project_key="test",
            teams_df=pd.DataFrame({"Key": [], "Name": [], "Description": []}),
            env_groups_df=pd.DataFrame({"Key": [], "Critical": []}),
            project_matrix_df=pd.DataFrame({"Team": []}),
            env_matrix_df=pd.DataFrame({"Team": [], "Environment": []})
        )
        payload = builder.build()

        assert payload.get_role_count() == 0
        assert payload.get_team_count() == 0


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
