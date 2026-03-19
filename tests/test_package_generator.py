"""
Tests for Phase 13: Client Delivery Package
============================================

Tests for PackageGenerator — verifies that the generated ZIP
contains correctly formatted, API-ready files and a valid deploy script.

Run with: pytest tests/test_package_generator.py -v
"""

import ast
import io
import json
import zipfile

import pandas as pd
import pytest

from services.package_generator import PackageGenerator, PackageGenerationError
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
            "Create Flags": [True, False],
            "Update Flags": [True, False],
            "View Project": [True, True],
        }),
        env_matrix_df=pd.DataFrame({
            "Team":             ["Developer", "Developer", "SRE", "SRE"],
            "Environment":      ["test", "production", "test", "production"],
            "Update Targeting": [True, False, False, False],
            "Apply Changes":    [False, True, False, False],
            "Review Changes":   [True, True, False, False],
        }),
    )
    return builder.build()


@pytest.fixture
def generator(sample_payload):
    """PackageGenerator with the sample payload."""
    return PackageGenerator(sample_payload, "voya-web")


def open_zip(zip_bytes: bytes) -> zipfile.ZipFile:
    """Helper: open ZIP bytes as a ZipFile."""
    return zipfile.ZipFile(io.BytesIO(zip_bytes))


def read_zip_json(zf: zipfile.ZipFile, path: str) -> dict:
    """Helper: read and parse a JSON file from a ZipFile."""
    return json.loads(zf.read(path).decode("utf-8"))


def read_zip_text(zf: zipfile.ZipFile, path: str) -> str:
    """Helper: read a text file from a ZipFile."""
    return zf.read(path).decode("utf-8")


# =============================================================================
# Group 1: PackageGenerator basic output
# =============================================================================

class TestPackageOutput:

    def test_returns_bytes(self, generator):
        """generate_package() returns bytes."""
        result = generator.generate_package()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_bytes_is_valid_zip(self, generator):
        """Returned bytes open as a valid ZipFile."""
        result = generator.generate_package()
        assert zipfile.is_zipfile(io.BytesIO(result))

    def test_zip_contains_required_files(self, generator):
        """ZIP contains all required top-level files."""
        zf = open_zip(generator.generate_package())
        names = zf.namelist()

        root = "voya_rbac_deployment"
        assert any(n.startswith(f"{root}/01_roles/") for n in names)
        assert any(n.startswith(f"{root}/02_teams/") for n in names)
        assert f"{root}/deploy.py"        in names
        assert f"{root}/settings.json"    in names
        assert f"{root}/requirements.txt" in names
        assert f"{root}/rollback.json"    in names
        assert f"{root}/README.md"        in names

    def test_root_folder_uses_customer_slug(self, sample_payload):
        """Root folder is slugified customer name."""
        gen = PackageGenerator(sample_payload, "voya-web")
        zf  = open_zip(gen.generate_package())
        assert all(n.startswith("voya_rbac_deployment/") for n in zf.namelist())

    def test_customer_name_with_spaces_is_slugified(self, sample_payload):
        """Spaces in customer name become underscores in folder name."""
        sample_payload.customer_name = "Acme Corp"
        gen = PackageGenerator(sample_payload, "acme")
        zf  = open_zip(gen.generate_package())
        assert all(n.startswith("acme_corp_rbac_deployment/") for n in zf.namelist())

    def test_empty_payload_raises_error(self, sample_payload):
        """Empty payload raises PackageGenerationError."""
        sample_payload.roles = []
        sample_payload.teams = []
        with pytest.raises(PackageGenerationError):
            PackageGenerator(sample_payload, "test")


# =============================================================================
# Group 2: Role file correctness
# =============================================================================

