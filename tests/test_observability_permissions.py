"""
Tests for Phase 14: Observability Permissions
==============================================

Tests that observability permissions generate roles with project-scoped
resources (no :env/* segment), matching the Gonfalon source validation.

All action names and resource paths verified against:
  gonfalon/internal/roles/action.go
  gonfalon/internal/roles/resource_identifier.go

Run with: pytest tests/test_observability_permissions.py -v
"""

import pytest
import pandas as pd

from core.ld_actions import (
    get_project_actions,
    is_observability_permission,
    get_observability_resource_type,
    build_project_type_resource,
    OBSERVABILITY_RESOURCE_MAP,
    PROJECT_PERMISSION_MAP,
)
from services.payload_builder import RoleAttributePayloadBuilder


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def base_builder_kwargs():
    """Common builder kwargs — override specific fields per test."""
    return dict(
        customer_name="Test",
        project_key="test-project",
        teams_df=pd.DataFrame({
            "Key": ["dev"], "Name": ["Developer"], "Description": [""]
        }),
        env_groups_df=pd.DataFrame({"Key": ["production"], "Critical": [True]}),
        env_matrix_df=pd.DataFrame({"Team": [], "Environment": []}),
    )


def make_builder(project_perms: dict, base_kwargs: dict) -> RoleAttributePayloadBuilder:
    """Helper: build a RoleAttributePayloadBuilder with given project permissions."""
    teams = ["Developer"]
    matrix_data = {"Team": teams}
    matrix_data.update({perm: [enabled] for perm, enabled in project_perms.items()})

    return RoleAttributePayloadBuilder(
        project_matrix_df=pd.DataFrame(matrix_data),
        **base_kwargs,
    )


# =============================================================================
# Group 1: Action Mappings (TC-OB-01, TC-OB-02)
# =============================================================================

class TestActionMappings:
    """Verify all observability permissions map to correct LD action codes."""

    def test_view_sessions_actions(self):
        """TC-OB-01a: View Sessions maps to viewSession."""
        assert get_project_actions("View Sessions") == ["viewSession"]

    def test_view_errors_actions(self):
        """TC-OB-01b: View Errors maps to viewError and updateErrorStatus."""
        actions = get_project_actions("View Errors")
        assert "viewError" in actions
        assert "updateErrorStatus" in actions
        assert len(actions) == 2

    def test_view_logs_actions(self):
        """TC-OB-01c: View Logs maps to viewLog."""
        assert get_project_actions("View Logs") == ["viewLog"]

    def test_view_traces_actions(self):
        """TC-OB-01d: View Traces maps to viewTrace."""
        assert get_project_actions("View Traces") == ["viewTrace"]

    def test_manage_alerts_actions(self):
        """TC-OB-01e: Manage Alerts maps to 5 alert actions."""
        actions = get_project_actions("Manage Alerts")
        assert "viewAlert" in actions
        assert "createAlert" in actions
        assert "deleteAlert" in actions
        assert "updateAlertOn" in actions
        assert "updateAlertConfiguration" in actions
        assert len(actions) == 5

    def test_manage_obs_dashboards_actions(self):
        """TC-OB-01f: Manage Observability Dashboards maps to 8 actions."""
        actions = get_project_actions("Manage Observability Dashboards")
        assert "viewObservabilityDashboard" in actions
        assert "createObservabilityDashboard" in actions
        assert "deleteObservabilityDashboard" in actions
        assert "addObservabilityGraphToDashboard" in actions
        assert "removeObservabilityGraphFromDashboard" in actions
        assert "updateObservabilityDashboardConfiguration" in actions
        assert "updateObservabilityGraphConfiguration" in actions
        assert "updateObservabilitySettings" in actions
        assert len(actions) == 8

    def test_talk_to_vega_actions(self):
        """TC-OB-01g: Talk to Vega maps to talkToVega."""
        assert get_project_actions("Talk to Vega") == ["talkToVega"]

    def test_all_observability_permissions_in_project_map(self):
        """TC-OB-02: All 7 observability permissions are in PROJECT_PERMISSION_MAP."""
        for perm in OBSERVABILITY_RESOURCE_MAP.keys():
            assert perm in PROJECT_PERMISSION_MAP, f"'{perm}' missing from PROJECT_PERMISSION_MAP"


