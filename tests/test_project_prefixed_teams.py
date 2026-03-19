"""
Tests for Project-Prefixed Teams Feature
========================================

Phase 11 Extension: Tests for ensuring project isolation by prefixing
team keys with project name.

Pattern: "dev" → "voya-dev" with roleAttributes.projects = ["voya"]

These tests validate:
1. Team key prefix generation
2. Team name formatting
3. Single project in roleAttributes
4. Project isolation guarantees
5. Edge cases
"""

import pytest
import pandas as pd
import json
from typing import Dict, List, Any

# Note: These imports will work after implementation
# For now, they document the expected interface

# from services.payload_builder import RoleAttributePayloadBuilder, DeployPayload


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_teams():
    """Sample teams DataFrame."""
    return pd.DataFrame({
        "Name": ["Developer", "QA Engineer", "Release Manager"],
        "Key": ["dev", "qa", "release"],
        "Description": ["Development team", "QA team", "Release team"]
    })


@pytest.fixture
def sample_env_groups():
    """Sample environment groups DataFrame."""
    return pd.DataFrame({
        "Name": ["Test", "Production"],
        "Key": ["test", "production"],
        "Critical": [False, True]
    })


@pytest.fixture
def sample_project_matrix():
    """Sample project permissions matrix."""
    return pd.DataFrame({
        "Team": ["Developer", "QA Engineer", "Release Manager"],
        "Create Flags": [True, False, False],
        "Update Flags": [True, True, True],
        "Archive Flags": [True, False, True],
        "View Project": [True, True, True],
    })


@pytest.fixture
def sample_env_matrix():
    """Sample environment permissions matrix."""
    return pd.DataFrame({
        "Team": [
            "Developer", "Developer",
            "QA Engineer", "QA Engineer",
            "Release Manager", "Release Manager"
        ],
        "Environment": [
            "test", "production",
            "test", "production",
            "test", "production"
        ],
        "Update Targeting": [
            True, False,
            True, True,
            True, True
        ],
        "Apply Changes": [
            True, False,
            False, False,
            True, True
        ],
        "View SDK Key": [
            True, True,
            True, True,
            True, True
        ],
    })


# =============================================================================
# Test Class: Team Key Prefix
# =============================================================================

