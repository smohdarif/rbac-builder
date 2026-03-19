"""
Permission Models
=================

Defines permission structures for RBAC configuration.

Two types of permissions:
1. ProjectPermission: Applies to ALL environments in a project
2. EnvironmentPermission: Applies to a SPECIFIC environment group

These map directly to LaunchDarkly policy actions and resources.

Learn more:
    - docs/phases/phase1/PYTHON_CONCEPTS.md
    - docs/RBAC_CONCEPTS.md
"""

from dataclasses import dataclass, asdict, field
from typing import Optional


# =============================================================================
# LESSON 27: Multiple Dataclasses in One File
# =============================================================================
# It's common to group related dataclasses in one file.
# Here we have two permission types that are closely related.
#
# When to split into separate files?
# - When a class gets very large (200+ lines)
# - When classes have different dependencies
# - When you want clearer file organization


@dataclass
class ProjectPermission:
    """
    Project-level permissions for a team.

    These permissions apply to ALL environments in the project.
    For example, if a team can "create flags", the flags appear in all environments.

    Attributes:
        team_key: Reference to the Team this permission belongs to
        create_flags: Can create new feature flags
        update_flags: Can update flag metadata (name, description, tags)
        archive_flags: Can archive (retire) flags
        update_client_side_availability: Can toggle client-side SDK exposure
        manage_metrics: Can create/edit metrics for experiments
        manage_release_pipelines: Can manage release pipelines
        view_project: Can view the project (usually True for all)
        create_ai_configs: Can create AI Configs (LLM management)
        update_ai_configs: Can update AI Configs
        delete_ai_configs: Can delete AI Configs

    Example:
        >>> perm = ProjectPermission(
        ...     team_key="dev",
        ...     create_flags=True,
        ...     update_flags=True,
        ...     view_project=True
        ... )
    """

    # =========================================================================
    # LESSON 28: Many Boolean Fields Pattern
    # =========================================================================
    # When you have many boolean fields (like permissions), consider:
    # 1. Group them logically in the class definition
    # 2. Use consistent naming (verb_noun: create_flags, update_flags)
    # 3. Default to False (deny by default - safer!)
    # 4. Consider using a dict or set for very dynamic permissions

    # The team this permission applies to
    team_key: str

    # --- Flag permissions (project-wide) ---
    create_flags: bool = False
    update_flags: bool = False
    archive_flags: bool = False

    # --- SDK and client permissions ---
    update_client_side_availability: bool = False

    # --- Metrics and pipelines ---
    manage_metrics: bool = False
    manage_release_pipelines: bool = False

    # --- Project access ---
    view_project: bool = True  # Usually everyone can view

    # --- AI Configs (added Dec 2024) ---
    create_ai_configs: bool = False
    update_ai_configs: bool = False
    delete_ai_configs: bool = False

    def __post_init__(self) -> None:
        """Validate the permission."""
        if not self.team_key or not self.team_key.strip():
            raise ValueError("team_key cannot be empty")
        self.team_key = self.team_key.lower().strip()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectPermission":
        """Create from dictionary."""
        return cls(
            team_key=data.get("team_key", ""),
            create_flags=data.get("create_flags", False),
            update_flags=data.get("update_flags", False),
            archive_flags=data.get("archive_flags", False),
            update_client_side_availability=data.get("update_client_side_availability", False),
            manage_metrics=data.get("manage_metrics", False),
            manage_release_pipelines=data.get("manage_release_pipelines", False),
            view_project=data.get("view_project", True),
            create_ai_configs=data.get("create_ai_configs", False),
            update_ai_configs=data.get("update_ai_configs", False),
            delete_ai_configs=data.get("delete_ai_configs", False),
        )

    # =========================================================================
    # LESSON 29: Utility Methods for Permissions
    # =========================================================================
    # Add methods that help work with permissions in practical scenarios.

    def get_enabled_permissions(self) -> list[str]:
        """
        Get a list of all enabled (True) permissions.

        Useful for:
            - Debugging
            - Generating human-readable summaries
            - Building policy statements

        Returns:
            list[str]: Names of permissions that are True

        Example:
            >>> perm = ProjectPermission(team_key="dev", create_flags=True)
            >>> perm.get_enabled_permissions()
            ['create_flags', 'view_project']
        """
        enabled = []
        # Iterate over all fields except team_key
        for field_name in [
            "create_flags", "update_flags", "archive_flags",
            "update_client_side_availability", "manage_metrics",
            "manage_release_pipelines", "view_project",
            "create_ai_configs", "update_ai_configs", "delete_ai_configs"
        ]:
            if getattr(self, field_name):
                enabled.append(field_name)
        return enabled

    def has_any_flag_permission(self) -> bool:
        """Check if this permission grants any flag-related access."""
        return any([
            self.create_flags,
            self.update_flags,
            self.archive_flags
        ])

    def __str__(self) -> str:
        """Human-readable representation."""
        enabled = self.get_enabled_permissions()
        return f"ProjectPermission({self.team_key}: {len(enabled)} permissions)"


