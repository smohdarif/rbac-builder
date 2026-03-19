"""
Test Role Attribute Pattern (formerly Phase 12 Critical Environments)
=====================================================================

Tests that the RoleAttributePayloadBuilder always uses the role attribute
pattern for environment scoping — regardless of whether environments have
a Critical column or critical/non-critical split.

The old {critical:true} wildcard pattern has been replaced by:
- ONE shared role per permission (e.g., "update-targeting")
- Role resource: proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*
- Teams fill in exact env keys via roleAttributes:
    update-targeting-environments = ["production", "staging"]

Run with: pytest tests/test_critical_environments.py -v
"""

import pytest
import pandas as pd
from services.payload_builder import RoleAttributePayloadBuilder, slugify


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def teams_df():
    """Standard teams DataFrame."""
    return pd.DataFrame({
        "Key": ["dev", "qa", "admin"],
        "Name": ["Developer", "QA Engineer", "Administrator"],
        "Description": ["Dev team", "QA team", "Admin team"]
    })


@pytest.fixture
def env_groups_with_criticality():
    """Environment groups with BOTH critical and non-critical environments."""
    return pd.DataFrame({
        "Key": ["Dev", "QA", "Staging", "Production", "DR"],
        "Requires Approvals": [False, False, False, True, True],
        "Critical": [False, False, False, True, True],
        "Notes": ["Development", "QA testing", "Pre-prod", "Live", "Disaster Recovery"]
    })


@pytest.fixture
def env_groups_all_non_critical():
    """Environment groups with ONLY non-critical environments."""
    return pd.DataFrame({
        "Key": ["Dev", "QA", "Staging"],
        "Requires Approvals": [False, False, False],
        "Critical": [False, False, False],
        "Notes": ["Development", "QA testing", "Pre-prod"]
    })


@pytest.fixture
def env_groups_no_critical_column():
    """Environment groups WITHOUT Critical column (backward compat)."""
    return pd.DataFrame({
        "Key": ["Test", "Production"],
        "Requires Approvals": [False, True],
        "Notes": ["Test env", "Prod env"]
    })


@pytest.fixture
def project_matrix_df():
    """Standard project permissions matrix."""
    return pd.DataFrame({
        "Team": ["Developer", "QA Engineer", "Administrator"],
        "Create Flags": [True, False, True],
        "Update Flags": [True, True, True],
        "View Project": [True, True, True]
    })


@pytest.fixture
def env_matrix_with_criticality():
    """
    Environment matrix where teams have different permissions per environment.
    Developer has targeting in non-critical envs only, review in critical envs.
    """
    return pd.DataFrame({
        "Team": [
            "Developer", "Developer", "Developer", "Developer", "Developer",
            "QA Engineer", "QA Engineer", "QA Engineer", "QA Engineer", "QA Engineer",
        ],
        "Environment": [
            "Dev", "QA", "Staging", "Production", "DR",
            "Dev", "QA", "Staging", "Production", "DR",
        ],
        "Update Targeting": [
            True, True, True, False, False,   # Developer: targeting in non-critical only
            True, True, True, False, False,   # QA same
        ],
        "Review Changes": [
            False, False, True, True, True,   # Developer: review in Staging/Prod/DR
            True, True, True, True, True,     # QA: review everywhere
        ],
        "Apply Changes": [
            True, True, False, False, False,  # Developer: apply in Dev/QA only
            False, False, False, False, False,
        ],
        "Manage Segments": [
            True, True, True, False, False,   # Developer: segments in non-critical
            False, False, False, False, False,
        ]
    })


# =============================================================================
# Helper: build a standard builder
# =============================================================================

def make_builder(teams_df, env_groups_df, project_matrix_df, env_matrix_df):
    return RoleAttributePayloadBuilder(
        customer_name="Test",
        project_key="test-project",
        teams_df=teams_df,
        env_groups_df=env_groups_df,
        project_matrix_df=project_matrix_df,
        env_matrix_df=env_matrix_df
    )


# =============================================================================
# Test: Helper methods still work (backward compat for env_groups inspection)
# =============================================================================