class TestRoleFiles:

    def test_role_file_count_matches_payload(self, generator, sample_payload):
        """Number of role files equals number of roles in payload."""
        zf         = open_zip(generator.generate_package())
        role_files = [n for n in zf.namelist() if "/01_roles/" in n]
        assert len(role_files) == sample_payload.get_role_count()

    def test_role_files_are_numbered(self, generator, sample_payload):
        """Role files have zero-padded numeric prefix."""
        zf         = open_zip(generator.generate_package())
        role_files = sorted(n for n in zf.namelist() if "/01_roles/" in n)
        for i, path in enumerate(role_files, start=1):
            filename = path.split("/")[-1]
            prefix   = filename.split("_")[0]
            assert prefix == str(i).zfill(2), f"Expected prefix {str(i).zfill(2)}, got {prefix}"

    def test_role_file_is_valid_json(self, generator):
        """Every role file parses as valid JSON."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/01_roles/" in path and path.endswith(".json"):
                content = zf.read(path).decode("utf-8")
                json.loads(content)  # raises if invalid

    def test_role_file_has_required_ld_api_fields(self, generator):
        """Every role file has key, name, base_permissions, policy."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/01_roles/" in path and path.endswith(".json"):
                role = read_zip_json(zf, path)
                assert "key"              in role, f"{path} missing 'key'"
                assert "name"             in role, f"{path} missing 'name'"
                assert "base_permissions" in role, f"{path} missing 'base_permissions'"
                assert "policy"           in role, f"{path} missing 'policy'"

    def test_role_file_base_permissions_is_no_access(self, generator):
        """base_permissions is always 'no_access'."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/01_roles/" in path and path.endswith(".json"):
                role = read_zip_json(zf, path)
                assert role["base_permissions"] == "no_access", (
                    f"{path}: base_permissions should be 'no_access', got {role['base_permissions']}"
                )

    def test_role_file_has_no_internal_fields(self, generator):
        """Role files do not contain rbac-builder internal fields."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/01_roles/" in path and path.endswith(".json"):
                role = read_zip_json(zf, path)
                assert "metadata"          not in role
                assert "deployment_order"  not in role

    def test_role_policy_preserved_exactly(self, generator, sample_payload):
        """Policy statements are preserved without modification."""
        zf         = open_zip(generator.generate_package())
        role_paths = sorted(n for n in zf.namelist() if "/01_roles/" in n and n.endswith(".json"))
        first_role = read_zip_json(zf, role_paths[0])

        # Find matching role in payload
        original = next(r for r in sample_payload.roles if r["key"] == first_role["key"])
        assert first_role["policy"] == original["policy"]

    def test_role_resource_strings_contain_role_attribute_placeholder(self, generator):
        """Role resources contain ${roleAttribute/...} placeholders unchanged."""
        zf = open_zip(generator.generate_package())
        found_placeholder = False
        for path in zf.namelist():
            if "/01_roles/" in path and path.endswith(".json"):
                role = read_zip_json(zf, path)
                for stmt in role["policy"]:
                    for resource in stmt.get("resources", []):
                        if "${roleAttribute/" in resource:
                            found_placeholder = True
        assert found_placeholder, "No role resource contained a roleAttribute placeholder"


# =============================================================================
# Group 3: Team file correctness
# =============================================================================

