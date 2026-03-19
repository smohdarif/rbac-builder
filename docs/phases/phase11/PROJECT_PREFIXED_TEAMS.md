# Project-Prefixed Teams Design Document

## Overview

| Field | Value |
|-------|-------|
| Feature | Project-Prefixed Teams |
| Status | 📋 Planning |
| Parent | Phase 11 (Role Attributes) |
| Goal | Ensure project isolation by prefixing team keys with project name |

## Problem Statement

With the current Role Attributes implementation, a single team (e.g., `dev`) could have multiple projects in its `roleAttributes.projects` array:

```json
{
  "key": "dev",
  "roleAttributes": [
    {"key": "projects", "values": ["voya", "mobile", "website"]}
  ]
}
```

**Problem:** All members of this team can see ALL projects, which breaks project isolation.

## Solution

Follow the ps-terraform-private pattern: **prefix team keys with project name** and assign **ONE project per team**.

```json
{
  "key": "voya-dev",
  "name": "Voya: Developer",
  "roleAttributes": [
    {"key": "projects", "values": ["voya"]}
  ]
}
```

---

# High-Level Design (HLD)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LaunchDarkly ACCOUNT                             │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  TEMPLATE ROLES (Shared - Created Once)                            │ │
│  │                                                                     │ │
│  │  • update-targeting     → proj/${roleAttribute/projects}:env/...   │ │
│  │  • create-flags         → proj/${roleAttribute/projects}:env/...   │ │
│  │  • manage-segments      → proj/${roleAttribute/projects}:env/...   │ │
│  │  • view-project         → proj/${roleAttribute/projects}           │ │
│  │                                                                     │ │
│  │  (These roles work for ANY team, ANY project)                      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  PROJECT-PREFIXED TEAMS (One per project × role type)              │ │
│  │                                                                     │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │ │
│  │  │ voya-dev         │  │ mobile-dev       │  │ website-dev      │ │ │
│  │  │ projects: [voya] │  │ projects: [mobile]│ │ projects: [web]  │ │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘ │ │
│  │                                                                     │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │ │
│  │  │ voya-qa          │  │ mobile-qa        │  │ website-qa       │ │ │
│  │  │ projects: [voya] │  │ projects: [mobile]│ │ projects: [web]  │ │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  PROJECTS                                                          │ │
│  │                                                                     │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐                     │ │
│  │  │  voya    │    │  mobile  │    │  website │                     │ │
│  │  └──────────┘    └──────────┘    └──────────┘                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User Input (Setup Tab)                    Generated Output
─────────────────────                     ────────────────

Project: "voya"                           Template Roles:
Teams: [dev, qa, release]        ───►     • update-targeting
Env Groups: [Test, Production]            • create-flags
                                          • manage-segments

                                          Teams:
                                          • voya-dev (projects: ["voya"])
                                          • voya-qa (projects: ["voya"])
                                          • voya-release (projects: ["voya"])
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Team key format | `{project}-{team}` | Matches ps-terraform-private pattern |
| Team name format | `{Project}: {Team}` | Clear identification in UI |
| Projects per team | ONE | Ensures project isolation |
| Roles | Shared templates | Reduces role count, consistent permissions |

---

# Detailed Low-Level Design (DLD)

## 1. Configuration Options

### New Session State Variables

```python
# ui/setup_tab.py

# Generation mode options (existing)
st.session_state.generation_mode = "hardcoded" | "role_attributes"

# NEW: Team key format options
st.session_state.team_key_format = "plain" | "project_prefixed"
# - plain: "dev" (current behavior)
# - project_prefixed: "voya-dev" (new behavior)

st.session_state.team_name_format = "{team}" | "{project}: {team}"
# - "{team}": "Developer"
# - "{project}: {team}": "Voya: Developer"
```

### UI Options