# =============================================================================
# Group 2: Resource Builder (TC-OB-03, TC-OB-04, TC-OB-05)
# =============================================================================

class TestResourceBuilder:
    """Verify the new build_project_type_resource() function."""

    def test_build_project_type_resource_session(self):
        """TC-OB-03: Session resource has no :env/* segment."""
        resource = build_project_type_resource("projects", "session")
        assert resource == "proj/${roleAttribute/projects}:session/*"
        assert ":env/" not in resource

    def test_build_project_type_resource_for_all_types(self):
        """TC-OB-04: All observability resource types produce correct paths."""
        expected = {
            "session":                 "proj/${roleAttribute/projects}:session/*",
            "error":                   "proj/${roleAttribute/projects}:error/*",
            "log":                     "proj/${roleAttribute/projects}:log/*",
            "trace":                   "proj/${roleAttribute/projects}:trace/*",
            "alert":                   "proj/${roleAttribute/projects}:alert/*",
            "observability-dashboard": "proj/${roleAttribute/projects}:observability-dashboard/*",
            "vega":                    "proj/${roleAttribute/projects}:vega/*",
        }
        for resource_type, expected_path in expected.items():
            result = build_project_type_resource("projects", resource_type)
            assert result == expected_path, f"Mismatch for '{resource_type}'"

    def test_is_observability_permission_true_for_obs_perms(self):
        """TC-OB-05a: is_observability_permission returns True for all obs perms."""
        for perm in OBSERVABILITY_RESOURCE_MAP.keys():
            assert is_observability_permission(perm), f"'{perm}' should be observability"

    def test_is_observability_permission_false_for_standard_perms(self):
        """TC-OB-05b: is_observability_permission returns False for non-obs perms."""
        assert is_observability_permission("Create Flags")   is False
        assert is_observability_permission("Update Flags")   is False
        assert is_observability_permission("Manage Metrics") is False
        assert is_observability_permission("View Project")   is False
        assert is_observability_permission("Unknown")        is False

    def test_get_observability_resource_type_for_all(self):
        """get_observability_resource_type returns correct type for each permission."""
        expected = {
            "View Sessions":                   "session",
            "View Errors":                     "error",
            "View Logs":                       "log",
            "View Traces":                     "trace",
            "Manage Alerts":                   "alert",
            "Manage Observability Dashboards": "observability-dashboard",
            "Talk to Vega":                    "vega",
        }
        for perm, resource_type in expected.items():
            assert get_observability_resource_type(perm) == resource_type

    def test_get_observability_resource_type_unknown_returns_empty(self):
        """Unknown permission returns empty string (safe default)."""
        assert get_observability_resource_type("Unknown Permission") == ""


# =============================================================================
# Group 3: Payload Builder — Role Generation (TC-OB-06 to TC-OB-11)
# =============================================================================