class TestTeamFiles:

    def test_team_file_count_matches_payload(self, generator, sample_payload):
        """Number of team files equals number of teams in payload."""
        zf         = open_zip(generator.generate_package())
        team_files = [n for n in zf.namelist() if "/02_teams/" in n]
        assert len(team_files) == sample_payload.get_team_count()

    def test_team_file_is_valid_json(self, generator):
        """Every team file parses as valid JSON."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/02_teams/" in path and path.endswith(".json"):
                json.loads(zf.read(path).decode("utf-8"))

    def test_team_file_has_required_ld_api_fields(self, generator):
        """Every team file has key, name, customRoleKeys, roleAttributes."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/02_teams/" in path and path.endswith(".json"):
                team = read_zip_json(zf, path)
                assert "key"            in team
                assert "name"           in team
                assert "customRoleKeys" in team
                assert "roleAttributes" in team

    def test_team_role_attributes_format(self, generator):
        """roleAttributes is a list of {key, values} dicts."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/02_teams/" in path and path.endswith(".json"):
                team = read_zip_json(zf, path)
                assert isinstance(team["roleAttributes"], list)
                for attr in team["roleAttributes"]:
                    assert "key"    in attr
                    assert "values" in attr
                    assert isinstance(attr["values"], list)

    def test_team_has_no_internal_fields(self, generator):
        """Team files do not contain rbac-builder internal fields."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/02_teams/" in path and path.endswith(".json"):
                team = read_zip_json(zf, path)
                assert "metadata"         not in team
                assert "deployment_order" not in team

    def test_team_projects_attribute_present(self, generator):
        """Every team has a 'projects' role attribute."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/02_teams/" in path and path.endswith(".json"):
                team  = read_zip_json(zf, path)
                keys  = [a["key"] for a in team["roleAttributes"]]
                assert "projects" in keys, f"{path}: missing 'projects' roleAttribute"


# =============================================================================
# Group 4: deploy.py correctness
# =============================================================================

class TestDeployScript:

    def test_deploy_script_is_valid_python(self, generator):
        """deploy.py content is valid Python syntax."""
        zf      = open_zip(generator.generate_package())
        root    = "voya_rbac_deployment"
        content = read_zip_text(zf, f"{root}/deploy.py")
        # ast.parse raises SyntaxError if the code is invalid
        ast.parse(content)

    def test_deploy_script_contains_key_sections(self, generator):
        """deploy.py contains required class/function definitions."""
        zf      = open_zip(generator.generate_package())
        root    = "voya_rbac_deployment"
        content = read_zip_text(zf, f"{root}/deploy.py")

        assert "class LDClient"     in content
        assert "class Deployer"     in content
        assert "class DeployResult" in content
        assert "def run(self)"      in content
        assert "settings.json"      in content
        assert "01_roles"           in content
        assert "02_teams"           in content
        assert "rollback.json"      in content
        assert "dry_run"            in content

    def test_deploy_script_contains_customer_info(self, generator):
        """deploy.py header contains customer name and project key."""
        zf      = open_zip(generator.generate_package())
        root    = "voya_rbac_deployment"
        content = read_zip_text(zf, f"{root}/deploy.py")

        assert "Voya"     in content
        assert "voya-web" in content

    def test_settings_json_has_placeholder_api_key(self, generator):
        """settings.json has placeholder API key — client must fill in."""
        zf       = open_zip(generator.generate_package())
        root     = "voya_rbac_deployment"
        settings = read_zip_json(zf, f"{root}/settings.json")

        assert settings["api_key"]  == "YOUR_API_KEY_HERE"
        assert settings["dry_run"]  == False
        assert "base_url"           in settings

    def test_requirements_txt_contains_requests(self, generator):
        """requirements.txt lists requests as a dependency."""
        zf      = open_zip(generator.generate_package())
        root    = "voya_rbac_deployment"
        content = read_zip_text(zf, f"{root}/requirements.txt")
        assert "requests" in content

    def test_rollback_json_is_empty_template(self, generator):
        """rollback.json starts as empty template (populated by deploy.py at runtime)."""
        zf      = open_zip(generator.generate_package())
        root    = "voya_rbac_deployment"
        content = read_zip_text(zf, f"{root}/rollback.json")
        assert content.strip() == "{}"


# =============================================================================
# Group 5: Edge cases
# =============================================================================

class TestEdgeCases:

    def test_more_than_nine_roles_are_zero_padded(self, sample_payload):
        """Files are zero-padded so 10+ roles sort correctly."""
        # Duplicate roles to get 12
        sample_payload.roles = (sample_payload.roles * 3)[:12]
        for i, r in enumerate(sample_payload.roles):
            r["key"] = f"role-{i+1}"

        gen        = PackageGenerator(sample_payload, "test")
        zf         = open_zip(gen.generate_package())
        role_files = sorted(n.split("/")[-1] for n in zf.namelist() if "/01_roles/" in n and n.endswith(".json"))

        assert role_files[0].startswith("01_")
        assert role_files[9].startswith("10_")   # not "1_"
        # Files sort correctly: "01_" < "02_" < ... < "10_" < "11_"
        assert role_files == sorted(role_files)

    def test_role_key_with_hyphens_safe_in_filename(self, generator):
        """Role keys with hyphens work fine in filenames."""
        zf = open_zip(generator.generate_package())
        for path in zf.namelist():
            if "/01_roles/" in path:
                # Should not raise any path/filename errors
                assert path.endswith(".json")

    def test_readme_is_non_empty(self, generator):
        """README.md is generated and non-empty."""
        zf      = open_zip(generator.generate_package())
        root    = "voya_rbac_deployment"
        content = read_zip_text(zf, f"{root}/README.md")
        assert len(content) > 100
        assert "Voya" in content or "voya" in content.lower()


# =============================================================================
# Group 6: Integration — file count and ordering
# =============================================================================

class TestIntegration:

    def test_total_file_count_matches_payload(self, generator, sample_payload):
        """Total JSON files = roles + teams."""
        zf         = open_zip(generator.generate_package())
        role_files = [n for n in zf.namelist() if "/01_roles/" in n and n.endswith(".json")]
        team_files = [n for n in zf.namelist() if "/02_teams/" in n and n.endswith(".json")]

        assert len(role_files) == sample_payload.get_role_count()
        assert len(team_files) == sample_payload.get_team_count()

    def test_roles_folder_comes_before_teams_folder_in_listing(self, generator):
        """01_roles/ is listed before 02_teams/ — correct deployment order."""
        zf    = open_zip(generator.generate_package())
        names = zf.namelist()
        role_indices = [i for i, n in enumerate(names) if "/01_roles/" in n]
        team_indices = [i for i, n in enumerate(names) if "/02_teams/" in n]

        if role_indices and team_indices:
            assert min(role_indices) < min(team_indices)

    def test_all_role_keys_in_team_custom_role_keys_exist_as_files(self, generator):
        """Every key in team customRoleKeys has a corresponding role file."""
        zf = open_zip(generator.generate_package())

        # Collect all role keys from role files
        role_keys = set()
        for path in zf.namelist():
            if "/01_roles/" in path and path.endswith(".json"):
                role = read_zip_json(zf, path)
                role_keys.add(role["key"])

        # Check every team's customRoleKeys references an existing role
        for path in zf.namelist():
            if "/02_teams/" in path and path.endswith(".json"):
                team = read_zip_json(zf, path)
                for key in team["customRoleKeys"]:
                    assert key in role_keys, (
                        f"Team {team['key']} references role '{key}' which has no role file"
                    )
