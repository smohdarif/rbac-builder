"""
Payload Builder Service
=======================

Transforms RBAC configuration data into LaunchDarkly API-ready JSON payloads.

LESSON 25: The Builder Pattern
==============================
The PayloadBuilder uses the Builder pattern to construct complex objects step by step.
Instead of creating everything in one giant constructor, we build pieces incrementally:
    1. Extract permissions from the matrix
    2. Map to LaunchDarkly actions
    3. Build policy statements
    4. Generate role JSON
    5. Generate team JSON

This makes the code easier to understand, test, and maintain.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

# Import our action mappings
from core.ld_actions import (
    get_project_actions,
    get_env_actions,
    build_project_resource,
    build_flag_resource,
    build_segment_resource,
    build_env_resource,
    build_experiment_resource,
    PROJECT_PERMISSION_MAP,
    ENV_PERMISSION_MAP,
    # Phase 11: Role Attributes support
    build_role_attribute_resource,
    build_env_role_attribute_resource,
    build_project_only_role_attribute_resource,
    build_context_kind_role_attribute_resource,
    CONTEXT_KIND_ACTIONS_FOR_PERMISSION,
    PERMISSION_ATTRIBUTE_MAP,
    get_attribute_name,
    is_project_level_permission,
    is_env_level_permission,
    get_resource_type_for_permission,
    # Phase 12: Critical Environment support
    build_critical_env_role_attribute_resource,
    build_non_critical_env_role_attribute_resource,
    build_critical_env_only_resource,
    build_non_critical_env_only_resource,
)


# =============================================================================
# LESSON 26: DeployPayload - The Output Container
# =============================================================================
# This dataclass holds all the generated payloads ready for deployment

@dataclass
class DeployPayload:
    """
    Container for all deployment data.

    This is the output of PayloadBuilder - contains everything needed
    to deploy RBAC to LaunchDarkly.

    Attributes:
        customer_name: Customer identifier
        project_key: LaunchDarkly project key
        roles: List of custom role JSON payloads
        teams: List of team JSON payloads
        created_at: When the payload was generated

    Example:
        >>> payload = DeployPayload(
        ...     customer_name="Acme Corp",
        ...     project_key="mobile-app",
        ...     roles=[{"key": "dev-prod", ...}],
        ...     teams=[{"key": "developers", ...}]
        ... )
    """
    customer_name: str
    project_key: str
    roles: List[Dict[str, Any]] = field(default_factory=list)
    teams: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": {
                "customer_name": self.customer_name,
                "project_key": self.project_key,
                "created_at": self.created_at.isoformat(),
                "version": "1.0",
                "generated_by": "RBAC Builder"
            },
            "custom_roles": self.roles,
            "teams": self.teams,
            "deployment_order": [
                "1. Create custom roles first",
                "2. Create teams with role assignments",
                "3. Assign members to teams"
            ]
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def get_role_count(self) -> int:
        """Return number of custom roles."""
        return len(self.roles)

    def get_team_count(self) -> int:
        """Return number of teams."""
        return len(self.teams)


# =============================================================================
# LESSON 27: PayloadBuilder - The Main Transformer
# =============================================================================

class PayloadBuilder:
    """
    Transforms RBAC configuration into LaunchDarkly API payloads.

    This class takes the permission matrices from the UI and generates:
    1. Custom Role JSON payloads (one per team+environment combination)
    2. Team JSON payloads (with role assignments)

    Usage:
        >>> builder = PayloadBuilder(
        ...     customer_name="Acme",
        ...     project_key="mobile-app",
        ...     teams_df=teams_dataframe,
        ...     env_groups_df=env_groups_dataframe,
        ...     project_matrix_df=project_matrix_dataframe,
        ...     env_matrix_df=env_matrix_dataframe
        ... )
        >>> payload = builder.build()
        >>> print(payload.to_json())
    """

    def __init__(
        self,
        customer_name: str,
        project_key: str,
        teams_df,           # pandas DataFrame
        env_groups_df,      # pandas DataFrame
        project_matrix_df,  # pandas DataFrame
        env_matrix_df,      # pandas DataFrame
    ):
        """
        Initialize the PayloadBuilder.

        Args:
            customer_name: Customer identifier
            project_key: LaunchDarkly project key
            teams_df: DataFrame with team definitions (Key, Name, Description)
            env_groups_df: DataFrame with environment groups (Key, Critical, etc.)
            project_matrix_df: DataFrame with project-level permissions
            env_matrix_df: DataFrame with environment-level permissions
        """
        self.customer_name = customer_name
        self.project_key = project_key
        self.teams_df = teams_df
        self.env_groups_df = env_groups_df
        self.project_matrix_df = project_matrix_df
        self.env_matrix_df = env_matrix_df

    # =========================================================================
    # MAIN BUILD METHOD
    # =========================================================================

    def build(self) -> DeployPayload:
        """
        Build the complete deployment payload.

        This is the main entry point - call this to generate all payloads.

        Returns:
            DeployPayload containing all roles and teams
        """
        roles = self.build_custom_roles()
        teams = self.build_teams(roles)

        return DeployPayload(
            customer_name=self.customer_name,
            project_key=self.project_key,
            roles=roles,
            teams=teams
        )

    # =========================================================================
    # ROLE BUILDING
    # =========================================================================

    def build_custom_roles(self) -> List[Dict[str, Any]]:
        """
        Generate all custom role JSON payloads.

        Creates SEPARATE roles for project-level and environment-level permissions:
        1. ONE project role per team (with create/archive flags, etc.)
        2. Environment-specific roles per team+env (with targeting/review, etc.)

        For example, if you have 2 teams and 2 environments, you get:
            - dev-project (project-level permissions)
            - dev-test (Test env permissions only)
            - dev-production (Production env permissions only)
            - qa-project (project-level permissions)
            - qa-test (Test env permissions only)
            - qa-production (Production env permissions only)

        Returns:
            List of custom role JSON dictionaries
        """
        roles = []

        # Get unique teams from the project matrix
        # We use the "Team" column which has the team NAME (display name)
        team_names = self.project_matrix_df["Team"].unique().tolist()

        # Get environment keys
        env_keys = self._get_env_keys()

        # =================================================================
        # LESSON 28: Separate Project vs Environment Roles
        # =================================================================
        # This matches the Terraform pattern where project-level permissions
        # are in ONE role, and environment permissions are in separate roles.

        for team_name in team_names:
            # Get team key from team name
            team_key = self._get_team_key(team_name)
            if not team_key:
                continue  # Skip if team not found

            # 1. Create ONE project-level role for this team
            project_role = self._build_project_role_for_team(team_name, team_key)
            if project_role:
                roles.append(project_role)

            # 2. Create environment-specific roles (env permissions ONLY)
            for env_key in env_keys:
                env_role = self._build_env_role_for_team(team_name, team_key, env_key)
                if env_role:  # Only add if role has permissions
                    roles.append(env_role)

        return roles

    def _build_project_role_for_team(
        self,
        team_name: str,
        team_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Build a single project-level role for a team.

        This role contains ONLY project-level permissions (create flags, archive, etc.)
        NOT environment-specific permissions.

        Args:
            team_name: Display name of the team (e.g., "Developer")
            team_key: Key of the team (e.g., "dev")

        Returns:
            Custom role JSON dictionary, or None if no permissions
        """
        # Generate role key and name
        role_key = f"{team_key.lower().replace(' ', '-')}-project"
        role_name = f"{team_name} - Project"

        # Build project-level policies only
        policy = self._build_project_policies(team_name)

        # Skip if no permissions granted
        if not policy:
            return None

        return {
            "key": role_key,
            "name": role_name,
            "description": f"Project-level permissions for {team_name}",
            "policy": policy
        }

    def _build_env_role_for_team(
        self,
        team_name: str,
        team_key: str,
        env_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Build a single environment-level role for a team+environment.

        This role contains ONLY environment-specific permissions (targeting, review, etc.)
        NOT project-level permissions.

        Args:
            team_name: Display name of the team (e.g., "Developer")
            team_key: Key of the team (e.g., "dev")
            env_key: Environment key (e.g., "production")

        Returns:
            Custom role JSON dictionary, or None if no permissions
        """
        # Generate role key and name
        role_key = self._generate_role_key(team_key, env_key)
        role_name = f"{team_name} - {env_key.title()}"

        # Build environment-level policies ONLY (no project policies!)
        policy = self._build_env_policies(team_name, env_key)

        # Skip if no permissions granted
        if not policy:
            return None

        return {
            "key": role_key,
            "name": role_name,
            "description": f"Environment permissions for {team_name} in {env_key}",
            "policy": policy
        }

    def _build_project_policies(self, team_name: str) -> List[Dict[str, Any]]:
        """
        Build project-level policy statements for a team.

        Args:
            team_name: Display name of the team

        Returns:
            List of policy statement dictionaries
        """
        policies = []

        # Find the row for this team in project_matrix
        team_row = self.project_matrix_df[
            self.project_matrix_df["Team"] == team_name
        ]

        if team_row.empty:
            return policies

        # Get the first (and should be only) row as a dict
        row = team_row.iloc[0].to_dict()

        # =================================================================
        # LESSON 30: Iterating Over Permission Columns
        # =================================================================
        # We check each permission column and add policies for enabled ones

        # Collect all actions that are enabled
        all_actions = []

        for column, action_enum in PROJECT_PERMISSION_MAP.items():
            if column in row and row[column] is True:
                all_actions.extend(action_enum.value)

        # If we have actions, create a single policy statement
        if all_actions:
            policies.append({
                "effect": "allow",
                "actions": all_actions,
                "resources": [build_flag_resource(self.project_key)]
            })

        return policies

    def _build_env_policies(self, team_name: str, env_key: str) -> List[Dict[str, Any]]:
        """
        Build environment-level policy statements for a team+environment.

        Args:
            team_name: Display name of the team
            env_key: Environment key

        Returns:
            List of policy statement dictionaries
        """
        policies = []

        # Find rows for this team+environment in env_matrix
        team_env_rows = self.env_matrix_df[
            (self.env_matrix_df["Team"] == team_name) &
            (self.env_matrix_df["Environment"] == env_key)
        ]

        if team_env_rows.empty:
            return policies

        row = team_env_rows.iloc[0].to_dict()

        # Collect flag-related actions
        flag_actions = []
        segment_actions = []
        experiment_actions = []

        for column, action_enum in ENV_PERMISSION_MAP.items():
            if column in row and row[column] is True:
                actions = action_enum.value

                # =============================================================
                # LESSON: Route actions to correct resource types
                # =============================================================
                # Different permission types target different LD resources:
                # - Segments use segment/* resource
                # - Experiments use experiment/* resource
                # - Everything else (targeting, approvals, etc.) uses flag/*
                if column == "Manage Segments":
                    segment_actions.extend(actions)
                elif column == "Manage Experiments":
                    experiment_actions.extend(actions)
                else:
                    flag_actions.extend(actions)

        # Add flag policy if we have flag actions
        if flag_actions:
            policies.append({
                "effect": "allow",
                "actions": flag_actions,
                "resources": [build_flag_resource(self.project_key, env_key)]
            })

        # Add segment policy if we have segment actions
        if segment_actions:
            policies.append({
                "effect": "allow",
                "actions": segment_actions,
                "resources": [build_segment_resource(self.project_key, env_key)]
            })

        # Add experiment policy if we have experiment actions
        if experiment_actions:
            policies.append({
                "effect": "allow",
                "actions": experiment_actions,
                "resources": [build_experiment_resource(self.project_key, env_key)]
            })

        return policies

    # =========================================================================
    # TEAM BUILDING
    # =========================================================================

    def build_teams(self, roles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate team JSON payloads with role assignments.

        Args:
            roles: List of custom roles (to extract role keys)

        Returns:
            List of team JSON dictionaries
        """
        teams = []

        # Iterate over unique teams
        for _, team_row in self.teams_df.iterrows():
            team_key = team_row.get("Key") or team_row.get("key")
            team_name = team_row.get("Name") or team_row.get("name")
            team_desc = team_row.get("Description") or team_row.get("description", "")

            if not team_key:
                continue

            # Find all roles that belong to this team
            team_role_keys = [
                role["key"]
                for role in roles
                if role["key"].startswith(f"{team_key}-")
            ]

            # =================================================================
            # LESSON 31: LaunchDarkly Team JSON Format
            # =================================================================
            teams.append({
                "key": team_key,
                "name": team_name,
                "description": team_desc,
                "customRoleKeys": team_role_keys
            })

        return teams

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _generate_role_key(self, team_key: str, env_key: str) -> str:
        """
        Generate a unique role key from team and environment.

        Format: {team_key}-{env_key}
        Example: "dev-production"
        """
        # Normalize to lowercase and replace spaces with dashes
        team_part = team_key.lower().replace(" ", "-")
        env_part = env_key.lower().replace(" ", "-")
        return f"{team_part}-{env_part}"

    def _get_team_key(self, team_name: str) -> Optional[str]:
        """
        Get team key from team name.

        Args:
            team_name: Display name (e.g., "Developer")

        Returns:
            Team key (e.g., "dev") or None if not found
        """
        # Check both column name formats
        name_col = "Name" if "Name" in self.teams_df.columns else "name"
        key_col = "Key" if "Key" in self.teams_df.columns else "key"

        team_row = self.teams_df[self.teams_df[name_col] == team_name]
        if not team_row.empty:
            return team_row.iloc[0][key_col]
        return None

    def _get_env_keys(self) -> List[str]:
        """Get list of environment keys from env_groups DataFrame."""
        key_col = "Key" if "Key" in self.env_groups_df.columns else "key"
        return [k for k in self.env_groups_df[key_col].tolist() if k]


# =============================================================================
# LESSON 32: Convenience Function
# =============================================================================

def build_payload_from_session(
    customer_name: str,
    project_key: str,
    session_state
) -> DeployPayload:
    """
    Build payload directly from Streamlit session state.

    This is a convenience function for use in the Streamlit app.

    Args:
        customer_name: Customer identifier
        project_key: Project key
        session_state: Streamlit session state object

    Returns:
        DeployPayload ready for export or deployment
    """
    builder = PayloadBuilder(
        customer_name=customer_name,
        project_key=project_key,
        teams_df=session_state.teams,
        env_groups_df=session_state.env_groups,
        project_matrix_df=session_state.project_matrix,
        env_matrix_df=session_state.env_matrix
    )
    return builder.build()


# =============================================================================
# LESSON 35: RoleAttributePayloadBuilder (Phase 11)
# =============================================================================
# This builder creates TEMPLATE roles with ${roleAttribute/...} placeholders
# instead of hardcoded project/environment values.
#
# Benefits:
# - ONE role definition serves ALL teams/projects
# - Teams specify their access via roleAttributes
# - Scales to enterprise without role explosion
#
# Example output:
#   Role: "update-targeting" with resource "proj/${roleAttribute/projects}:env/*:flag/*"
#   Team: { customRoleKeys: ["update-targeting"], roleAttributes: [{key: "projects", values: ["voya"]}] }

def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug format.

    Example:
        >>> slugify("Update Targeting")
        'update-targeting'
        >>> slugify("Manage AI Variations")
        'manage-ai-variations'
    """
    return text.lower().replace(" ", "-")


class RoleAttributePayloadBuilder:
    """
    Builds template roles with role attribute placeholders and teams with roleAttributes.

    This is the enterprise-scale alternative to PayloadBuilder. Instead of creating
    separate roles for each team×environment combination, it creates:
    1. ONE template role per permission type (with placeholders)
    2. Teams that fill in the placeholders via roleAttributes

    Following the ps-terraform-private pattern:
    - Each team has ONE project in roleAttributes (for project isolation)
    - Team keys are prefixed with project name (e.g., "voya-dev")
    - Team names include project prefix (e.g., "Voya: Developer")

    Usage:
        >>> builder = RoleAttributePayloadBuilder(
        ...     customer_name="Acme",
        ...     project_key="mobile-app",
        ...     teams_df=teams_dataframe,
        ...     env_groups_df=env_groups_dataframe,
        ...     project_matrix_df=project_matrix_dataframe,
        ...     env_matrix_df=env_matrix_dataframe,
        ...     prefix_team_keys=True,
        ...     team_name_format="{project}: {team}"
        ... )
        >>> payload = builder.build()
        >>> print(payload.to_json())
    """

    def __init__(
        self,
        customer_name: str,
        project_key: str,               # Single project (not list!)
        teams_df,                       # pandas DataFrame
        env_groups_df,                  # pandas DataFrame
        project_matrix_df,              # pandas DataFrame
        env_matrix_df,                  # pandas DataFrame
        prefix_team_keys: bool = True,  # Prefix team keys with project
        team_name_format: str = "{project}: {team}",  # Format for team names
    ):
        """
        Initialize the RoleAttributePayloadBuilder.

        Args:
            customer_name: Customer identifier
            project_key: Single project key teams will have access to (ONE per team)
            teams_df: DataFrame with team definitions (Key, Name, Description)
            env_groups_df: DataFrame with environment groups (Key, Critical, etc.)
            project_matrix_df: DataFrame with project-level permissions
            env_matrix_df: DataFrame with environment-level permissions
            prefix_team_keys: If True, prefix team keys with project name (e.g., "voya-dev")
            team_name_format: Format string for team names ("{project}: {team}")
        """
        self.customer_name = customer_name
        self.project_key = project_key  # Single project for isolation
        self.teams_df = teams_df
        self.env_groups_df = env_groups_df
        self.project_matrix_df = project_matrix_df
        self.env_matrix_df = env_matrix_df
        self.prefix_team_keys = prefix_team_keys
        self.team_name_format = team_name_format

    # =========================================================================
    # LESSON 43: Critical Environment Detection (Phase 12)
    # =========================================================================
    # These methods detect whether the configuration uses the criticality
    # pattern (both critical and non-critical environments defined).
    #
    # When the pattern is detected, we generate TWO sets of roles:
    # - non-critical-* roles with *;{critical:false} resource specifier
    # - critical-* roles with *;{critical:true} resource specifier

    def _is_env_critical(self, env_key: str) -> bool:
        """
        Check if a specific environment is marked as Critical.

        Looks up the Critical column in env_groups_df for the given env key.

        Args:
            env_key: The environment key to check

        Returns:
            True if environment is marked Critical, False otherwise
        """
        # Handle both column name formats
        key_col = "Key" if "Key" in self.env_groups_df.columns else "key"
        critical_col = "Critical" if "Critical" in self.env_groups_df.columns else "critical"

        if critical_col not in self.env_groups_df.columns:
            return False  # No Critical column, default to non-critical

        row = self.env_groups_df[self.env_groups_df[key_col] == env_key]
        if row.empty:
            return False
        return row.iloc[0].get(critical_col, False) == True

    def _get_critical_envs(self) -> list:
        """
        Get list of environment keys where Critical=True.

        Returns:
            List of environment keys marked as critical
        """
        key_col = "Key" if "Key" in self.env_groups_df.columns else "key"
        critical_col = "Critical" if "Critical" in self.env_groups_df.columns else "critical"

        if critical_col not in self.env_groups_df.columns:
            return []

        return self.env_groups_df[
            self.env_groups_df[critical_col] == True
        ][key_col].tolist()

    def _get_non_critical_envs(self) -> list:
        """
        Get list of environment keys where Critical=False.

        Returns:
            List of environment keys marked as non-critical
        """
        key_col = "Key" if "Key" in self.env_groups_df.columns else "key"
        critical_col = "Critical" if "Critical" in self.env_groups_df.columns else "critical"

        if critical_col not in self.env_groups_df.columns:
            # If no Critical column, all envs are non-critical
            return self.env_groups_df[key_col].tolist()

        return self.env_groups_df[
            self.env_groups_df[critical_col] == False
        ][key_col].tolist()

    def _uses_criticality_pattern(self) -> bool:
        """
        Check if env_groups has BOTH critical and non-critical environments.

        The criticality pattern is only used when there are environments
        of both types. If all environments are the same criticality,
        we use the standard per-permission role pattern instead.

        Returns:
            True if both critical and non-critical environments exist
        """
        critical_envs = self._get_critical_envs()
        non_critical_envs = self._get_non_critical_envs()
        return len(critical_envs) > 0 and len(non_critical_envs) > 0

    # =========================================================================
    # MAIN BUILD METHOD
    # =========================================================================

    def build(self) -> DeployPayload:
        """
        Build the complete deployment payload with template roles and teams.

        Returns:
            DeployPayload with template roles and teams with roleAttributes
        """
        # Step 1: Build template roles (one per permission type)
        roles = self._build_template_roles()

        # Step 2: Build teams with role attributes
        teams = self._build_teams_with_attributes(roles)

        return DeployPayload(
            customer_name=self.customer_name,
            project_key=self.project_key,  # Single project
            roles=roles,
            teams=teams
        )

    # =========================================================================
    # TEMPLATE ROLE BUILDING
    # =========================================================================

    def _build_template_roles(self) -> List[Dict[str, Any]]:
        """
        Build template roles with ${roleAttribute/...} placeholders.

        Creates ONE role per permission type that any team has enabled.
        The roles use placeholders instead of hardcoded values.

        When criticality pattern is detected (both critical and non-critical
        environments exist), generates TWO roles per environment permission:
        - non-critical-{permission} with *;{critical:false} resource
        - critical-{permission} with *;{critical:true} resource

        Returns:
            List of template role JSON dictionaries
        """
        roles = []

        # =================================================================
        # LESSON 36: Determine which permissions are actually used
        # =================================================================
        # Only create roles for permissions that at least one team has enabled.
        # This avoids creating unused roles.

        # Build project-level template roles (unchanged - not affected by criticality)
        used_project_perms = self._get_used_project_permissions()
        for permission in used_project_perms:
            role = self._build_project_template_role(permission)
            if role:
                roles.append(role)

        # =================================================================
        # LESSON 44: Role Attribute Pattern — one role per permission
        # =================================================================
        # Each env permission gets ONE shared role template.
        # The role uses ${roleAttribute/<perm>-environments} as a placeholder.
        # Teams fill in this placeholder with exact environment keys via
        # their roleAttributes block — e.g., update-targeting-environments = ["production"].
        #
        # This replaces the old Phase 12 {critical:true} wildcard pattern.
        # The role attribute pattern is more explicit and testable: you can
        # read exactly which environments each team has access to.
        used_env_perms = self._get_used_env_permissions()

        for permission in used_env_perms:
            role = self._build_env_template_role(permission)
            if role:
                roles.append(role)

        return roles

    def _get_used_project_permissions(self) -> List[str]:
        """
        Get list of project permissions that at least one team has enabled.

        Returns:
            List of permission names (UI column names)
        """
        used = []
        for column in PROJECT_PERMISSION_MAP.keys():
            if column in self.project_matrix_df.columns:
                # Check if any team has this permission enabled
                if self.project_matrix_df[column].any():
                    used.append(column)
        return used

    def _get_used_env_permissions(self) -> List[str]:
        """
        Get list of environment permissions that at least one team has enabled.

        Returns:
            List of permission names (UI column names)
        """
        used = []
        for column in ENV_PERMISSION_MAP.keys():
            if column in self.env_matrix_df.columns:
                # Check if any team has this permission enabled
                if self.env_matrix_df[column].any():
                    used.append(column)
        return used

    def _build_project_template_role(
        self,
        permission_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Build a project-level template role with role attribute placeholder.

        Args:
            permission_name: UI permission name (e.g., "Create Flags")

        Returns:
            Template role JSON dictionary
        """
        actions = get_project_actions(permission_name)
        if not actions:
            return None

        role_key = slugify(permission_name)
        resource_type = get_resource_type_for_permission(permission_name)

        # =================================================================
        # LESSON: View Project uses project-only resource
        # =================================================================
        # viewProject action targets the project itself, not flags
        if permission_name == "View Project":
            policy = [{
                "effect": "allow",
                "actions": actions,
                "resources": [build_project_only_role_attribute_resource("projects")]
            }]
        else:
            # Build policy with role attribute placeholder
            policy = [{
                "effect": "allow",
                "actions": actions,
                "resources": [build_role_attribute_resource("projects", resource_type)]
            }]

            # =================================================================
            # LESSON: Context Kind statement (matches ps-terraform default)
            # =================================================================
            # By default, flag creation/update roles include context kind
            # permissions. This matches manage-flags/main.tf where:
            #   create_context_kind = coalesce(null, !false) = true
            # create-flags gets: createContextKind
            # update-flags gets: updateContextKind, updateAvailabilityForExperiments
            context_kind_actions = CONTEXT_KIND_ACTIONS_FOR_PERMISSION.get(permission_name)
            if context_kind_actions:
                policy.append({
                    "effect": "allow",
                    "actions": context_kind_actions,
                    "resources": [build_context_kind_role_attribute_resource("projects")]
                })

            # Add viewProject for non-view roles
            policy.append({
                "effect": "allow",
                "actions": ["viewProject"],
                "resources": [build_project_only_role_attribute_resource("projects")]
            })

        return {
            "key": role_key,
            "name": permission_name,
            "description": f"Template role for {permission_name}",
            "base_permissions": "no_access",
            "policy": policy
        }

    def _build_env_template_role(
        self,
        permission_name: str,
        critical: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Build an environment-level template role with role attribute placeholders.

        When critical is None (default):
            - Uses ${roleAttribute/<permission>Environments} placeholder
            - Role key: slugify(permission_name)

        When critical is True:
            - Uses *;{critical:true} wildcard specifier
            - Role key: critical-{slugify(permission_name)}

        When critical is False:
            - Uses *;{critical:false} wildcard specifier
            - Role key: non-critical-{slugify(permission_name)}

        Args:
            permission_name: UI permission name (e.g., "Update Targeting")
            critical: None for standard mode, True/False for criticality mode

        Returns:
            Template role JSON dictionary
        """
        actions = get_env_actions(permission_name)
        if not actions:
            return None

        base_key = slugify(permission_name)
        resource_type = get_resource_type_for_permission(permission_name)

        # =================================================================
        # LESSON 45: Critical Environment Role Building (Phase 12)
        # =================================================================
        # When using criticality pattern, generate wildcard-based resources
        # instead of per-permission environment attribute placeholders.

        if critical is True:
            # Critical environment role
            role_key = f"critical-{base_key}"
            role_name = f"Critical: {permission_name}"
            description = f"Template role for {permission_name} in critical environments"

            if permission_name == "View SDK Key":
                resource = build_critical_env_only_resource("projects")
            else:
                resource = build_critical_env_role_attribute_resource("projects", resource_type)

        elif critical is False:
            # Non-critical environment role
            role_key = f"non-critical-{base_key}"
            role_name = f"Non-Critical: {permission_name}"
            description = f"Template role for {permission_name} in non-critical environments"

            if permission_name == "View SDK Key":
                resource = build_non_critical_env_only_resource("projects")
            else:
                resource = build_non_critical_env_role_attribute_resource("projects", resource_type)

        else:
            # Standard mode - use environment attribute placeholder
            role_key = base_key
            role_name = permission_name
            description = f"Template role for {permission_name}"
            env_attr = get_attribute_name(permission_name)

            if permission_name == "View SDK Key":
                resource = f"proj/${{roleAttribute/projects}}:env/${{roleAttribute/{env_attr}}}"
            else:
                resource = build_env_role_attribute_resource("projects", env_attr, resource_type)

        # Build policy
        policy = [{
            "effect": "allow",
            "actions": actions,
            "resources": [resource]
        }]

        # Add viewProject for all env roles
        policy.append({
            "effect": "allow",
            "actions": ["viewProject"],
            "resources": [build_project_only_role_attribute_resource("projects")]
        })

        return {
            "key": role_key,
            "name": role_name,
            "description": description,
            "base_permissions": "no_access",
            "policy": policy
        }

    # =========================================================================
    # TEAM BUILDING WITH ROLE ATTRIBUTES
    # =========================================================================

    def _build_teams_with_attributes(
        self,
        roles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Build teams with roleAttributes that fill in the template placeholders.

        Each team gets:
        1. List of customRoleKeys (which template roles they use)
        2. roleAttributes (values to fill in the placeholders)
        3. Project-prefixed key (if prefix_team_keys is True)
        4. Formatted name (based on team_name_format)

        Args:
            roles: List of template roles (to validate role keys)

        Returns:
            List of team JSON dictionaries with roleAttributes
        """
        teams = []
        role_keys = {role["key"] for role in roles}

        for _, team_row in self.teams_df.iterrows():
            base_key = team_row.get("Key") or team_row.get("key")
            base_name = team_row.get("Name") or team_row.get("name")
            team_desc = team_row.get("Description") or team_row.get("description", "")

            if not base_key:
                continue

            # Apply project prefix to team key if enabled
            team_key = self._build_team_key(base_key)

            # Apply name format
            team_name = self._build_team_name(base_name)

            # Get roles this team should have
            team_roles = self._get_team_role_keys(base_name, role_keys)

            # Get role attributes for this team (single project!)
            role_attributes = self._build_team_role_attributes(base_name)

            teams.append({
                "key": team_key,
                "name": team_name,
                "description": team_desc,
                "customRoleKeys": team_roles,
                "roleAttributes": role_attributes
            })

        return teams

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

    def _get_team_role_keys(
        self,
        team_name: str,
        available_role_keys: set
    ) -> List[str]:
        """
        Get the template role keys a team should be assigned.

        A team gets a role if they have that permission enabled anywhere
        (for project perms) or in any environment (for env perms).

        When criticality pattern is used, maps environment permissions to
        the correct critical or non-critical role based on the environment's
        Critical column value.

        Args:
            team_name: Display name of the team
            available_role_keys: Set of role keys that exist

        Returns:
            List of role keys to assign to this team
        """
        roles = []

        # Check project permissions
        team_project_row = self.project_matrix_df[
            self.project_matrix_df["Team"] == team_name
        ]
        if not team_project_row.empty:
            row = team_project_row.iloc[0].to_dict()
            for column in PROJECT_PERMISSION_MAP.keys():
                if column in row and row[column] is True:
                    role_key = slugify(column)
                    if role_key in available_role_keys:
                        roles.append(role_key)

        # =================================================================
        # LESSON 46: Role Assignment — one role per permission
        # =================================================================
        # A team gets a role if it has that permission enabled in ANY environment.
        # Which specific environments are allowed is handled separately by the
        # team's roleAttributes (e.g., update-targeting-environments = ["prod"]).
        # This keeps role assignment simple: just check if the permission is used at all.

        team_env_rows = self.env_matrix_df[
            self.env_matrix_df["Team"] == team_name
        ]

        if not team_env_rows.empty:
            for column in ENV_PERMISSION_MAP.keys():
                if column in team_env_rows.columns:
                    if team_env_rows[column].any():
                        role_key = slugify(column)
                        if role_key in available_role_keys:
                            roles.append(role_key)

        return list(set(roles))  # Remove duplicates

    def _build_team_role_attributes(self, team_name: str) -> List[Dict[str, Any]]:
        """
        Build the roleAttributes list for a team.

        This determines what values fill in the ${roleAttribute/...} placeholders.

        IMPORTANT: Following ps-terraform-private pattern, each team has ONE project
        in roleAttributes to ensure project isolation.

        When criticality pattern is used:
        - Only "projects" attribute is needed
        - Environment attributes are NOT needed (wildcard *;{critical:true/false} matches all)

        When standard mode is used:
        - "projects" attribute for project scoping
        - Per-permission environment attributes (e.g., updateTargetingEnvironments)

        Args:
            team_name: Display name of the team

        Returns:
            List of roleAttribute dictionaries
        """
        attributes = []

        # =================================================================
        # LESSON 37: Single project in "projects" attribute
        # =================================================================
        # This fills in ${roleAttribute/projects} in all roles.
        # CRITICAL: Only ONE project per team for isolation!
        attributes.append({
            "key": "projects",
            "values": [self.project_key]  # Single project, not list!
        })

        # =================================================================
        # LESSON 38: Add environment attributes for each env permission
        # =================================================================
        # For each environment-level permission, add a roleAttribute listing
        # the exact environment keys the team can perform that action in.
        # e.g., update-targeting-environments = ["production", "staging"]
        #
        # This fills the ${roleAttribute/update-targeting-environments} placeholder
        # in the role's resource string. The team controls which envs it can access
        # by setting these values — no LD-side environment property setup required.

        team_env_rows = self.env_matrix_df[
            self.env_matrix_df["Team"] == team_name
        ]

        if team_env_rows.empty:
            return attributes

        # Get environment column name
        env_col = "Environment" if "Environment" in team_env_rows.columns else "environment"

        for column in ENV_PERMISSION_MAP.keys():
            if column not in team_env_rows.columns:
                continue

            # Find environments where this team has this permission
            allowed_envs = team_env_rows[
                team_env_rows[column] == True
            ][env_col].tolist()

            if allowed_envs:
                attr_name = get_attribute_name(column)
                attributes.append({
                    "key": attr_name,
                    "values": allowed_envs
                })

        return attributes


def build_role_attribute_payload_from_session(
    customer_name: str,
    project_key: str,
    session_state,
    prefix_team_keys: bool = True,
    team_name_format: str = "{project}: {team}"
) -> DeployPayload:
    """
    Build role attribute payload directly from Streamlit session state.

    This is the convenience function for role attributes mode.

    Args:
        customer_name: Customer identifier
        project_key: Single project key (not list!)
        session_state: Streamlit session state object
        prefix_team_keys: If True, prefix team keys with project name
        team_name_format: Format string for team names

    Returns:
        DeployPayload with template roles and teams with roleAttributes
    """
    builder = RoleAttributePayloadBuilder(
        customer_name=customer_name,
        project_key=project_key,
        teams_df=session_state.teams,
        env_groups_df=session_state.env_groups,
        project_matrix_df=session_state.project_matrix,
        env_matrix_df=session_state.env_matrix,
        prefix_team_keys=prefix_team_keys,
        team_name_format=team_name_format
    )
    return builder.build()


# =============================================================================
# Module test
# =============================================================================
if __name__ == "__main__":
    import pandas as pd

    print("=== PayloadBuilder Test ===\n")

    # Create test data
    teams_df = pd.DataFrame({
        "Key": ["dev", "qa"],
        "Name": ["Developer", "QA Engineer"],
        "Description": ["Dev team", "QA team"]
    })

    env_groups_df = pd.DataFrame({
        "Key": ["Test", "Production"],
        "Critical": [False, True]
    })

    project_matrix_df = pd.DataFrame({
        "Team": ["Developer", "QA Engineer"],
        "Create Flags": [True, False],
        "Update Flags": [True, True],
        "View Project": [True, True]
    })

    env_matrix_df = pd.DataFrame({
        "Team": ["Developer", "Developer", "QA Engineer", "QA Engineer"],
        "Environment": ["Test", "Production", "Test", "Production"],
        "Update Targeting": [True, False, True, False],
        "Review Changes": [False, False, True, True],
        "Apply Changes": [True, False, True, False]
    })

    # Build payload
    builder = PayloadBuilder(
        customer_name="Test Corp",
        project_key="test-project",
        teams_df=teams_df,
        env_groups_df=env_groups_df,
        project_matrix_df=project_matrix_df,
        env_matrix_df=env_matrix_df
    )

    payload = builder.build()

    print(f"Generated {payload.get_role_count()} roles and {payload.get_team_count()} teams\n")
    print("=== JSON Output ===")
    print(payload.to_json())