class TestRoleGeneration:
    """Verify roles generated for observability permissions have correct structure."""

    def test_observability_role_has_no_env_segment(self, base_builder_kwargs):
        """TC-OB-06: View Sessions role resource has no :env/* in path."""
        builder = make_builder({"View Sessions": True}, base_builder_kwargs)
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "view-sessions")

        resource = role["policy"][0]["resources"][0]
        assert ":env/" not in resource
        assert ":session/*" in resource

    def test_observability_role_base_permissions_no_access(self, base_builder_kwargs):
        """TC-OB-07: All observability roles have base_permissions = no_access."""
        perms = {p: True for p in OBSERVABILITY_RESOURCE_MAP}
        builder = make_builder(perms, base_builder_kwargs)
        payload = builder.build()

        for role in payload.roles:
            if role["key"] in [
                "view-sessions", "view-errors", "view-logs", "view-traces",
                "manage-alerts", "manage-observability-dashboards", "talk-to-vega"
            ]:
                assert role["base_permissions"] == "no_access", (
                    f"{role['key']} should have base_permissions='no_access'"
                )

    def test_observability_role_has_view_project_statement(self, base_builder_kwargs):
        """TC-OB-08: Observability roles always include a viewProject statement."""
        builder = make_builder({"View Sessions": True}, base_builder_kwargs)
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "view-sessions")

        assert len(role["policy"]) == 2
        view_proj = role["policy"][1]
        assert view_proj["actions"] == ["viewProject"]
        assert "proj/${roleAttribute/projects}" in view_proj["resources"][0]

    def test_standard_flag_roles_still_have_env_segment(self, base_builder_kwargs):
        """TC-OB-09: Standard flag roles are NOT affected — still use :env/*:flag/*."""
        builder = make_builder({"Create Flags": True}, base_builder_kwargs)
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "create-flags")

        resource = role["policy"][0]["resources"][0]
        assert ":env/*:flag/*" in resource

    def test_mix_of_obs_and_flag_permissions(self, base_builder_kwargs):
        """TC-OB-10: Mix of observability and flag permissions generates correct roles."""
        builder = make_builder(
            {"Create Flags": True, "View Sessions": True, "View Traces": True},
            base_builder_kwargs
        )
        payload = builder.build()
        role_keys = [r["key"] for r in payload.roles]

        assert "create-flags" in role_keys
        assert "view-sessions" in role_keys
        assert "view-traces" in role_keys

        create_flags  = next(r for r in payload.roles if r["key"] == "create-flags")
        view_sessions = next(r for r in payload.roles if r["key"] == "view-sessions")
        view_traces   = next(r for r in payload.roles if r["key"] == "view-traces")

        assert ":env/*:flag/*"  in create_flags["policy"][0]["resources"][0]
        assert ":session/*"     in view_sessions["policy"][0]["resources"][0]
        assert ":trace/*"       in view_traces["policy"][0]["resources"][0]

        # Confirm no env in observability
        assert ":env/" not in view_sessions["policy"][0]["resources"][0]
        assert ":env/" not in view_traces["policy"][0]["resources"][0]

    def test_manage_obs_dashboards_has_all_8_actions(self, base_builder_kwargs):
        """TC-OB-11: Manage Observability Dashboards role has all 8 actions."""
        builder = make_builder({"Manage Observability Dashboards": True}, base_builder_kwargs)
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "manage-observability-dashboards")

        actions = role["policy"][0]["actions"]
        required = [
            "viewObservabilityDashboard", "createObservabilityDashboard",
            "deleteObservabilityDashboard", "addObservabilityGraphToDashboard",
            "removeObservabilityGraphFromDashboard",
            "updateObservabilityDashboardConfiguration",
            "updateObservabilityGraphConfiguration", "updateObservabilitySettings",
        ]
        for action in required:
            assert action in actions, f"Missing action: {action}"

    def test_trace_resource_is_project_scoped_not_env_scoped(self, base_builder_kwargs):
        """
        Critical validation: View Traces uses proj/${projects}:trace/*
        NOT proj/${projects}:env/*:trace/* (the Slack response had this wrong).
        """
        builder = make_builder({"View Traces": True}, base_builder_kwargs)
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "view-traces")

        resource = role["policy"][0]["resources"][0]
        assert resource == "proj/${roleAttribute/projects}:trace/*"
        assert ":env/" not in resource

    def test_vega_resource_is_project_scoped_not_env_scoped(self, base_builder_kwargs):
        """
        Critical validation: Talk to Vega uses proj/${projects}:vega/*
        NOT proj/${projects}:env/*:vega/* (the Slack response had this wrong).
        """
        builder = make_builder({"Talk to Vega": True}, base_builder_kwargs)
        payload = builder.build()
        role = next(r for r in payload.roles if r["key"] == "talk-to-vega")

        resource = role["policy"][0]["resources"][0]
        assert resource == "proj/${roleAttribute/projects}:vega/*"
        assert ":env/" not in resource


# =============================================================================
# Group 4: Edge Cases (TC-OB-12 to TC-OB-14)
# =============================================================================

