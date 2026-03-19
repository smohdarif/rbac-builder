"""
Tests for Role Attributes Feature
=================================

Phase 11: Tests for generating template roles with role attribute placeholders
and teams with roleAttributes.

These tests validate:
1. Role attribute resource string builders
2. Template role generation
3. Team role attributes generation
4. Full payload generation in role attributes mode
5. Edge cases and error handling
6. Comparison between hardcoded and role attributes modes
"""

import pytest
import pandas as pd
import json
from typing import Dict, List, Any

from core.ld_actions import (
    build_role_attribute_resource,
    build_env_role_attribute_resource,
    build_project_only_role_attribute_resource,
    PERMISSION_ATTRIBUTE_MAP,
    get_attribute_name,
    is_project_level_permission,
    is_env_level_permission,
    get_resource_type_for_permission,
    PROJECT_PERMISSION_MAP,
    ENV_PERMISSION_MAP,
)
from services.payload_builder import (
    RoleAttributePayloadBuilder,
    DeployPayload,
    PayloadBuilder,
    slugify,
)


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
    """
    Sample environment groups DataFrame.

    Note: All environments are non-critical to avoid triggering the
    criticality pattern. For criticality tests, see test_critical_environments.py
    """
    return pd.DataFrame({
        "Name": ["Test", "Staging", "Production"],
        "Key": ["test", "staging", "production"],
        "Environments": ["test", "staging", "production"],
        "Critical": [False, False, False]  # All non-critical to test standard behavior
    })


@pytest.fixture
def sample_project_matrix():
    """Sample project permissions matrix."""
    return pd.DataFrame({
        "Team": ["Developer", "QA Engineer", "Release Manager"],
        "Create Flags": [True, False, False],
        "Update Flags": [True, True, True],
        "Archive Flags": [True, False, True],
        "Update Client Side Availability": [False, False, True],
        "Manage Metrics": [False, False, True],
        "Manage Release Pipelines": [False, False, True],
        "Create AI Configs": [False, False, False],
        "Update AI Configs": [False, False, False],
        "Delete AI Configs": [False, False, False],
        "Manage AI Variations": [False, False, False],
        "View Project": [True, True, True],
    })


@pytest.fixture
def sample_env_matrix():
    """Sample environment permissions matrix."""
    return pd.DataFrame({
        "Team": [
            "Developer", "Developer", "Developer",
            "QA Engineer", "QA Engineer", "QA Engineer",
            "Release Manager", "Release Manager", "Release Manager"
        ],
        "Environment": [
            "test", "staging", "production",
            "test", "staging", "production",
            "test", "staging", "production"
        ],
        "Update Targeting": [
            True, True, False,
            True, True, True,
            True, True, True
        ],
        "Review Changes": [
            False, False, True,
            True, True, True,
            True, True, True
        ],
        "Apply Changes": [
            True, True, False,
            False, False, False,
            True, True, True
        ],
        "Manage Segments": [
            True, True, False,
            True, True, False,
            True, True, True
        ],
        "Manage Experiments": [
            False, False, False,
            False, False, False,
            True, True, True
        ],
        "Update AI Config Targeting": [
            False, False, False,
            False, False, False,
            False, False, False
        ],
        "View SDK Key": [
            True, True, True,
            True, True, True,
            True, True, True
        ],
    })


# =============================================================================
# Test Class: Resource Builders
# =============================================================================

