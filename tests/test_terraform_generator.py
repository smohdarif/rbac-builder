"""
Tests for Phase 16: Terraform Generator
========================================

Tests that the TerraformGenerator produces valid, correct HCL
matching the 15 test cases defined in docs/phases/phase16/DESIGN.md.

Key things validated:
- ZIP contains the right files
- ${ placeholders are escaped to $${ in HCL
- Resource names use underscores (not hyphens)
- Teams reference roles as TF resource references (not string literals)
- lifecycle ignore_changes block present on all teams
- role_attributes blocks generated correctly

Run with: pytest tests/test_terraform_generator.py -v
"""

import io
import zipfile

import pandas as pd
import pytest

from services.terraform_generator import (
    TerraformGenerator,
    TerraformGenerationError,
    tf_resource_name,
    hcl_list,
    hcl_list_escaped,
)
from services.payload_builder import RoleAttributePayloadBuilder


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_payload():
    """Build a realistic DeployPayload for testing."""
    builder = RoleAttributePayloadBuilder(
        customer_name="Voya",
        project_key="voya-web",
        teams_df=pd.DataFrame({
            "Key":         ["dev", "sre"],
            "Name":        ["Developer", "SRE"],
            "Description": ["Dev team", "SRE team"],
        }),
        env_groups_df=pd.DataFrame({
            "Key":      ["test", "production"],
            "Critical": [False, True],
        }),
        project_matrix_df=pd.DataFrame({
            "Team":         ["Developer", "SRE"],
            "Create Flags": [True,  False],
            "Update Flags": [True,  False],
            "View Project": [True,  True],
        }),
        env_matrix_df=pd.DataFrame({
            "Team":             ["Developer", "Developer", "SRE", "SRE"],
            "Environment":      ["test",      "production", "test", "production"],
            "Update Targeting": [True,  False, False, False],
            "Apply Changes":    [False, True,  False, False],
        }),
    )
    return builder.build()


@pytest.fixture
def generator(sample_payload):
    return TerraformGenerator(sample_payload, "voya-web")


def open_zip(zip_bytes: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(zip_bytes))


def read_file(zf: zipfile.ZipFile, path: str) -> str:
    return zf.read(path).decode("utf-8")


# =============================================================================
# Helper function tests
# =============================================================================

class TestHelpers:

    def test_tf_resource_name_converts_hyphens(self):
        """Hyphens become underscores for valid HCL identifiers."""
        assert tf_resource_name("create-flags")   == "create_flags"
        assert tf_resource_name("voya-web-dev")   == "voya_web_dev"
        assert tf_resource_name("update-targeting") == "update_targeting"

    def test_tf_resource_name_no_change_for_underscores(self):
        """Already valid names are unchanged."""
        assert tf_resource_name("view_project") == "view_project"

    def test_hcl_list_single_value(self):
        assert hcl_list(["voya-web"]) == '["voya-web"]'

    def test_hcl_list_multiple_values(self):
        assert hcl_list(["production", "staging"]) == '["production", "staging"]'

    def test_hcl_list_empty(self):
        assert hcl_list([]) == '[]'

    def test_hcl_list_escaped_replaces_dollar_brace(self):
        """${roleAttribute/...} → $${roleAttribute/...}"""
        resources = ["proj/${roleAttribute/projects}:env/*:flag/*"]
        result = hcl_list_escaped(resources)
        assert "$${roleAttribute/projects}" in result
        # Must NOT have unescaped ${
        assert '"proj/${roleAttribute' not in result

    def test_hcl_list_escaped_multiple_placeholders(self):
        """Both placeholders in an env-scoped resource are escaped."""
        resources = [
            "proj/${roleAttribute/projects}:env/${roleAttribute/update-targeting-environments}:flag/*"
        ]
        result = hcl_list_escaped(resources)
        assert "$${roleAttribute/projects}" in result
        assert "$${roleAttribute/update-targeting-environments}" in result

    def test_hcl_list_escaped_no_placeholder_unchanged(self):
        """Resources without placeholders pass through unchanged."""
        resources = ["proj/my-project:env/production:flag/*"]
        result = hcl_list_escaped(resources)
        assert '"proj/my-project:env/production:flag/*"' in result


# =============================================================================
# Group 1: Package output (TC-TF-01, TC-TF-02)
# =============================================================================