class TestEdgeCases:

    def test_no_obs_roles_when_none_enabled(self, base_builder_kwargs):
        """TC-OB-12: No observability roles generated when none are checked."""
        builder = make_builder({"Create Flags": True}, base_builder_kwargs)
        payload = builder.build()
        role_keys = [r["key"] for r in payload.roles]

        obs_keys = [
            "view-sessions", "view-errors", "view-logs", "view-traces",
            "manage-alerts", "manage-observability-dashboards", "talk-to-vega"
        ]
        for key in obs_keys:
            assert key not in role_keys, f"Unexpected role '{key}' in output"

    def test_all_obs_permissions_simultaneously(self, base_builder_kwargs):
        """TC-OB-13: All 7 observability permissions can be enabled together."""
        perms = {p: True for p in OBSERVABILITY_RESOURCE_MAP}
        builder = make_builder(perms, base_builder_kwargs)
        payload = builder.build()
        role_keys = [r["key"] for r in payload.roles]

        expected_keys = [
            "view-sessions", "view-errors", "view-logs", "view-traces",
            "manage-alerts", "manage-observability-dashboards", "talk-to-vega"
        ]
        for key in expected_keys:
            assert key in role_keys, f"Missing role '{key}'"

    def test_slugify_produces_correct_role_keys(self, base_builder_kwargs):
        """TC-OB-14: Permission names slugify to correct role keys."""
        perms = {p: True for p in OBSERVABILITY_RESOURCE_MAP}
        builder = make_builder(perms, base_builder_kwargs)
        payload = builder.build()
        role_keys = set(r["key"] for r in payload.roles)

        assert "view-sessions"                   in role_keys
        assert "view-errors"                     in role_keys
        assert "view-logs"                       in role_keys
        assert "view-traces"                     in role_keys
        assert "manage-alerts"                   in role_keys
        assert "manage-observability-dashboards" in role_keys
        assert "talk-to-vega"                    in role_keys


# =============================================================================
# Group 5: Integration (TC-OB-15)
# =============================================================================

class TestIntegration:

    def test_full_payload_obs_plus_flags_plus_env(self, base_builder_kwargs):
        """
        TC-OB-15: Full payload with observability + flags + env permissions.
        Verifies all three permission types coexist correctly.
        """
        base_builder_kwargs["env_matrix_df"] = pd.DataFrame({
            "Team":             ["Developer", "Developer"],
            "Environment":      ["test", "production"],
            "Update Targeting": [True, False],
            "Apply Changes":    [False, True],
        })

        builder = RoleAttributePayloadBuilder(
            project_matrix_df=pd.DataFrame({
                "Team":         ["Developer"],
                "Create Flags": [True],
                "View Sessions":[True],
                "View Errors":  [True],
            }),
            **base_builder_kwargs,
        )
        payload = builder.build()
        role_keys = [r["key"] for r in payload.roles]

        # All three types present
        assert "create-flags"     in role_keys
        assert "view-sessions"    in role_keys
        assert "view-errors"      in role_keys
        assert "update-targeting" in role_keys
        assert "apply-changes"    in role_keys

        # Resource path correctness per type
        def get_resource(key):
            return next(r for r in payload.roles if r["key"] == key)["policy"][0]["resources"][0]

        assert ":env/*:flag/*"   in get_resource("create-flags")
        assert ":session/*"      in get_resource("view-sessions")
        assert ":error/*"        in get_resource("view-errors")
        assert "update-targeting-environments" in get_resource("update-targeting")
        assert "apply-changes-environments"    in get_resource("apply-changes")

        # Observability roles have NO env segment
        assert ":env/" not in get_resource("view-sessions")
        assert ":env/" not in get_resource("view-errors")

        # Teams have env roleAttributes for env permissions but NOT for observability
        team = payload.teams[0]
        attr_keys = [a["key"] for a in team["roleAttributes"]]

        assert "projects"                      in attr_keys
        assert "update-targeting-environments" in attr_keys
        assert "apply-changes-environments"    in attr_keys
        # No session/error attributes — observability is project-scoped
        assert "view-sessions-environments"    not in attr_keys
        assert "view-errors-environments"      not in attr_keys