```
┌─────────────────────────────────────────────────────────────┐
│  Generation Mode                                             │
│  ○ Hardcoded (Project-specific roles)                       │
│  ● Role Attributes (Template roles)                          │
│                                                              │
│  Team Isolation (only shown when Role Attributes selected)  │
│  ☑ Prefix team keys with project name                       │
│    Example: "dev" → "voya-dev"                              │
│                                                              │
│  Team Name Format                                            │
│  ○ Plain: "Developer"                                        │
│  ● Prefixed: "Voya: Developer"                              │
└─────────────────────────────────────────────────────────────┘
```

## 2. Payload Builder Changes

### Modified RoleAttributePayloadBuilder Class

```python
# services/payload_builder.py

class RoleAttributePayloadBuilder:
    def __init__(
        self,
        customer_name: str,
        project_key: str,              # Single project (not list)
        teams_df,
        env_groups_df,
        project_matrix_df,
        env_matrix_df,
        # NEW parameters:
        prefix_team_keys: bool = True,      # Default: prefix enabled
        team_name_format: str = "{project}: {team}",
    ):
        self.customer_name = customer_name
        self.project_key = project_key      # ONE project
        self.prefix_team_keys = prefix_team_keys
        self.team_name_format = team_name_format
        # ... rest of init
```

### Team Key Generation

```python
def _build_team_key(self, base_key: str) -> str:
    """
    Build team key with optional project prefix.

    Args:
        base_key: Original team key (e.g., "dev")

    Returns:
        Prefixed key if enabled (e.g., "voya-dev")
    """
    if self.prefix_team_keys:
        return f"{self.project_key}-{base_key}"
    return base_key


def _build_team_name(self, base_name: str) -> str:
    """
    Build team display name with optional project prefix.

    Args:
        base_name: Original team name (e.g., "Developer")

    Returns:
        Formatted name (e.g., "Voya: Developer")
    """
    if self.team_name_format == "{project}: {team}":
        # Capitalize project key for display
        project_display = self.project_key.replace("-", " ").title()
        return f"{project_display}: {base_name}"
    return base_name
```

### Role Attributes Generation

```python
def _build_team_role_attributes(self, team_name: str) -> List[Dict[str, Any]]:
    """
    Build roleAttributes for a team.

    Key change: projects array contains ONLY the single project.
    """
    attributes = []

    # ONE project only (not a list of all projects)
    attributes.append({
        "key": "projects",
        "values": [self.project_key]  # Single project!
    })

    # Environment attributes (unchanged from current implementation)
    # ... rest of method

    return attributes
```

## 3. Output Format

### Team JSON Structure (Before)

```json
{
  "key": "dev",
  "name": "Developer",
  "customRoleKeys": ["update-targeting", "create-flags"],
  "roleAttributes": [
    {"key": "projects", "values": ["voya", "mobile", "website"]}
  ]
}
```

### Team JSON Structure (After - Project Prefixed)

```json
{
  "key": "voya-dev",
  "name": "Voya: Developer",
  "customRoleKeys": ["update-targeting", "create-flags"],
  "roleAttributes": [
    {"key": "projects", "values": ["voya"]}
  ]
}
```

## 4. File Changes Required

| File | Changes |
|------|---------|
| `ui/setup_tab.py` | Add team key format options UI |
| `services/payload_builder.py` | Add prefix logic to `RoleAttributePayloadBuilder` |
| `ui/deploy_tab.py` | Pass new options to builder |
| `tests/test_role_attributes.py` | Add tests for prefixed teams |

---

# Pseudo Logic

## 1. Setup Tab - Initialize Options

```python
def _initialize_session_state():
    # ... existing code ...

    # NEW: Team prefix options (default to prefixed for isolation)
    if "prefix_team_keys" not in st.session_state:
        st.session_state.prefix_team_keys = True

    if "team_name_format" not in st.session_state:
        st.session_state.team_name_format = "{project}: {team}"
```

## 2. Setup Tab - Render Options