class TestRoleAttributeResourceBuilders:
    """Tests for role attribute resource string builders."""

    def test_build_role_attribute_resource_flag(self):
        """Test building flag resource with role attribute."""
        resource = build_role_attribute_resource("projects", "flag")
        assert resource == "proj/${roleAttribute/projects}:env/*:flag/*"

    def test_build_role_attribute_resource_segment(self):
        """Test building segment resource with role attribute."""
        resource = build_role_attribute_resource("projects", "segment")
        assert resource == "proj/${roleAttribute/projects}:env/*:segment/*"

    def test_build_role_attribute_resource_experiment(self):
        """Test building experiment resource with role attribute."""
        resource = build_role_attribute_resource("projects", "experiment")
        assert resource == "proj/${roleAttribute/projects}:env/*:experiment/*"

    def test_build_env_role_attribute_resource(self):
        """Test building env-scoped resource with two attributes."""
        resource = build_env_role_attribute_resource(
            "projects",
            "updateTargetingEnvironments",
            "flag"
        )
        expected = "proj/${roleAttribute/projects}:env/${roleAttribute/updateTargetingEnvironments}:flag/*"
        assert resource == expected

    def test_build_env_role_attribute_resource_segment(self):
        """Test building segment resource with two attributes."""
        resource = build_env_role_attribute_resource(
            "projects",
            "manageSegmentsEnvironments",
            "segment"
        )
        expected = "proj/${roleAttribute/projects}:env/${roleAttribute/manageSegmentsEnvironments}:segment/*"
        assert resource == expected

    def test_build_project_only_role_attribute_resource(self):
        """Test building project-only resource with role attribute."""
        resource = build_project_only_role_attribute_resource("projects")
        assert resource == "proj/${roleAttribute/projects}"

    def test_placeholder_format_matches_launchdarkly(self):
        """Test that placeholder format is correct for LaunchDarkly API."""
        # The format must be exactly: ${roleAttribute/attributeName}
        # Not: $${...} (that's Terraform escaping)
        resource = build_role_attribute_resource("projects", "flag")
        assert "${roleAttribute/projects}" in resource
        assert "$${" not in resource  # No Terraform escaping


# =============================================================================
# Test Class: Template Role Generation
# =============================================================================