class TestTeamKeyPrefix:
    """Tests for project-prefixed team keys."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_team_key_with_prefix_enabled(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that team keys are prefixed with project name."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        )
        payload = builder.build()

        # Find dev team
        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["key"] == "voya-dev"

    @pytest.mark.skip(reason="Implementation pending")
    def test_team_key_without_prefix(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that team keys remain plain when prefix disabled."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=False,
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if t["key"] == "dev")
        assert dev_team["key"] == "dev"

    @pytest.mark.skip(reason="Implementation pending")
    def test_all_teams_have_project_prefix(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test all teams get the project prefix."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="mobile",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        )
        payload = builder.build()

        for team in payload.teams:
            assert team["key"].startswith("mobile-"), f"Team {team['key']} missing prefix"

    @pytest.mark.skip(reason="Implementation pending")
    def test_prefix_handles_hyphenated_project(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test prefix with project keys containing hyphens."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="voya-web",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["key"] == "voya-web-dev"


# =============================================================================
# Test Class: Team Name Format
# =============================================================================

class TestTeamNameFormat:
    """Tests for team display name formatting."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_team_name_with_project_prefix(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test team name includes project prefix."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
            team_name_format="{project}: {team}",
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["name"] == "Voya: Developer"

    @pytest.mark.skip(reason="Implementation pending")
    def test_team_name_plain_format(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test plain team name when format is {team}."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
            team_name_format="{team}",
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["name"] == "Developer"

    @pytest.mark.skip(reason="Implementation pending")
    def test_project_name_capitalized_with_hyphen(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test project name with hyphens is properly capitalized."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="mobile-app",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
            team_name_format="{project}: {team}",
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["name"] == "Mobile App: Developer"


# =============================================================================
# Test Class: Single Project Role Attributes
# =============================================================================

class TestSingleProjectRoleAttributes:
    """Tests for single project in roleAttributes."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_projects_attribute_has_single_value(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that projects roleAttribute contains only ONE project."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        )
        payload = builder.build()

        for team in payload.teams:
            projects_attr = next(
                a for a in team["roleAttributes"]
                if a["key"] == "projects"
            )
            assert len(projects_attr["values"]) == 1, \
                f"Team {team['key']} has {len(projects_attr['values'])} projects, expected 1"
            assert projects_attr["values"] == ["voya"]

    @pytest.mark.skip(reason="Implementation pending")
    def test_projects_attribute_matches_project_key(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test projects value matches the configured project key."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="mobile-app",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        )
        payload = builder.build()

        for team in payload.teams:
            projects_attr = next(
                a for a in team["roleAttributes"]
                if a["key"] == "projects"
            )
            assert projects_attr["values"] == ["mobile-app"]

    @pytest.mark.skip(reason="Implementation pending")
    def test_each_team_isolated_to_one_project(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that each team can only access one project."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        )
        payload = builder.build()

        for team in payload.teams:
            projects_attr = next(
                a for a in team["roleAttributes"]
                if a["key"] == "projects"
            )
            # Only one project - isolation guaranteed
            assert len(projects_attr["values"]) == 1, \
                f"Team {team['key']} is NOT isolated - has access to multiple projects"


# =============================================================================
# Test Class: Integration Tests
# =============================================================================

class TestProjectPrefixedTeamsIntegration:
    """Integration tests for the full workflow."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_full_payload_structure(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test complete payload with prefixed teams."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="acme",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
            team_name_format="{project}: {team}",
        )
        payload = builder.build()

        # Roles should be templates (shared)
        assert len(payload.roles) > 0
        for role in payload.roles:
            assert "${roleAttribute/projects}" in str(role["policy"])

        # Teams should be prefixed
        expected_keys = {"voya-dev", "voya-qa", "voya-release"}
        actual_keys = {t["key"] for t in payload.teams}
        assert expected_keys == actual_keys

        # Each team should have single project
        for team in payload.teams:
            projects = next(
                a["values"] for a in team["roleAttributes"]
                if a["key"] == "projects"
            )
            assert projects == ["voya"]

    @pytest.mark.skip(reason="Implementation pending")
    def test_multiple_projects_require_separate_generations(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that multiple projects need separate payload generations."""
        from services.payload_builder import RoleAttributePayloadBuilder

        # Generate for project 1
        payload1 = RoleAttributePayloadBuilder(
            customer_name="acme",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        ).build()

        # Generate for project 2
        payload2 = RoleAttributePayloadBuilder(
            customer_name="acme",
            project_key="mobile",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        ).build()

        # Team keys should be different (no overlap)
        keys1 = {t["key"] for t in payload1.teams}
        keys2 = {t["key"] for t in payload2.teams}
        assert keys1.isdisjoint(keys2), "Teams from different projects should have different keys"

        # Roles should be same (templates are shared)
        role_keys1 = {r["key"] for r in payload1.roles}
        role_keys2 = {r["key"] for r in payload2.roles}
        assert role_keys1 == role_keys2, "Template roles should be identical"

    @pytest.mark.skip(reason="Implementation pending")
    def test_json_output_valid_for_launchdarkly(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that output is valid JSON for LaunchDarkly API."""
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="acme",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        )
        payload = builder.build()

        # Should serialize without error
        json_str = payload.to_json()
        parsed = json.loads(json_str)

        # Verify structure
        assert "custom_roles" in parsed
        assert "teams" in parsed

        # Verify team structure
        for team in parsed["teams"]:
            assert "key" in team
            assert "name" in team
            assert "customRoleKeys" in team
            assert "roleAttributes" in team

            # Verify key is prefixed
            assert team["key"].startswith("voya-")

            # Verify roleAttributes structure
            for attr in team["roleAttributes"]:
                assert "key" in attr
                assert "values" in attr
                assert isinstance(attr["values"], list)


# =============================================================================
# Test Class: Edge Cases
# =============================================================================

class TestProjectPrefixEdgeCases:
    """Edge case tests."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_empty_project_key_raises_error(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test handling of empty project key."""
        from services.payload_builder import RoleAttributePayloadBuilder

        with pytest.raises(ValueError, match="project_key"):
            RoleAttributePayloadBuilder(
                customer_name="test",
                project_key="",
                teams_df=sample_teams,
                env_groups_df=sample_env_groups,
                project_matrix_df=sample_project_matrix,
                env_matrix_df=sample_env_matrix,
                prefix_team_keys=True,
            )

    @pytest.mark.skip(reason="Implementation pending")
    def test_whitespace_project_key_raises_error(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test handling of whitespace-only project key."""
        from services.payload_builder import RoleAttributePayloadBuilder

        with pytest.raises(ValueError):
            RoleAttributePayloadBuilder(
                customer_name="test",
                project_key="   ",
                teams_df=sample_teams,
                env_groups_df=sample_env_groups,
                project_matrix_df=sample_project_matrix,
                env_matrix_df=sample_env_matrix,
                prefix_team_keys=True,
            )

    @pytest.mark.skip(reason="Implementation pending")
    def test_prefix_default_is_true(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that prefix_team_keys defaults to True for safety."""
        from services.payload_builder import RoleAttributePayloadBuilder

        # Don't specify prefix_team_keys - should default to True
        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            # prefix_team_keys not specified
        )
        payload = builder.build()

        # Should be prefixed by default
        for team in payload.teams:
            assert team["key"].startswith("voya-")


# =============================================================================
# Test Class: Comparison with ps-terraform-private Pattern
# =============================================================================

class TestTerraformPatternCompliance:
    """Tests to verify compliance with ps-terraform-private pattern."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_team_key_format_matches_terraform(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """
        Test team key format matches ps-terraform-private.

        Terraform uses: key_format = "default-%s"
        Result: "default-developers"

        Our format: "{project}-{team}"
        Result: "voya-dev"
        """
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="default",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        )
        payload = builder.build()

        # Key format should be {project}-{team}
        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["key"] == "default-dev"

    @pytest.mark.skip(reason="Implementation pending")
    def test_role_attributes_structure_matches_terraform(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """
        Test roleAttributes structure matches ps-terraform-private.

        Terraform uses:
        role_attributes {
          key    = "projects"
          values = ["default"]
        }
        """
        from services.payload_builder import RoleAttributePayloadBuilder

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="default",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,
        )
        payload = builder.build()

        for team in payload.teams:
            # Find projects attribute
            projects_attr = next(
                a for a in team["roleAttributes"]
                if a["key"] == "projects"
            )

            # Structure should match Terraform
            assert "key" in projects_attr
            assert "values" in projects_attr
            assert projects_attr["key"] == "projects"
            assert projects_attr["values"] == ["default"]