```python
def _render_team_isolation_options():
    """Only shown when role_attributes mode is selected."""

    IF st.session_state.generation_mode == "role_attributes":
        st.subheader("Team Isolation")

        # Checkbox for prefixing
        prefix_enabled = st.checkbox(
            "Prefix team keys with project name",
            value=st.session_state.prefix_team_keys,
            help="Creates 'voya-dev' instead of 'dev' for project isolation"
        )
        st.session_state.prefix_team_keys = prefix_enabled

        IF prefix_enabled:
            # Show example
            project = st.session_state.get("project", "voya")
            st.caption(f"Example: 'dev' → '{project}-dev'")

            # Name format option
            name_format = st.radio(
                "Team name format",
                options=["{team}", "{project}: {team}"],
                format_func=lambda x: {
                    "{team}": "Plain (Developer)",
                    "{project}: {team}": f"Prefixed ({project.title()}: Developer)"
                }[x]
            )
            st.session_state.team_name_format = name_format
```

## 3. Payload Builder - Build Teams

```python
def _build_teams_with_attributes(self, roles):
    teams = []
    role_keys = {role["key"] for role in roles}

    FOR each team_row in self.teams_df:
        base_key = team_row["Key"]
        base_name = team_row["Name"]
        base_desc = team_row["Description"]

        # Apply prefix if enabled
        IF self.prefix_team_keys:
            team_key = f"{self.project_key}-{base_key}"
            team_name = self._format_team_name(base_name)
        ELSE:
            team_key = base_key
            team_name = base_name

        # Get roles for this team
        team_roles = self._get_team_role_keys(base_name, role_keys)

        # Build role attributes with SINGLE project
        role_attributes = [
            {"key": "projects", "values": [self.project_key]}
        ]

        # Add environment-specific attributes
        env_attributes = self._build_env_attributes(base_name)
        role_attributes.extend(env_attributes)

        teams.append({
            "key": team_key,
            "name": team_name,
            "description": base_desc,
            "customRoleKeys": team_roles,
            "roleAttributes": role_attributes
        })

    RETURN teams


def _format_team_name(self, base_name):
    IF self.team_name_format == "{project}: {team}":
        project_display = self.project_key.replace("-", " ").title()
        RETURN f"{project_display}: {base_name}"
    ELSE:
        RETURN base_name
```

## 4. Deploy Tab - Pass Options to Builder

```python
def _render_ld_payload_generator(customer_name, validation_result):
    # ... existing code ...

    IF st.button("Generate LaunchDarkly Payloads"):
        IF generation_mode == "role_attributes":
            # Get single project (not list)
            project_key = st.session_state.get("project", "default")

            # NEW: Get prefix options
            prefix_team_keys = st.session_state.get("prefix_team_keys", True)
            team_name_format = st.session_state.get("team_name_format", "{project}: {team}")

            builder = RoleAttributePayloadBuilder(
                customer_name=customer_name,
                project_key=project_key,          # Single project
                teams_df=st.session_state.teams,
                env_groups_df=st.session_state.env_groups,
                project_matrix_df=st.session_state.project_matrix,
                env_matrix_df=st.session_state.env_matrix,
                prefix_team_keys=prefix_team_keys,
                team_name_format=team_name_format,
            )

            payload = builder.build()
```

---

# Test Cases

## Test File: `tests/test_project_prefixed_teams.py`

### 1. Team Key Prefix Tests

```python
class TestTeamKeyPrefix:
    """Tests for project-prefixed team keys."""

    def test_team_key_with_prefix_enabled(self):
        """Test that team keys are prefixed with project name."""
        builder = RoleAttributePayloadBuilder(
            project_key="voya",
            prefix_team_keys=True,
            # ... other params
        )
        payload = builder.build()

        # Find dev team
        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["key"] == "voya-dev"

    def test_team_key_without_prefix(self):
        """Test that team keys remain plain when prefix disabled."""
        builder = RoleAttributePayloadBuilder(
            project_key="voya",
            prefix_team_keys=False,
            # ... other params
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if t["key"] == "dev")
        assert dev_team["key"] == "dev"

    def test_all_teams_have_project_prefix(self):
        """Test all teams get the project prefix."""
        builder = RoleAttributePayloadBuilder(
            project_key="mobile",
            prefix_team_keys=True,
            # ... other params with teams: dev, qa, release
        )
        payload = builder.build()

        for team in payload.teams:
            assert team["key"].startswith("mobile-")

    def test_prefix_handles_special_characters(self):
        """Test prefix with project keys containing hyphens."""
        builder = RoleAttributePayloadBuilder(
            project_key="voya-web",
            prefix_team_keys=True,
            # ... other params
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["key"] == "voya-web-dev"
```

