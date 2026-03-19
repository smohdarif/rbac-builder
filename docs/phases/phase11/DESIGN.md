# Phase 11: Role Attributes Support - Design Document

## Header

| Field | Value |
|-------|-------|
| Phase | 11 |
| Status | ✅ Complete |
| Goal | Support role attribute-based roles and teams for multi-project deployments |
| Dependencies | Phase 3 (Payload Builder), Phase 5 (UI Modules) |

---

## Table of Contents

1. [High-Level Design (HLD)](#high-level-design-hld)
2. [Detailed Low-Level Design (DLD)](#detailed-low-level-design-dld)
3. [Pseudo Logic](#pseudo-logic)
4. [Test Cases](#test-cases)
5. [Implementation Plan](#implementation-plan)

---

## High-Level Design (HLD)

### 1.1 What Are We Building?

A feature to generate **template roles** with role attribute placeholders and **teams** with role attribute values. This enables:

- Single role definitions shared across multiple projects
- Dynamic project/environment scoping at team level
- Enterprise-scale RBAC without role explosion

### 1.2 Current vs New Architecture

```
CURRENT APPROACH (Hardcoded):
┌─────────────────────────────────────────────────────────┐
│ For each team × environment:                            │
│   Create role: "dev-test"                               │
│   Resources: proj/voya:env/test:flag/*   ← Hardcoded   │
└─────────────────────────────────────────────────────────┘
Result: N teams × M environments = N×M roles


NEW APPROACH (Role Attributes):
┌─────────────────────────────────────────────────────────┐
│ Create ONE role template:                               │
│   Role: "update-targeting"                              │
│   Resources: proj/${roleAttribute/projects}:env/*:flag/*│
│                                                         │
│ For each team:                                          │
│   Assign role + roleAttributes: { projects: ["voya"] } │
└─────────────────────────────────────────────────────────┘
Result: Fixed number of roles, teams have different access
```

### 1.3 Feature Toggle

Users should be able to choose between:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Hardcoded** (current) | Project-specific roles | Single project, simple setup |
| **Role Attributes** (new) | Template roles with placeholders | Multi-project, enterprise |

### 1.4 Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   UI Input   │────▶│ PayloadBuilder│────▶│  JSON Output │
│              │     │              │     │              │
│ - Teams      │     │ Mode:        │     │ - Roles      │
│ - Env Groups │     │ ○ Hardcoded  │     │ - Teams      │
│ - Matrix     │     │ ● RoleAttrs  │     │ - RoleAttrs  │
│ - Mode Toggle│     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 1.5 Core Features

| Feature | Description |
|---------|-------------|
| Mode Selection | UI toggle for hardcoded vs role attributes |
| Template Roles | Generate roles with `${roleAttribute/...}` placeholders |
| Team Role Attributes | Generate teams with `roleAttributes` block |
| Multi-Project Support | Optional: configure multiple projects |
| Backward Compatible | Existing hardcoded mode still works |

---

## Detailed Low-Level Design (DLD)

### 2.1 File Changes

```
rbac-builder/
├── core/
│   └── ld_actions.py          # Add role attribute resource builders
├── services/
│   └── payload_builder.py     # Add RoleAttributePayloadBuilder
├── ui/
│   ├── setup_tab.py           # Add mode toggle
│   └── deploy_tab.py          # Handle new payload format
├── models/
│   └── __init__.py            # Add RoleAttributeConfig model
└── tests/
    └── test_role_attributes.py # New test file
```

### 2.2 New Data Models

#### 2.2.1 RoleAttributeConfig

```python
@dataclass
class RoleAttributeConfig:
    """Configuration for role attribute mode."""

    enabled: bool = False
    project_attribute_name: str = "projects"
    environment_attributes: Dict[str, str] = field(default_factory=dict)
    # Maps permission name to attribute name
    # e.g., {"Update Targeting": "updateTargetingEnvironments"}
```

#### 2.2.2 TeamRoleAttributes

```python
@dataclass
class TeamRoleAttributes:
    """Role attributes for a specific team."""

    team_key: str
    attributes: Dict[str, List[str]]
    # e.g., {"projects": ["voya"], "updateTargetingEnvironments": ["test", "prod"]}
```

### 2.3 PayloadBuilder Changes

#### 2.3.1 New Class: RoleAttributePayloadBuilder

```python
class RoleAttributePayloadBuilder:
    """
    Builds template roles with role attribute placeholders
    and teams with role attribute values.
    """

    def __init__(
        self,
        customer_name: str,
        project_key: str,              # Single project (not list)
        teams_df: pd.DataFrame,
        env_groups_df: pd.DataFrame,
        project_matrix: pd.DataFrame,
        env_matrix: pd.DataFrame,
        prefix_team_keys: bool = True,      # Prefix team keys with project
        team_name_format: str = "{project}: {team}",
    ):
        ...

    def build(self) -> DeployPayload:
        """Build template roles and teams with role attributes."""
        ...

    def _build_template_roles(self) -> List[Dict]:
        """Build roles with ${roleAttribute/...} placeholders."""
        ...

    def _build_teams_with_attributes(self, roles: List[Dict]) -> List[Dict]:
        """Build teams with roleAttributes block."""
        ...
```

### 2.4 Resource String Changes

#### 2.4.1 New Resource Builders

```python
def build_role_attribute_resource(attribute_name: str, resource_type: str) -> str:
    """
    Build resource string with role attribute placeholder.

    Example:
        >>> build_role_attribute_resource("projects", "flag")
        'proj/${roleAttribute/projects}:env/*:flag/*'
    """
    return f"proj/${{roleAttribute/{attribute_name}}}:env/*:{resource_type}/*"


def build_env_role_attribute_resource(
    project_attr: str,
    env_attr: str,
    resource_type: str
) -> str:
    """
    Build environment-scoped resource with role attributes.

    Example:
        >>> build_env_role_attribute_resource("projects", "updateTargetingEnvs", "flag")
        'proj/${roleAttribute/projects}:env/${roleAttribute/updateTargetingEnvs}:flag/*'
    """
    return f"proj/${{roleAttribute/{project_attr}}}:env/${{roleAttribute/{env_attr}}}:{resource_type}/*"
```

### 2.5 UI Changes

#### 2.5.1 Setup Tab: Mode Toggle

```python
# In ui/setup_tab.py

def _render_generation_mode():
    """Render toggle for generation mode."""
    st.subheader("Generation Mode")

    mode = st.radio(
        "Select role generation mode:",
        options=["hardcoded", "role_attributes"],
        format_func=lambda x: {
            "hardcoded": "Hardcoded (Project-specific roles)",
            "role_attributes": "Role Attributes (Template roles)"
        }[x],
        help="Role Attributes mode creates reusable template roles"
    )

    st.session_state.generation_mode = mode

    if mode == "role_attributes":
        _render_role_attribute_config()
```

#### 2.5.2 Setup Tab: Project Input (for Role Attributes mode)

```python
def _render_role_attribute_config():
    """Render configuration for role attributes mode."""
    st.caption("Configure project for teams")

    # Single project input (not multiple)
    project_key = st.text_input(
        "Project Key",
        value=st.session_state.get("project_key", ""),
        help="The project key these teams will have access to"
    )

    st.session_state.project_key = project_key.strip()

    # Team key prefix option
    prefix_enabled = st.checkbox(
        "Prefix team keys with project name",
        value=st.session_state.get("prefix_team_keys", True),
        help="Creates 'voya-dev' instead of 'dev' for project isolation"
    )
    st.session_state.prefix_team_keys = prefix_enabled
```

### 2.6 Output JSON Format

#### 2.6.1 Template Role (Role Attributes Mode)

```json
{
  "key": "update-targeting",
  "name": "Update Targeting",
  "description": "Template role for update targeting permissions",
  "policy": [
    {
      "effect": "allow",
      "actions": ["updateOn", "updateRules", "updateTargets", "..."],
      "resources": ["proj/${roleAttribute/projects}:env/${roleAttribute/updateTargetingEnvironments}:flag/*"]
    }
  ]
}
```

#### 2.6.2 Team with Role Attributes

```json
{
  "key": "developers",
  "name": "Developers",
  "description": "Development team",
  "customRoleKeys": [
    "view-project",
    "create-flags",
    "update-targeting",
    "manage-segments"
  ],
  "roleAttributes": [
    {
      "key": "projects",
      "values": ["voya"]
    },
    {
      "key": "updateTargetingEnvironments",
      "values": ["test", "staging"]
    },
    {
      "key": "manageSegmentsEnvironments",
      "values": ["test", "staging"]
    }
  ]
}
```

### 2.7 Permission to Attribute Mapping

```python
# Maps UI permission names to role attribute names
PERMISSION_ATTRIBUTE_MAP = {
    # Project-level (all use "projects" attribute)
    "Create Flags": "projects",
    "Update Flags": "projects",
    "Archive Flags": "projects",
    "View Project": "projects",

    # Environment-level (each has own attribute)
    "Update Targeting": "updateTargetingEnvironments",
    "Review Changes": "reviewChangesEnvironments",
    "Apply Changes": "applyChangesEnvironments",
    "Manage Segments": "manageSegmentsEnvironments",
    "Manage Experiments": "manageExperimentsEnvironments",
    "View SDK Key": "viewSdkKeyEnvironments",
}
```

---

## Pseudo Logic

### 3.1 Main Build Flow (Role Attributes Mode)

```
FUNCTION build_role_attributes_payload():

    # Step 1: Determine which permissions are used
    used_project_permissions = get_used_project_permissions(project_matrix)
    used_env_permissions = get_used_env_permissions(env_matrix)

    # Step 2: Build template roles (one per permission type)
    template_roles = []

    FOR EACH permission IN used_project_permissions:
        role = build_project_template_role(permission)
        template_roles.append(role)

    FOR EACH permission IN used_env_permissions:
        role = build_env_template_role(permission)
        template_roles.append(role)

    # Step 3: Build teams with role attributes
    teams = []

    FOR EACH team IN teams_df:
        team_roles = get_team_roles(team, project_matrix, env_matrix)
        team_attributes = build_team_attributes(team, env_matrix, env_groups)

        team_json = {
            "key": team.key,
            "name": team.name,
            "customRoleKeys": team_roles,
            "roleAttributes": team_attributes
        }
        teams.append(team_json)

    RETURN DeployPayload(roles=template_roles, teams=teams)
```

### 3.2 Build Project Template Role

```
FUNCTION build_project_template_role(permission_name):

    actions = get_project_actions(permission_name)

    role = {
        "key": slugify(permission_name),  # e.g., "create-flags"
        "name": permission_name,
        "description": f"Template role for {permission_name}",
        "policy": [{
            "effect": "allow",
            "actions": actions,
            "resources": ["proj/${roleAttribute/projects}:env/*:flag/*"]
        }]
    }

    # Add viewProject for all roles
    IF permission_name != "View Project":
        role["policy"].append({
            "effect": "allow",
            "actions": ["viewProject"],
            "resources": ["proj/${roleAttribute/projects}"]
        })

    RETURN role
```

### 3.3 Build Environment Template Role

```
FUNCTION build_env_template_role(permission_name):

    actions = get_env_actions(permission_name)
    attribute_name = PERMISSION_ATTRIBUTE_MAP[permission_name]

    # Determine resource type
    IF permission_name == "Manage Segments":
        resource_type = "segment"
    ELSE IF permission_name == "Manage Experiments":
        resource_type = "experiment"
    ELSE:
        resource_type = "flag"

    role = {
        "key": slugify(permission_name),
        "name": permission_name,
        "description": f"Template role for {permission_name}",
        "policy": [{
            "effect": "allow",
            "actions": actions,
            "resources": [
                f"proj/${{roleAttribute/projects}}:env/${{roleAttribute/{attribute_name}}}:{resource_type}/*"
            ]
        }]
    }

    RETURN role
```

### 3.4 Build Team Attributes

```
FUNCTION build_team_attributes(team, env_matrix, project_key):

    attributes = []

    # Always add projects attribute with SINGLE project (not list)
    attributes.append({
        "key": "projects",
        "values": [project_key]  # ONE project only for isolation
    })

    # For each environment permission, add attribute with allowed environments
    FOR EACH permission IN ENV_PERMISSIONS:
        attribute_name = PERMISSION_ATTRIBUTE_MAP[permission]

        # Find which environments this team has this permission for
        allowed_envs = []
        FOR EACH row IN env_matrix WHERE row.Team == team.name:
            IF row[permission] == True:
                allowed_envs.append(row.Environment)

        IF allowed_envs:
            attributes.append({
                "key": attribute_name,
                "values": allowed_envs
            })

    RETURN attributes
```

### 3.5 Get Team Roles

```
FUNCTION get_team_roles(team, project_matrix, env_matrix):

    roles = []

    # Check project permissions
    team_project_row = project_matrix[project_matrix.Team == team.name]
    FOR EACH permission IN PROJECT_PERMISSIONS:
        IF team_project_row[permission] == True:
            roles.append(slugify(permission))

    # Check env permissions (add role if team has it for ANY environment)
    team_env_rows = env_matrix[env_matrix.Team == team.name]
    FOR EACH permission IN ENV_PERMISSIONS:
        IF ANY(team_env_rows[permission] == True):
            roles.append(slugify(permission))

    RETURN unique(roles)
```

---

## Test Cases

### 4.1 Unit Tests: Resource Builders

```python
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

    def test_build_env_role_attribute_resource(self):
        """Test building env-scoped resource with two attributes."""
        resource = build_env_role_attribute_resource(
            "projects",
            "updateTargetingEnvironments",
            "flag"
        )
        expected = "proj/${roleAttribute/projects}:env/${roleAttribute/updateTargetingEnvironments}:flag/*"
        assert resource == expected

    def test_build_env_role_attribute_resource_experiment(self):
        """Test building experiment resource with role attributes."""
        resource = build_env_role_attribute_resource(
            "projects",
            "manageExperimentsEnvironments",
            "experiment"
        )
        expected = "proj/${roleAttribute/projects}:env/${roleAttribute/manageExperimentsEnvironments}:experiment/*"
        assert resource == expected
```

### 4.2 Unit Tests: Template Role Generation

```python
class TestTemplateRoleGeneration:
    """Tests for generating template roles."""

    def test_generate_project_template_role(self):
        """Test generating a project-level template role."""
        role = build_project_template_role("Create Flags")

        assert role["key"] == "create-flags"
        assert role["name"] == "Create Flags"
        assert "${roleAttribute/projects}" in role["policy"][0]["resources"][0]
        assert "createFlag" in role["policy"][0]["actions"]

    def test_generate_env_template_role(self):
        """Test generating an environment-level template role."""
        role = build_env_template_role("Update Targeting")

        assert role["key"] == "update-targeting"
        assert "${roleAttribute/projects}" in role["policy"][0]["resources"][0]
        assert "${roleAttribute/updateTargetingEnvironments}" in role["policy"][0]["resources"][0]

    def test_template_role_includes_view_project(self):
        """Test that non-view roles include viewProject action."""
        role = build_project_template_role("Create Flags")

        # Should have a second policy for viewProject
        view_policy = [p for p in role["policy"] if "viewProject" in p["actions"]]
        assert len(view_policy) == 1

    def test_segment_template_uses_segment_resource(self):
        """Test that segment permission uses segment resource type."""
        role = build_env_template_role("Manage Segments")

        assert ":segment/*" in role["policy"][0]["resources"][0]
        assert ":flag/*" not in role["policy"][0]["resources"][0]

    def test_experiment_template_uses_experiment_resource(self):
        """Test that experiment permission uses experiment resource type."""
        role = build_env_template_role("Manage Experiments")

        assert ":experiment/*" in role["policy"][0]["resources"][0]
```

### 4.3 Unit Tests: Team Role Attributes

```python
class TestTeamRoleAttributes:
    """Tests for generating team role attributes."""

    @pytest.fixture
    def sample_env_matrix(self):
        return pd.DataFrame({
            "Team": ["Developer", "Developer", "QA", "QA"],
            "Environment": ["test", "production", "test", "production"],
            "Update Targeting": [True, False, True, True],
            "Manage Segments": [True, False, True, False],
        })

    def test_build_team_attributes_includes_projects(self, sample_env_matrix):
        """Test that team attributes always include projects."""
        attrs = build_team_attributes(
            team={"name": "Developer"},
            env_matrix=sample_env_matrix,
            project_key="voya"  # Single project, not list
        )

        projects_attr = [a for a in attrs if a["key"] == "projects"]
        assert len(projects_attr) == 1
        assert projects_attr[0]["values"] == ["voya"]  # Single project in list

    def test_build_team_attributes_env_permissions(self, sample_env_matrix):
        """Test that env permissions create correct attributes."""
        attrs = build_team_attributes(
            team={"name": "Developer"},
            env_matrix=sample_env_matrix,
            project_key="voya"
        )

        targeting_attr = [a for a in attrs if a["key"] == "updateTargetingEnvironments"]
        assert len(targeting_attr) == 1
        assert targeting_attr[0]["values"] == ["test"]  # Only test, not production

    def test_build_team_attributes_multiple_envs(self, sample_env_matrix):
        """Test team with permission in multiple environments."""
        attrs = build_team_attributes(
            team={"name": "QA"},
            env_matrix=sample_env_matrix,
            project_key="voya"
        )

        targeting_attr = [a for a in attrs if a["key"] == "updateTargetingEnvironments"]
        assert set(targeting_attr[0]["values"]) == {"test", "production"}

    def test_build_team_attributes_no_permission_no_attribute(self, sample_env_matrix):
        """Test that missing permissions don't create attributes."""
        # Developer has no Manage Segments in production
        attrs = build_team_attributes(
            team={"name": "Developer"},
            env_matrix=sample_env_matrix,
            project_key="voya"
        )

        segments_attr = [a for a in attrs if a["key"] == "manageSegmentsEnvironments"]
        assert len(segments_attr) == 1
        assert segments_attr[0]["values"] == ["test"]  # Only test
```

### 4.4 Integration Tests: Full Payload Generation

```python
class TestRoleAttributePayloadBuilder:
    """Integration tests for the full payload builder."""

    @pytest.fixture
    def builder(self, sample_teams, sample_env_groups, sample_project_matrix, sample_env_matrix):
        return RoleAttributePayloadBuilder(
            customer_name="test-customer",
            project_key="voya",              # Single project
            teams_df=sample_teams,
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
            prefix_team_keys=True,           # Prefix for isolation
            team_name_format="{project}: {team}",
        )

    def test_build_returns_deploy_payload(self, builder):
        """Test that build returns a DeployPayload object."""
        payload = builder.build()

        assert isinstance(payload, DeployPayload)
        assert hasattr(payload, "roles")
        assert hasattr(payload, "teams")

    def test_build_creates_template_roles(self, builder):
        """Test that template roles are created."""
        payload = builder.build()

        # Should have roles with ${roleAttribute/...} in resources
        for role in payload.roles:
            has_placeholder = any(
                "${roleAttribute/" in r
                for p in role["policy"]
                for r in p["resources"]
            )
            assert has_placeholder, f"Role {role['key']} missing role attribute placeholder"

    def test_build_creates_teams_with_role_attributes(self, builder):
        """Test that teams have roleAttributes."""
        payload = builder.build()

        for team in payload.teams:
            assert "roleAttributes" in team
            assert isinstance(team["roleAttributes"], list)
            assert len(team["roleAttributes"]) > 0

    def test_build_teams_have_correct_roles(self, builder):
        """Test that teams are assigned the correct roles."""
        payload = builder.build()

        for team in payload.teams:
            # All teams should have some roles
            assert len(team["customRoleKeys"]) > 0
            # Roles should match template role keys
            role_keys = [r["key"] for r in payload.roles]
            for team_role in team["customRoleKeys"]:
                assert team_role in role_keys

    def test_build_no_duplicate_roles(self, builder):
        """Test that no duplicate roles are created."""
        payload = builder.build()

        role_keys = [r["key"] for r in payload.roles]
        assert len(role_keys) == len(set(role_keys))

    def test_payload_json_serializable(self, builder):
        """Test that payload can be serialized to JSON."""
        payload = builder.build()

        import json
        json_str = payload.to_json()
        parsed = json.loads(json_str)

        assert "custom_roles" in parsed or "roles" in parsed
        assert "teams" in parsed
```

### 4.5 Edge Case Tests

```python
class TestRoleAttributeEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_teams_returns_empty_payload(self):
        """Test handling of empty teams DataFrame."""
        builder = RoleAttributePayloadBuilder(
            customer_name="test",
            project_key="proj",           # Single project
            teams_df=pd.DataFrame({"Name": [], "Key": []}),
            env_groups_df=sample_env_groups,
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame(),
            prefix_team_keys=True,
        )

        payload = builder.build()
        assert len(payload.roles) == 0
        assert len(payload.teams) == 0

    def test_no_permissions_team_gets_view_only(self):
        """Test team with no permissions only gets view role."""
        # Matrix with all False except View Project
        project_matrix = pd.DataFrame({
            "Team": ["ReadOnly"],
            "Create Flags": [False],
            "View Project": [True],
        })

        builder = RoleAttributePayloadBuilder(project_key="voya", ...)
        payload = builder.build()

        readonly_team = [t for t in payload.teams if t["key"] == "voya-readonly"][0]
        assert "view-project" in readonly_team["customRoleKeys"]
        assert len(readonly_team["customRoleKeys"]) == 1

    def test_single_project_enforced(self):
        """Test that each team has exactly ONE project in roleAttributes."""
        builder = RoleAttributePayloadBuilder(
            project_key="voya",
            prefix_team_keys=True,
            ...
        )

        payload = builder.build()

        for team in payload.teams:
            projects_attr = [a for a in team["roleAttributes"] if a["key"] == "projects"]
            # Must be exactly ONE project for isolation
            assert len(projects_attr[0]["values"]) == 1
            assert projects_attr[0]["values"] == ["voya"]

    def test_special_characters_in_project_key(self):
        """Test handling of special characters in project keys."""
        builder = RoleAttributePayloadBuilder(
            project_key="my-project_v2",   # Single project with special chars
            prefix_team_keys=True,
            ...
        )

        payload = builder.build()
        # Should not error
        assert payload is not None
        # Team key should be prefixed
        assert payload.teams[0]["key"].startswith("my-project_v2-")
```

### 4.6 Comparison Tests

```python
class TestModeComparison:
    """Tests comparing hardcoded vs role attributes modes."""

    def test_same_permissions_different_output(self, sample_data):
        """Test that same input produces different outputs based on mode."""
        hardcoded_builder = PayloadBuilder(mode="hardcoded", **sample_data)
        roleattr_builder = RoleAttributePayloadBuilder(**sample_data)

        hardcoded_payload = hardcoded_builder.build()
        roleattr_payload = roleattr_builder.build()

        # Role attributes mode should have fewer roles
        assert len(roleattr_payload.roles) < len(hardcoded_payload.roles)

        # But teams should have roleAttributes in role attr mode
        for team in roleattr_payload.teams:
            assert "roleAttributes" in team

        for team in hardcoded_payload.teams:
            assert "roleAttributes" not in team

    def test_role_count_comparison(self, sample_data):
        """Test that role attributes mode reduces role count."""
        # 2 teams × 2 environments = 4 env roles + 2 project roles = 6 (hardcoded)
        # Role attributes: ~5-7 template roles regardless of team count

        hardcoded = PayloadBuilder(mode="hardcoded", **sample_data).build()
        roleattr = RoleAttributePayloadBuilder(**sample_data).build()

        # Hardcoded creates N×M roles
        # Role attributes creates fixed number
        print(f"Hardcoded roles: {len(hardcoded.roles)}")
        print(f"Role attribute roles: {len(roleattr.roles)}")

        # With more teams/envs, the difference would be larger
        assert len(roleattr.roles) <= len(hardcoded.roles)
```

---

## Implementation Plan

### 5.1 Implementation Steps

| Step | Task | File | Estimated Complexity |
|------|------|------|---------------------|
| 1 | Add role attribute resource builders | `core/ld_actions.py` | Low |
| 2 | Add permission-to-attribute mapping | `core/ld_actions.py` | Low |
| 3 | Create RoleAttributePayloadBuilder class | `services/payload_builder.py` | Medium |
| 4 | Implement template role generation | `services/payload_builder.py` | Medium |
| 5 | Implement team role attributes generation | `services/payload_builder.py` | Medium |
| 6 | Add mode toggle to Setup UI | `ui/setup_tab.py` | Low |
| 7 | Update Deploy tab to handle new mode | `ui/deploy_tab.py` | Low |
| 8 | Write unit tests | `tests/test_role_attributes.py` | Medium |
| 9 | Write integration tests | `tests/test_role_attributes.py` | Medium |
| 10 | Update documentation | `docs/` | Low |

### 5.2 Implementation Order

```
Phase 1: Core Logic
├── Step 1: Resource builders
├── Step 2: Permission mapping
└── Step 3: RoleAttributePayloadBuilder shell

Phase 2: Generation Logic
├── Step 4: Template role generation
└── Step 5: Team attributes generation

Phase 3: UI Integration
├── Step 6: Mode toggle
└── Step 7: Deploy handling

Phase 4: Testing & Docs
├── Step 8: Unit tests
├── Step 9: Integration tests
└── Step 10: Documentation
```

### 5.3 Rollback Plan

If issues arise:
1. Mode toggle defaults to "hardcoded"
2. Existing hardcoded flow unchanged
3. Role attributes is opt-in feature

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [Phase 10](../phase10/) | [All Phases](../) | - |

---

*Last updated: 2026-03-16*