class TestPackageOutput:

    def test_returns_bytes(self, generator):
        """TC-TF-01: generate_package() returns bytes."""
        result = generator.generate_package()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_bytes_is_valid_zip(self, generator):
        """TC-TF-01: Returned bytes open as a valid ZipFile."""
        result = generator.generate_package()
        assert zipfile.is_zipfile(io.BytesIO(result))

    def test_zip_contains_required_files(self, generator):
        """TC-TF-02: ZIP contains all four required files."""
        zf    = open_zip(generator.generate_package())
        names = zf.namelist()
        root  = "voya_terraform"

        assert f"{root}/main.tf"      in names
        assert f"{root}/providers.tf" in names
        assert f"{root}/variables.tf" in names
        assert f"{root}/README.md"    in names

    def test_root_folder_uses_customer_slug(self, sample_payload):
        """Root folder is derived from slugified customer name."""
        gen   = TerraformGenerator(sample_payload, "voya-web")
        zf    = open_zip(gen.generate_package())
        assert all(n.startswith("voya_terraform/") for n in zf.namelist())

    def test_customer_name_with_spaces_slugified(self, sample_payload):
        """Spaces become underscores in folder name."""
        sample_payload.customer_name = "Acme Corp"
        gen = TerraformGenerator(sample_payload, "acme")
        zf  = open_zip(gen.generate_package())
        assert all(n.startswith("acme_corp_terraform/") for n in zf.namelist())

    def test_empty_payload_raises_error(self, sample_payload):
        """TC-TF (edge): empty payload raises TerraformGenerationError."""
        sample_payload.roles = []
        sample_payload.teams = []
        with pytest.raises(TerraformGenerationError):
            TerraformGenerator(sample_payload, "test")


# =============================================================================
# Group 2: providers.tf and variables.tf (TC-TF-03, TC-TF-04)
# =============================================================================

class TestStaticFiles:

    def test_providers_tf_contains_ld_provider(self, generator):
        """TC-TF-03: providers.tf declares the LaunchDarkly provider."""
        zf      = open_zip(generator.generate_package())
        content = read_file(zf, "voya_terraform/providers.tf")

        assert "launchdarkly/launchdarkly" in content
        assert "required_version"          in content
        assert "var.launchdarkly_access_token" in content

    def test_providers_tf_has_version_constraint(self, generator):
        """providers.tf pins a version range."""
        zf      = open_zip(generator.generate_package())
        content = read_file(zf, "voya_terraform/providers.tf")
        assert "~> 2" in content   # version constraint present

    def test_variables_tf_declares_access_token(self, generator):
        """TC-TF-04: variables.tf declares the API token variable."""
        zf      = open_zip(generator.generate_package())
        content = read_file(zf, "voya_terraform/variables.tf")

        assert "launchdarkly_access_token" in content
        assert "sensitive"                 in content
        assert "true"                      in content


# =============================================================================
# Group 3: main.tf — Custom Roles (TC-TF-05, TC-TF-06, TC-TF-07, TC-TF-08)
# =============================================================================

class TestRoleGeneration:

    def _main_tf(self, generator) -> str:
        zf = open_zip(generator.generate_package())
        return read_file(zf, "voya_terraform/main.tf")

    def test_each_role_has_resource_block(self, generator, sample_payload):
        """TC-TF-05: Each role generates a launchdarkly_custom_role resource."""
        content = self._main_tf(generator)
        for role in sample_payload.roles:
            assert f'resource "launchdarkly_custom_role"' in content
            assert f'key              = "{role["key"]}"'  in content

    def test_hyphens_converted_to_underscores_in_resource_name(self, generator):
        """TC-TF-06: Resource name uses underscores, not hyphens."""
        content = self._main_tf(generator)
        # "create-flags" → resource name "create_flags"
        assert 'resource "launchdarkly_custom_role" "create_flags"' in content
        # Must NOT have hyphen in resource name position
        assert 'resource "launchdarkly_custom_role" "create-flags"' not in content

    def test_role_attribute_placeholders_escaped(self, generator):
        """TC-TF-07: ${roleAttribute/...} escaped to $${ in HCL output."""
        content = self._main_tf(generator)
        # All ${ in string values must be $${
        assert "$${roleAttribute/" in content
        # No unescaped ${roleAttribute in strings
        # (allow ${roleAttribute only if preceded by $$ — i.e., $${)
        import re
        # Find all ${roleAttribute occurrences not preceded by another $
        unescaped = re.findall(r'(?<!\$)\$\{roleAttribute', content)
        assert len(unescaped) == 0, f"Found unescaped placeholder(s): {unescaped}"

    def test_policy_statements_match_payload(self, generator, sample_payload):
        """TC-TF-08: Number of policy_statements blocks matches policy length."""
        content = self._main_tf(generator)
        # Count total policy_statements blocks and total policies across all roles
        total_expected = sum(
            len(role.get("policy", []))
            for role in sample_payload.roles
        )
        total_actual = content.count("policy_statements {")
        assert total_actual == total_expected

    def test_base_permissions_no_access_in_all_roles(self, generator, sample_payload):
        """All role resources have base_permissions = "no_access"."""
        content = self._main_tf(generator)
        role_count = len(sample_payload.roles)
        no_access_count = content.count('base_permissions = "no_access"')
        assert no_access_count == role_count

    def test_main_tf_contains_customer_info(self, generator):
        """Header comment includes customer name and project key."""
        content = self._main_tf(generator)
        assert "Voya"     in content
        assert "voya-web" in content


# =============================================================================
# Group 4: main.tf — Teams (TC-TF-09, TC-TF-10, TC-TF-11, TC-TF-12)
# =============================================================================