### 2. Team Name Format Tests

```python
class TestTeamNameFormat:
    """Tests for team display name formatting."""

    def test_team_name_with_project_prefix(self):
        """Test team name includes project prefix."""
        builder = RoleAttributePayloadBuilder(
            project_key="voya",
            prefix_team_keys=True,
            team_name_format="{project}: {team}",
            # ... other params
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["name"] == "Voya: Developer"

    def test_team_name_plain_format(self):
        """Test plain team name when format is {team}."""
        builder = RoleAttributePayloadBuilder(
            project_key="voya",
            prefix_team_keys=True,
            team_name_format="{team}",
            # ... other params
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["name"] == "Developer"

    def test_project_name_capitalized(self):
        """Test project name is properly capitalized in team name."""
        builder = RoleAttributePayloadBuilder(
            project_key="mobile-app",
            team_name_format="{project}: {team}",
            # ... other params
        )
        payload = builder.build()

        dev_team = next(t for t in payload.teams if "dev" in t["key"])
        assert dev_team["name"] == "Mobile App: Developer"
```

### 3. Role Attributes - Single Project Tests

```python
class TestSingleProjectRoleAttributes:
    """Tests for single project in roleAttributes."""

    def test_projects_attribute_has_single_value(self):
        """Test that projects roleAttribute contains only ONE project."""
        builder = RoleAttributePayloadBuilder(
            project_key="voya",
            prefix_team_keys=True,
            # ... other params
        )
        payload = builder.build()

        for team in payload.teams:
            projects_attr = next(
                a for a in team["roleAttributes"]
                if a["key"] == "projects"
            )
            assert len(projects_attr["values"]) == 1
            assert projects_attr["values"] == ["voya"]

    def test_projects_attribute_matches_project_key(self):
        """Test projects value matches the configured project key."""
        builder = RoleAttributePayloadBuilder(
            project_key="mobile-app",
            prefix_team_keys=True,
            # ... other params
        )
        payload = builder.build()

        for team in payload.teams:
            projects_attr = next(
                a for a in team["roleAttributes"]
                if a["key"] == "projects"
            )
            assert projects_attr["values"] == ["mobile-app"]

    def test_each_team_isolated_to_one_project(self):
        """Test that each team can only access one project."""
        builder = RoleAttributePayloadBuilder(
            project_key="voya",
            prefix_team_keys=True,
            # ... other params
        )
        payload = builder.build()

        for team in payload.teams:
            projects_attr = next(
                a for a in team["roleAttributes"]
                if a["key"] == "projects"
            )
            # Only one project - isolation guaranteed
            assert len(projects_attr["values"]) == 1
```

### 4. Integration Tests