class TestEnvGroupHelpers:
    """
    These helper methods remain available for env_groups inspection
    even though they no longer drive role generation.
    """

    def test_is_env_critical_true_for_critical(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        assert builder._is_env_critical("Production") == True
        assert builder._is_env_critical("DR") == True

    def test_is_env_critical_false_for_non_critical(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        assert builder._is_env_critical("Dev") == False
        assert builder._is_env_critical("QA") == False
        assert builder._is_env_critical("Staging") == False

    def test_get_critical_envs(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        critical_envs = builder._get_critical_envs()
        assert "Production" in critical_envs
        assert "DR" in critical_envs
        assert len(critical_envs) == 2

    def test_get_non_critical_envs(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        non_critical_envs = builder._get_non_critical_envs()
        assert "Dev" in non_critical_envs
        assert "QA" in non_critical_envs
        assert "Staging" in non_critical_envs
        assert len(non_critical_envs) == 3


# =============================================================================
# Test: Role generation always uses single role per permission
# =============================================================================

class TestRoleGeneration:
    """
    Regardless of criticality column, builder generates ONE role per permission
    using ${roleAttribute/<perm>-environments} placeholder — no critical/non-critical split.
    """

    def test_generates_single_role_per_env_permission_with_criticality_data(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """Even with mixed critical/non-critical envs, only ONE role per permission."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        role_keys = [r["key"] for r in payload.roles]

        # Single role for each permission — no critical/non-critical split
        assert "update-targeting" in role_keys
        assert "review-changes" in role_keys
        assert "apply-changes" in role_keys
        assert "manage-segments" in role_keys

        # Must NOT have old {critical:*} role keys
        assert "non-critical-update-targeting" not in role_keys
        assert "critical-update-targeting" not in role_keys
        assert "non-critical-review-changes" not in role_keys
        assert "critical-review-changes" not in role_keys

    def test_generates_single_role_per_env_permission_without_critical_column(
        self, teams_df, env_groups_no_critical_column, project_matrix_df
    ):
        """No Critical column → still uses role attribute pattern."""
        env_matrix = pd.DataFrame({
            "Team": ["Developer", "Developer"],
            "Environment": ["Test", "Production"],
            "Update Targeting": [True, False],
            "Review Changes": [False, True]
        })
        builder = make_builder(teams_df, env_groups_no_critical_column, project_matrix_df, env_matrix)
        payload = builder.build()
        role_keys = [r["key"] for r in payload.roles]

        assert "update-targeting" in role_keys
        assert "review-changes" in role_keys
        assert "non-critical-update-targeting" not in role_keys
        assert "critical-update-targeting" not in role_keys

    def test_env_role_resource_uses_env_attribute_placeholder(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """Role resource must use ${roleAttribute/update-targeting-environments} — not {critical:*}."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "update-targeting")

        resource = role["policy"][0]["resources"][0]

        # Must have per-permission env attribute placeholder
        assert "${roleAttribute/update-targeting-environments}" in resource

        # Must NOT have old wildcard specifiers
        assert "{critical:true}" not in resource
        assert "{critical:false}" not in resource

    def test_manage_segments_role_uses_env_attribute_placeholder(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """Manage Segments role resource uses manage-segments-environments attribute."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "manage-segments")

        resource = role["policy"][0]["resources"][0]
        assert "${roleAttribute/manage-segments-environments}" in resource
        assert "{critical:" not in resource

    def test_view_sdk_key_role_uses_env_attribute_placeholder(
        self, teams_df, env_groups_no_critical_column, project_matrix_df
    ):
        """View SDK Key role resource uses view-sdk-key-environments attribute."""
        env_matrix = pd.DataFrame({
            "Team": ["Developer", "Developer"],
            "Environment": ["Test", "Production"],
            "View SDK Key": [True, True]
        })
        builder = make_builder(teams_df, env_groups_no_critical_column, project_matrix_df, env_matrix)
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "view-sdk-key")

        resource = role["policy"][0]["resources"][0]
        assert "${roleAttribute/view-sdk-key-environments}" in resource
        assert "{critical:" not in resource

    def test_project_roles_not_affected(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """Project-level roles are unchanged — they only use the projects attribute."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        role_keys = [r["key"] for r in payload.roles]

        assert "create-flags" in role_keys
        assert "update-flags" in role_keys
        assert "non-critical-create-flags" not in role_keys
        assert "critical-create-flags" not in role_keys


# =============================================================================
# Test: Team role assignment
# =============================================================================

class TestTeamRoleAssignment:
    """
    Teams get a role key if they have that permission enabled in ANY environment.
    The roleAttributes control which specific envs are accessible.
    """

    def test_team_gets_single_update_targeting_role(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """Developer has Update Targeting in Dev/QA/Staging → gets 'update-targeting' (not split)."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        dev_team = next(t for t in payload.teams if "dev" in t["key"])

        assert "update-targeting" in dev_team["customRoleKeys"]
        assert "non-critical-update-targeting" not in dev_team["customRoleKeys"]
        assert "critical-update-targeting" not in dev_team["customRoleKeys"]

    def test_team_gets_single_review_changes_role(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """Developer has Review Changes in Staging/Prod/DR → gets 'review-changes' (not split)."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        dev_team = next(t for t in payload.teams if "dev" in t["key"])

        assert "review-changes" in dev_team["customRoleKeys"]
        assert "non-critical-review-changes" not in dev_team["customRoleKeys"]
        assert "critical-review-changes" not in dev_team["customRoleKeys"]

    def test_team_without_permission_does_not_get_role(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """QA Engineer has no Apply Changes → should not get apply-changes role."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        qa_team = next(t for t in payload.teams if "qa" in t["key"])

        assert "apply-changes" not in qa_team["customRoleKeys"]


# =============================================================================
# Test: Role attributes on teams (the core of the pattern)
# =============================================================================

class TestTeamRoleAttributes:
    """
    Teams always have per-permission env attributes listing the exact environment
    keys they can access for each permission.
    """

    def test_team_has_per_permission_env_attributes(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """Developer team has per-permission env attributes for all its env roles."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        attr_keys = [a["key"] for a in dev_team["roleAttributes"]]

        assert "projects" in attr_keys
        assert "update-targeting-environments" in attr_keys
        assert "review-changes-environments" in attr_keys
        assert "apply-changes-environments" in attr_keys
        assert "manage-segments-environments" in attr_keys

    def test_update_targeting_envs_are_correct(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """Developer has Update Targeting in Dev/QA/Staging — attr must reflect this."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        attr = next(a for a in dev_team["roleAttributes"] if a["key"] == "update-targeting-environments")

        assert "Dev" in attr["values"]
        assert "QA" in attr["values"]
        assert "Staging" in attr["values"]
        # Production and DR are NOT in Developer's targeting list
        assert "Production" not in attr["values"]
        assert "DR" not in attr["values"]

    def test_apply_changes_envs_are_correct(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """Developer has Apply Changes in Dev/QA only — attr must reflect this."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        attr = next(a for a in dev_team["roleAttributes"] if a["key"] == "apply-changes-environments")

        assert "Dev" in attr["values"]
        assert "QA" in attr["values"]
        assert "Staging" not in attr["values"]
        assert "Production" not in attr["values"]

    def test_review_changes_envs_include_both_critical_and_non_critical(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """
        Developer has Review Changes in Staging (non-critical) AND Production/DR (critical).
        All are listed together in one attribute — no split needed.
        """
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        attr = next(a for a in dev_team["roleAttributes"] if a["key"] == "review-changes-environments")

        assert "Staging" in attr["values"]
        assert "Production" in attr["values"]
        assert "DR" in attr["values"]

    def test_no_env_attributes_for_unused_permissions(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """QA has no Apply Changes → no apply-changes-environments attribute."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()
        qa_team = next(t for t in payload.teams if "qa" in t["key"])
        attr_keys = [a["key"] for a in qa_team["roleAttributes"]]

        assert "apply-changes-environments" not in attr_keys

    def test_projects_attribute_always_present(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """projects attribute must always be present on every team."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()

        for team in payload.teams:
            projects_attr = next((a for a in team["roleAttributes"] if a["key"] == "projects"), None)
            assert projects_attr is not None, f"Team {team['key']} missing 'projects' attribute"
            assert projects_attr["values"] == ["test-project"]

    def test_no_critical_wildcard_in_attributes(
        self, teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality
    ):
        """No team roleAttribute should use *;{critical:*} — only explicit env keys."""
        builder = make_builder(teams_df, env_groups_with_criticality, project_matrix_df, env_matrix_with_criticality)
        payload = builder.build()

        for team in payload.teams:
            for attr in team["roleAttributes"]:
                for value in attr["values"]:
                    assert "{critical:" not in str(value), (
                        f"Team {team['key']} attr '{attr['key']}' has critical wildcard in values"
                    )