@dataclass
class EnvironmentPermission:
    """
    Environment-level permissions for a team in a specific environment group.

    These permissions are scoped to specific environments (e.g., only "production").
    This allows fine-grained control like:
    - Developers can update targeting in dev, but not production
    - QA can apply changes in staging, but only review in production

    Attributes:
        team_key: Reference to the Team
        environment_key: Reference to the EnvironmentGroup
        update_targeting: Can modify flag targeting rules
        review_changes: Can review pending changes (for approvals)
        apply_changes: Can apply/approve pending changes
        manage_segments: Can create and manage user segments
        manage_experiments: Can run experiments and A/B tests
        view_sdk_key: Can view the SDK key for this environment
        update_ai_config_targeting: Can update AI Config targeting rules

    Example:
        >>> perm = EnvironmentPermission(
        ...     team_key="dev",
        ...     environment_key="development",
        ...     update_targeting=True,
        ...     manage_segments=True
        ... )
    """

    # =========================================================================
    # LESSON 30: Composite Keys
    # =========================================================================
    # This model has a "composite key" - it's identified by TWO fields:
    #   (team_key, environment_key)
    #
    # This means: one EnvironmentPermission per team/environment combination.
    # - dev + development = one permission set
    # - dev + production = different permission set

    # Composite key: team + environment
    team_key: str
    environment_key: str

    # --- Targeting permissions ---
    update_targeting: bool = False

    # --- Approval workflow permissions ---
    review_changes: bool = False
    apply_changes: bool = False

    # --- Segment and experiment permissions ---
    manage_segments: bool = False
    manage_experiments: bool = False

    # --- SDK access ---
    view_sdk_key: bool = False

    # --- AI Config targeting (added Jun 2025) ---
    update_ai_config_targeting: bool = False

    def __post_init__(self) -> None:
        """Validate the permission."""
        if not self.team_key or not self.team_key.strip():
            raise ValueError("team_key cannot be empty")
        if not self.environment_key or not self.environment_key.strip():
            raise ValueError("environment_key cannot be empty")

        self.team_key = self.team_key.lower().strip()
        self.environment_key = self.environment_key.lower().strip()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "EnvironmentPermission":
        """Create from dictionary."""
        return cls(
            team_key=data.get("team_key", ""),
            environment_key=data.get("environment_key", ""),
            update_targeting=data.get("update_targeting", False),
            review_changes=data.get("review_changes", False),
            apply_changes=data.get("apply_changes", False),
            manage_segments=data.get("manage_segments", False),
            manage_experiments=data.get("manage_experiments", False),
            view_sdk_key=data.get("view_sdk_key", False),
            update_ai_config_targeting=data.get("update_ai_config_targeting", False),
        )

    def get_enabled_permissions(self) -> list[str]:
        """Get a list of all enabled permissions."""
        enabled = []
        for field_name in [
            "update_targeting", "review_changes", "apply_changes",
            "manage_segments", "manage_experiments", "view_sdk_key",
            "update_ai_config_targeting"
        ]:
            if getattr(self, field_name):
                enabled.append(field_name)
        return enabled

    def can_make_changes(self) -> bool:
        """Check if this permission allows making changes to the environment."""
        return any([
            self.update_targeting,
            self.apply_changes,
            self.manage_segments,
            self.manage_experiments,
            self.update_ai_config_targeting
        ])

    def __str__(self) -> str:
        """Human-readable representation."""
        enabled = self.get_enabled_permissions()
        return f"EnvironmentPermission({self.team_key}@{self.environment_key}: {len(enabled)} permissions)"


# =============================================================================
# Testing
# =============================================================================
if __name__ == "__main__":
    print("Testing Permission models...")
    print()

    # Test ProjectPermission
    print("=== ProjectPermission ===")
    proj_perm = ProjectPermission(
        team_key="dev",
        create_flags=True,
        update_flags=True,
        view_project=True
    )
    print(f"Created: {proj_perm}")
    print(f"Enabled: {proj_perm.get_enabled_permissions()}")
    print(f"Has flag permission: {proj_perm.has_any_flag_permission()}")
    print(f"Dict: {proj_perm.to_dict()}")
    print()

    # Test EnvironmentPermission
    print("=== EnvironmentPermission ===")
    env_perm = EnvironmentPermission(
        team_key="dev",
        environment_key="development",
        update_targeting=True,
        manage_segments=True,
        view_sdk_key=True
    )
    print(f"Created: {env_perm}")
    print(f"Enabled: {env_perm.get_enabled_permissions()}")
    print(f"Can make changes: {env_perm.can_make_changes()}")
    print()

    # Test production permissions (more restrictive)
    prod_perm = EnvironmentPermission(
        team_key="dev",
        environment_key="production",
        review_changes=True,  # Can review but not apply
        update_targeting=False,
        apply_changes=False
    )
    print(f"Production: {prod_perm}")
    print(f"Enabled: {prod_perm.get_enabled_permissions()}")
    print(f"Can make changes: {prod_perm.can_make_changes()}")  # Should be False

    print("\nAll tests passed!")