class TestTemplateRoleGeneration:
    """Tests for generating template roles."""

    def test_slugify_function(self):
        """Test slugify converts names to URL-safe format."""
        assert slugify("Create Flags") == "create-flags"
        assert slugify("Update Client Side Availability") == "update-client-side-availability"
        assert slugify("Manage AI Variations") == "manage-ai-variations"

    def test_builder_creates_template_roles(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that builder creates template roles with placeholders."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        # All roles should have ${roleAttribute/...} in resources
        for role in payload.roles:
            has_placeholder = any(
                "${roleAttribute/" in r
                for p in role["policy"]
                for r in p["resources"]
            )
            assert has_placeholder, f"Role {role['key']} missing role attribute placeholder"

    def test_template_roles_have_correct_structure(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that template roles have all required fields."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        for role in payload.roles:
            assert "key" in role
            assert "name" in role
            assert "description" in role
            assert "policy" in role
            assert isinstance(role["policy"], list)
            assert len(role["policy"]) > 0

    def test_segment_template_uses_segment_resource(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that Manage Segments uses segment/* resource."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        segment_role = next(
            (r for r in payload.roles if r["key"] == "manage-segments"),
            None
        )
        assert segment_role is not None
        assert ":segment/*" in segment_role["policy"][0]["resources"][0]

    def test_experiment_template_uses_experiment_resource(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that Manage Experiments uses experiment/* resource."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        experiment_role = next(
            (r for r in payload.roles if r["key"] == "manage-experiments"),
            None
        )
        assert experiment_role is not None
        assert ":experiment/*" in experiment_role["policy"][0]["resources"][0]


# =============================================================================
# Test Class: Team Role Attributes
# =============================================================================

class TestTeamRoleAttributes:
    """Tests for generating team role attributes."""

    def test_teams_have_role_attributes(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that teams have roleAttributes in output."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        for team in payload.teams:
            assert "roleAttributes" in team
            assert isinstance(team["roleAttributes"], list)
            assert len(team["roleAttributes"]) > 0

    def test_teams_have_projects_attribute(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that all teams have single project attribute."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",  # Single project per team
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        for team in payload.teams:
            projects_attr = [
                a for a in team["roleAttributes"]
                if a["key"] == "projects"
            ]
            assert len(projects_attr) == 1
            # Each team has exactly ONE project (for isolation)
            assert projects_attr[0]["values"] == ["voya"]

    def test_team_env_attributes_match_matrix(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that env attributes match the permissions matrix."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,  # Teams are prefixed
        )
        payload = builder.build()

        # Find Developer team (now prefixed with project: voya-dev)
        dev_team = next(
            (t for t in payload.teams if t["key"] == "voya-dev"),
            None
        )
        assert dev_team is not None

        # Developer has Update Targeting for test and staging only (not production)
        targeting_attr = next(
            (a for a in dev_team["roleAttributes"]
             if a["key"] == "update-targeting-environments"),
            None
        )
        assert targeting_attr is not None
        assert set(targeting_attr["values"]) == {"test", "staging"}


# =============================================================================
# Test Class: Full Payload Builder (Integration)
# =============================================================================

class TestRoleAttributePayloadBuilder:
    """Integration tests for RoleAttributePayloadBuilder."""

    def test_build_returns_deploy_payload(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that build returns a DeployPayload object."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        assert isinstance(payload, DeployPayload)
        assert hasattr(payload, "roles")
        assert hasattr(payload, "teams")

    def test_build_no_duplicate_roles(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that no duplicate roles are created."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        role_keys = [r["key"] for r in payload.roles]
        assert len(role_keys) == len(set(role_keys)), "Duplicate role keys found"

    def test_payload_json_serializable(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that payload can be serialized to valid JSON."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        # Should not raise
        json_str = payload.to_json()
        parsed = json.loads(json_str)

        assert "custom_roles" in parsed
        assert "teams" in parsed

    def test_teams_reference_valid_roles(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that teams only reference roles that exist."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        role_keys = {r["key"] for r in payload.roles}
        for team in payload.teams:
            for team_role in team["customRoleKeys"]:
                assert team_role in role_keys, f"Team {team['key']} references non-existent role {team_role}"


# =============================================================================
# Test Class: Edge Cases
# =============================================================================

class TestRoleAttributeEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_teams_returns_empty_payload(self, sample_env_groups):
        """Test handling of empty teams DataFrame."""
        empty_teams = pd.DataFrame({"Name": [], "Key": [], "Description": []})
        empty_project_matrix = pd.DataFrame({"Team": []})
        empty_env_matrix = pd.DataFrame({"Team": [], "Environment": []})

        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="proj",
            teams_df=empty_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=empty_project_matrix,
            env_matrix_df=empty_env_matrix,
        )

        payload = builder.build()
        assert len(payload.roles) == 0
        assert len(payload.teams) == 0

    def test_single_project_enforced(
        self, sample_teams, sample_env_groups, sample_project_matrix, sample_env_matrix
    ):
        """Test that each team has exactly ONE project in roleAttributes."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="voya",  # Single project (not list!)
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )

        payload = builder.build()

        # Each team must have exactly ONE project for isolation
        for team in payload.teams:
            projects_attr = [a for a in team["roleAttributes"] if a["key"] == "projects"]
            assert len(projects_attr) == 1
            assert len(projects_attr[0]["values"]) == 1  # Only ONE project!
            assert projects_attr[0]["values"] == ["voya"]


# =============================================================================
# Test Class: Mode Comparison
# =============================================================================

class TestModeComparison:
    """Tests comparing hardcoded vs role attributes modes."""

    def test_role_attributes_role_count_scales_better(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that role attributes mode scales better with more teams."""
        # For small team counts, role attributes might have more roles
        # because it creates one role per permission type.
        #
        # The key benefit is that role attributes count stays CONSTANT
        # as you add more teams, while hardcoded grows linearly.
        #
        # Hardcoded: 3 teams × (1 project + 3 env) = 12 roles
        # With 10 teams: 10 × 4 = 40 roles
        # With 100 teams: 100 × 4 = 400 roles
        #
        # Role Attributes: ~13 template roles (based on permissions)
        # With 10 teams: still ~13 roles
        # With 100 teams: still ~13 roles

        # Role attributes mode
        roleattr_builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        roleattr_payload = roleattr_builder.build()

        # Role count should be based on unique permissions, not teams
        # Max permissions: ~11 project + ~7 env = ~18 (if all enabled)
        # Our sample has fewer enabled, so should be less
        assert len(roleattr_payload.roles) < 20  # Reasonable upper bound

        # Verify roles are template roles (have placeholders)
        for role in roleattr_payload.roles:
            has_placeholder = any(
                "${roleAttribute/" in r
                for p in role["policy"]
                for r in p["resources"]
            )
            assert has_placeholder

    def test_teams_have_role_attributes_only_in_ra_mode(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that roleAttributes only appear in role attributes mode."""
        # Hardcoded mode
        hardcoded_builder = PayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        hardcoded_payload = hardcoded_builder.build()

        # Role attributes mode
        roleattr_builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        roleattr_payload = roleattr_builder.build()

        # Hardcoded teams should NOT have roleAttributes
        for team in hardcoded_payload.teams:
            assert "roleAttributes" not in team

        # Role attributes teams SHOULD have roleAttributes
        for team in roleattr_payload.teams:
            assert "roleAttributes" in team


# =============================================================================
# Test Class: Permission Attribute Mapping
# =============================================================================

class TestPermissionAttributeMapping:
    """Tests for permission to attribute name mapping."""

    def test_all_env_permissions_have_mapping(self):
        """Test that all env permissions have attribute mappings."""
        for perm in ENV_PERMISSION_MAP.keys():
            attr = get_attribute_name(perm)
            assert attr is not None
            assert attr != ""

    def test_attribute_names_follow_kebab_case_convention(self):
        """Test that attribute names follow kebab-case convention (matching sa-demo)."""
        for perm, attr in PERMISSION_ATTRIBUTE_MAP.items():
            if perm in ENV_PERMISSION_MAP:
                # Env permissions should have kebab-case attribute names ending in -environments
                assert attr.endswith("-environments") or attr == "projects"
                # Should not have underscores
                assert "_" not in attr
                # Should not have camelCase (no uppercase letters)
                assert attr == attr.lower()

    def test_project_permissions_use_projects_attribute(self):
        """Test that all project permissions use 'projects' attribute."""
        for perm in PROJECT_PERMISSION_MAP.keys():
            attr = get_attribute_name(perm)
            assert attr == "projects"

    def test_is_project_level_permission(self):
        """Test is_project_level_permission function."""
        assert is_project_level_permission("Create Flags") is True
        assert is_project_level_permission("View Project") is True
        assert is_project_level_permission("Update Targeting") is False
        assert is_project_level_permission("Manage Segments") is False

    def test_is_env_level_permission(self):
        """Test is_env_level_permission function."""
        assert is_env_level_permission("Update Targeting") is True
        assert is_env_level_permission("Manage Segments") is True
        assert is_env_level_permission("Create Flags") is False
        assert is_env_level_permission("View Project") is False

    def test_get_resource_type_for_permission(self):
        """Test get_resource_type_for_permission function."""
        assert get_resource_type_for_permission("Update Targeting") == "flag"
        assert get_resource_type_for_permission("Manage Segments") == "segment"
        assert get_resource_type_for_permission("Manage Experiments") == "experiment"
        assert get_resource_type_for_permission("Create Flags") == "flag"


# =============================================================================
# Test Class: JSON Output Validation
# =============================================================================

class TestJsonOutputValidation:
    """Tests for validating JSON output format."""

    def test_role_json_has_required_fields(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that role JSON has all required fields."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        for role in payload.roles:
            assert "key" in role
            assert "name" in role
            assert "policy" in role
            assert len(role["policy"]) > 0

    def test_team_json_has_required_fields(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test that team JSON has all required fields."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        for team in payload.teams:
            assert "key" in team
            assert "name" in team
            assert "customRoleKeys" in team
            assert "roleAttributes" in team

    def test_role_attributes_format(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test roleAttributes format is correct."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        for team in payload.teams:
            for attr in team["roleAttributes"]:
                assert "key" in attr
                assert "values" in attr
                assert isinstance(attr["key"], str)
                assert isinstance(attr["values"], list)

    def test_policy_format(
        self,
        sample_teams,
        sample_env_groups,
        sample_project_matrix,
        sample_env_matrix
    ):
        """Test policy format is correct."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        for role in payload.roles:
            for policy in role["policy"]:
                assert "effect" in policy
                assert policy["effect"] == "allow"
                assert "actions" in policy
                assert "resources" in policy
                assert isinstance(policy["actions"], list)
                assert isinstance(policy["resources"], list)