class TestTeamGeneration:

    def _main_tf(self, generator) -> str:
        zf = open_zip(generator.generate_package())
        return read_file(zf, "voya_terraform/main.tf")

    def test_each_team_has_resource_block(self, generator, sample_payload):
        """TC-TF-09: Each team generates a launchdarkly_team resource."""
        content = self._main_tf(generator)
        for team in sample_payload.teams:
            assert f'resource "launchdarkly_team"' in content
            assert f'key         = "{team["key"]}"' in content

    def test_team_resource_name_uses_underscores(self, generator):
        """TC-TF-09: Team resource name has underscores not hyphens."""
        content = self._main_tf(generator)
        # "voya-web-dev" → "voya_web_dev"
        assert 'resource "launchdarkly_team" "voya_web_dev"' in content
        assert 'resource "launchdarkly_team" "voya-web-dev"' not in content

    def test_team_references_roles_by_tf_reference(self, generator, sample_payload):
        """TC-TF-10: custom_role_keys uses TF references, not string literals."""
        content = self._main_tf(generator)
        # Must have TF resource references
        assert "launchdarkly_custom_role." in content
        assert ".key," in content

        # Must NOT have bare string literals like "create-flags" in custom_role_keys
        # (strings inside role_attributes blocks are fine, but role key strings shouldn't appear)
        # Check that role keys appear as resource references, not standalone strings
        for role in sample_payload.roles:
            resource_ref = f"launchdarkly_custom_role.{tf_resource_name(role['key'])}.key"
            # The reference should exist (if the role is used by a team)
            # We just verify no raw "create-flags", strings in custom_role_keys context
            # by checking the reference format exists
            assert resource_ref in content or role["key"] not in [
                k for team in sample_payload.teams
                for k in team.get("customRoleKeys", [])
            ]

    def test_team_role_attributes_generated(self, generator, sample_payload):
        """TC-TF-11: Team role_attributes blocks appear for each attribute."""
        content = self._main_tf(generator)

        for team in sample_payload.teams:
            for attr in team.get("roleAttributes", []):
                assert f'key    = "{attr["key"]}"' in content
                for val in attr["values"]:
                    assert val in content

    def test_lifecycle_ignore_changes_present(self, generator, sample_payload):
        """TC-TF-12: Every team has lifecycle ignore_changes block."""
        content = self._main_tf(generator)
        team_count = len(sample_payload.teams)
        lifecycle_count = content.count("ignore_changes = [member_ids, maintainers]")
        assert lifecycle_count == team_count, (
            f"Expected {team_count} lifecycle blocks, found {lifecycle_count}"
        )

    def test_projects_role_attribute_present(self, generator):
        """Every team has a 'projects' role_attribute."""
        content = self._main_tf(generator)
        assert 'key    = "projects"' in content
        assert '"voya-web"'          in content


# =============================================================================
# Group 5: Edge Cases (TC-TF-13, TC-TF-14, TC-TF-15)
# =============================================================================

class TestEdgeCases:

    def _main_tf(self, generator) -> str:
        zf = open_zip(generator.generate_package())
        return read_file(zf, "voya_terraform/main.tf")

    def test_unknown_role_keys_excluded_from_team(self, sample_payload):
        """TC-TF-13: Role keys not in payload are omitted from custom_role_keys."""
        # Add a foreign key to a team that doesn't exist as a role
        sample_payload.teams[0]["customRoleKeys"].append("view-teams-global")
        # view-teams-global is NOT in sample_payload.roles

        gen     = TerraformGenerator(sample_payload, "voya-web")
        content = self._main_tf(gen)

        # The reference to the unknown role must NOT appear
        assert "view_teams_global" not in content

    def test_no_unescaped_dollar_brace_in_strings(self, generator):
        """TC-TF-14: No unescaped ${ appears inside HCL string literals."""
        import re
        content = self._main_tf(generator)
        # Find ${roleAttribute not preceded by $ (i.e., not $${roleAttribute)
        unescaped = re.findall(r'(?<!\$)\$\{roleAttribute', content)
        assert len(unescaped) == 0, (
            "Found " + str(len(unescaped)) + " unescaped ${roleAttribute placeholder(s)"
        )

    def test_no_duplicate_resource_blocks(self, generator, sample_payload):
        """TC-TF-15: Exact count of role and team resource blocks."""
        content = self._main_tf(generator)

        role_blocks = content.count('"launchdarkly_custom_role"')
        team_blocks = content.count('"launchdarkly_team"')

        assert role_blocks == sample_payload.get_role_count(), (
            f"Expected {sample_payload.get_role_count()} role blocks, got {role_blocks}"
        )
        assert team_blocks == sample_payload.get_team_count(), (
            f"Expected {sample_payload.get_team_count()} team blocks, got {team_blocks}"
        )

    def test_readme_is_non_empty(self, generator):
        """README.md is generated and contains useful content."""
        zf      = open_zip(generator.generate_package())
        content = read_file(zf, "voya_terraform/README.md")
        assert len(content) > 100
        assert "terraform init"  in content
        assert "terraform apply" in content
        assert "Voya"            in content