```python
class TestProjectPrefixedTeamsIntegration:
    """Integration tests for the full workflow."""

    def test_full_payload_structure(self):
        """Test complete payload with prefixed teams."""
        builder = RoleAttributePayloadBuilder(
            customer_name="acme",
            project_key="voya",
            prefix_team_keys=True,
            team_name_format="{project}: {team}",
            teams_df=sample_teams,          # dev, qa, release
            env_groups_df=sample_env_groups,
            project_matrix_df=sample_project_matrix,
            env_matrix_df=sample_env_matrix,
        )
        payload = builder.build()

        # Roles should be templates (shared)
        assert len(payload.roles) > 0
        for role in payload.roles:
            assert "${roleAttribute/projects}" in str(role["policy"])

        # Teams should be prefixed
        expected_keys = ["voya-dev", "voya-qa", "voya-release"]
        actual_keys = [t["key"] for t in payload.teams]
        assert set(expected_keys) == set(actual_keys)

        # Each team should have single project
        for team in payload.teams:
            projects = next(
                a["values"] for a in team["roleAttributes"]
                if a["key"] == "projects"
            )
            assert projects == ["voya"]

    def test_multiple_projects_require_multiple_payloads(self):
        """Test that multiple projects need separate payload generations."""
        # Generate for project 1
        payload1 = RoleAttributePayloadBuilder(
            project_key="voya",
            prefix_team_keys=True,
            # ... params
        ).build()

        # Generate for project 2
        payload2 = RoleAttributePayloadBuilder(
            project_key="mobile",
            prefix_team_keys=True,
            # ... params
        ).build()

        # Team keys should be different
        keys1 = {t["key"] for t in payload1.teams}
        keys2 = {t["key"] for t in payload2.teams}
        assert keys1.isdisjoint(keys2)  # No overlap

        # Roles should be same (templates)
        role_keys1 = {r["key"] for r in payload1.roles}
        role_keys2 = {r["key"] for r in payload2.roles}
        assert role_keys1 == role_keys2  # Same template roles

    def test_json_output_valid(self):
        """Test that output is valid JSON for LaunchDarkly API."""
        builder = RoleAttributePayloadBuilder(
            project_key="voya",
            prefix_team_keys=True,
            # ... params
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
```

### 5. Edge Cases

```python
class TestProjectPrefixEdgeCases:
    """Edge case tests."""

    def test_empty_project_key(self):
        """Test handling of empty project key."""
        with pytest.raises(ValueError):
            RoleAttributePayloadBuilder(
                project_key="",
                prefix_team_keys=True,
                # ... params
            )

    def test_project_key_with_spaces(self):
        """Test project key with spaces is handled."""
        builder = RoleAttributePayloadBuilder(
            project_key="my project",  # Will be slugified
            prefix_team_keys=True,
            # ... params
        )
        payload = builder.build()

        # Keys should not have spaces
        for team in payload.teams:
            assert " " not in team["key"]

    def test_unicode_in_project_key(self):
        """Test unicode characters in project key."""
        builder = RoleAttributePayloadBuilder(
            project_key="проект",
            prefix_team_keys=True,
            # ... params
        )
        payload = builder.build()

        # Should handle gracefully
        assert len(payload.teams) > 0

    def test_very_long_project_key(self):
        """Test very long project key."""
        long_key = "a" * 100
        builder = RoleAttributePayloadBuilder(
            project_key=long_key,
            prefix_team_keys=True,
            # ... params
        )
        payload = builder.build()

        # Should work (LaunchDarkly has key length limits)
        assert len(payload.teams) > 0
```

---

# Implementation Plan

## Step 1: Update Payload Builder
1. Modify `RoleAttributePayloadBuilder.__init__()` to accept single `project_key`
2. Add `prefix_team_keys` and `team_name_format` parameters
3. Implement `_build_team_key()` and `_build_team_name()` methods
4. Update `_build_team_role_attributes()` to use single project

## Step 2: Update Setup Tab UI
1. Add checkbox for "Prefix team keys with project name"
2. Add radio for team name format
3. Only show when role_attributes mode is selected

## Step 3: Update Deploy Tab
1. Change `default_projects` list to single `project_key`
2. Pass new options to builder

## Step 4: Write Tests
1. Create `tests/test_project_prefixed_teams.py`
2. Implement all test cases above
3. Run and verify all pass

## Step 5: Update Documentation
1. Update Phase 11 README
2. Add examples to ROLE_ATTRIBUTES_EXPLAINED.md

---

# Summary

| Aspect | Current | After Implementation |
|--------|---------|---------------------|
| Team key | `dev` | `voya-dev` |
| Team name | `Developer` | `Voya: Developer` |
| Projects per team | Multiple possible | ONE (enforced) |
| Project isolation | Not guaranteed | Guaranteed |
| Pattern match | Partial | Matches ps-terraform-private |

This design ensures that teams are properly isolated to their respective projects, following the enterprise pattern from ps-terraform-private.
