"""
RBAC Config Model
=================

The top-level container that holds the complete RBAC configuration.

This is the "root" model that contains:
- Customer information
- All teams
- All environment groups
- All project permissions
- All environment permissions

When you save/load a configuration, you serialize/deserialize this model.

Learn more: docs/phases/phase1/PYTHON_CONCEPTS.md
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json

# =============================================================================
# LESSON 31: Importing from Sibling Modules
# =============================================================================
# These are "relative imports" - importing from files in the same package.
# The dot (.) means "current package" (models/)
#
# Alternative absolute imports would be:
#   from models.team import Team
#
# Relative imports are preferred inside a package because:
# - They make the package more portable
# - They clearly show the relationship between files

from .team import Team
from .environment import EnvironmentGroup
from .permissions import ProjectPermission, EnvironmentPermission


@dataclass
class RBACConfig:
    """
    Complete RBAC configuration for a customer.

    This is the main container that holds all configuration data.
    Think of it as the "document" that gets saved to a JSON file.

    Attributes:
        customer_name: Name of the customer/organization
        project_key: LaunchDarkly project key
        mode: "Manual" or "Connected" (API mode)
        created_at: When the config was first created
        updated_at: When the config was last modified
        teams: List of Team objects
        env_groups: List of EnvironmentGroup objects
        project_permissions: List of ProjectPermission objects
        env_permissions: List of EnvironmentPermission objects

    Example:
        >>> config = RBACConfig(
        ...     customer_name="Acme Inc",
        ...     project_key="mobile-app",
        ...     teams=[Team(key="dev", name="Developer")],
        ...     env_groups=[EnvironmentGroup(key="production", is_critical=True)]
        ... )
        >>> config.to_json()  # Save to JSON string
    """

    # =========================================================================
    # LESSON 32: Required vs Optional Fields
    # =========================================================================
    # Fields without defaults are REQUIRED (must be provided)
    # Fields with defaults are OPTIONAL (will use default if not provided)
    #
    # Python rule: Required fields must come BEFORE optional fields

    # --- Required fields ---
    customer_name: str
    project_key: str

    # --- Optional fields with simple defaults ---
    mode: str = "Manual"  # "Manual" or "Connected"

    # =========================================================================
    # LESSON 33: datetime Fields
    # =========================================================================
    # datetime objects are not directly JSON-serializable.
    # We'll need to convert them to strings (ISO format) when saving.
    #
    # Using default_factory=datetime.now means each new config gets
    # the current time as its creation time.

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # =========================================================================
    # LESSON 34: List Fields with default_factory
    # =========================================================================
    # IMPORTANT: Never use [] as a default for list fields!
    # Always use field(default_factory=list) instead.
    #
    # Why? Mutable default gotcha (see PYTHON_CONCEPTS.md Section 4)
    # - [] as default = ALL instances share the SAME list
    # - default_factory=list = each instance gets its OWN list

    teams: list[Team] = field(default_factory=list)
    env_groups: list[EnvironmentGroup] = field(default_factory=list)
    project_permissions: list[ProjectPermission] = field(default_factory=list)
    env_permissions: list[EnvironmentPermission] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the configuration."""
        if not self.customer_name or not self.customer_name.strip():
            raise ValueError("customer_name cannot be empty")

        if not self.project_key or not self.project_key.strip():
            raise ValueError("project_key cannot be empty")

        # Normalize
        self.customer_name = self.customer_name.strip()
        self.project_key = self.project_key.lower().strip()

        # Validate mode
        if self.mode not in ("Manual", "Connected"):
            raise ValueError(f"mode must be 'Manual' or 'Connected', got '{self.mode}'")

    # =========================================================================
    # LESSON 35: Complex Serialization (Nested Objects)
    # =========================================================================
    # When your dataclass contains other dataclasses, you need to handle
    # the serialization recursively.
    #
    # asdict() does this automatically, but datetime needs special handling.

    def to_dict(self) -> dict:
        """
        Convert the entire configuration to a dictionary.

        Handles:
            - Nested dataclasses (teams, env_groups, permissions)
            - datetime objects (converted to ISO format strings)

        Returns:
            dict: Complete configuration as a dictionary
        """
        return {
            "customer_name": self.customer_name,
            "project_key": self.project_key,
            "mode": self.mode,
            # datetime → ISO string for JSON compatibility
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            # Nested objects → list of dicts
            "teams": [t.to_dict() for t in self.teams],
            "env_groups": [e.to_dict() for e in self.env_groups],
            "project_permissions": [p.to_dict() for p in self.project_permissions],
            "env_permissions": [p.to_dict() for p in self.env_permissions],
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Convert to a JSON string.

        Args:
            indent: Number of spaces for indentation (default: 2)

        Returns:
            str: JSON-formatted string
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "RBACConfig":
        """
        Create an RBACConfig from a dictionary.

        Handles:
            - Nested objects (creates Team, EnvironmentGroup, etc. instances)
            - ISO datetime strings (converts back to datetime objects)

        Args:
            data: Dictionary with configuration data

        Returns:
            RBACConfig: A new configuration instance
        """
        # =====================================================================
        # LESSON 36: Parsing Nested Data
        # =====================================================================
        # When loading from JSON/dict, we need to:
        # 1. Parse datetime strings back to datetime objects
        # 2. Create instances of nested classes (Team, etc.)

        return cls(
            customer_name=data.get("customer_name", ""),
            project_key=data.get("project_key", ""),
            mode=data.get("mode", "Manual"),
            # Handle None/null timestamps (templates have null timestamps)
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            # Create instances from nested dicts
            teams=[Team.from_dict(t) for t in data.get("teams", [])],
            env_groups=[EnvironmentGroup.from_dict(e) for e in data.get("env_groups", [])],
            project_permissions=[ProjectPermission.from_dict(p) for p in data.get("project_permissions", [])],
            env_permissions=[EnvironmentPermission.from_dict(p) for p in data.get("env_permissions", [])],
        )

    @classmethod
    def from_json(cls, json_string: str) -> "RBACConfig":
        """
        Create an RBACConfig from a JSON string.

        Args:
            json_string: JSON-formatted string

        Returns:
            RBACConfig: A new configuration instance
        """
        data = json.loads(json_string)
        return cls.from_dict(data)

    # =========================================================================
    # LESSON 37: Convenience Methods
    # =========================================================================
    # Add methods that make the model easier to use in practice.
    # Think about common operations you'll need.

    def get_team_by_key(self, key: str) -> Optional[Team]:
        """
        Find a team by its key.

        Args:
            key: Team key to search for

        Returns:
            Team if found, None otherwise
        """
        key = key.lower().strip()
        for team in self.teams:
            if team.key == key:
                return team
        return None

    def get_env_group_by_key(self, key: str) -> Optional[EnvironmentGroup]:
        """
        Find an environment group by its key.

        Args:
            key: Environment group key to search for

        Returns:
            EnvironmentGroup if found, None otherwise
        """
        key = key.lower().strip()
        for env_group in self.env_groups:
            if env_group.key == key:
                return env_group
        return None

    def get_project_permission(self, team_key: str) -> Optional[ProjectPermission]:
        """
        Get project permissions for a team.

        Args:
            team_key: Team key to search for

        Returns:
            ProjectPermission if found, None otherwise
        """
        team_key = team_key.lower().strip()
        for perm in self.project_permissions:
            if perm.team_key == team_key:
                return perm
        return None

    def get_env_permission(self, team_key: str, env_key: str) -> Optional[EnvironmentPermission]:
        """
        Get environment permissions for a team in a specific environment.

        Args:
            team_key: Team key
            env_key: Environment group key

        Returns:
            EnvironmentPermission if found, None otherwise
        """
        team_key = team_key.lower().strip()
        env_key = env_key.lower().strip()
        for perm in self.env_permissions:
            if perm.team_key == team_key and perm.environment_key == env_key:
                return perm
        return None

    def mark_updated(self) -> None:
        """Update the updated_at timestamp to now."""
        self.updated_at = datetime.now()

    def summary(self) -> str:
        """
        Get a human-readable summary of the configuration.

        Returns:
            str: Summary text
        """
        return (
            f"RBAC Config: {self.customer_name}\n"
            f"  Project: {self.project_key}\n"
            f"  Mode: {self.mode}\n"
            f"  Teams: {len(self.teams)}\n"
            f"  Environment Groups: {len(self.env_groups)}\n"
            f"  Project Permissions: {len(self.project_permissions)}\n"
            f"  Environment Permissions: {len(self.env_permissions)}\n"
            f"  Created: {self.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"  Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')}"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"RBACConfig({self.customer_name}, {self.project_key})"


# =============================================================================
# Testing
# =============================================================================
if __name__ == "__main__":
    print("Testing RBACConfig model...")
    print()

    # Create teams
    dev_team = Team(key="dev", name="Developer", description="Development team")
    qa_team = Team(key="qa", name="QA Engineer", description="Quality assurance")
    admin_team = Team(key="admin", name="Administrator", description="Full access")

    # Create environment groups
    dev_env = EnvironmentGroup(key="development", is_critical=False, notes="Dev, test environments")
    prod_env = EnvironmentGroup(key="production", is_critical=True, requires_approval=True)

    # Create project permissions
    dev_proj_perm = ProjectPermission(
        team_key="dev",
        create_flags=True,
        update_flags=True,
        view_project=True
    )

    # Create environment permissions
    dev_env_perm = EnvironmentPermission(
        team_key="dev",
        environment_key="development",
        update_targeting=True,
        manage_segments=True
    )
    dev_prod_perm = EnvironmentPermission(
        team_key="dev",
        environment_key="production",
        review_changes=True,  # Can only review, not apply
        update_targeting=False
    )

    # Create the complete config
    config = RBACConfig(
        customer_name="Acme Corporation",
        project_key="mobile-app",
        mode="Manual",
        teams=[dev_team, qa_team, admin_team],
        env_groups=[dev_env, prod_env],
        project_permissions=[dev_proj_perm],
        env_permissions=[dev_env_perm, dev_prod_perm]
    )

    print("=== Config Summary ===")
    print(config.summary())
    print()

    # Test serialization
    print("=== JSON Serialization ===")
    json_str = config.to_json()
    print(json_str[:500] + "...")  # Print first 500 chars
    print()

    # Test deserialization
    print("=== JSON Deserialization ===")
    loaded_config = RBACConfig.from_json(json_str)
    print(f"Loaded: {loaded_config}")
    print(f"Teams: {[str(t) for t in loaded_config.teams]}")
    print()

    # Test lookup methods
    print("=== Lookup Methods ===")
    team = config.get_team_by_key("dev")
    print(f"get_team_by_key('dev'): {team}")

    env = config.get_env_group_by_key("production")
    print(f"get_env_group_by_key('production'): {env}")

    proj_perm = config.get_project_permission("dev")
    print(f"get_project_permission('dev'): {proj_perm}")

    env_perm = config.get_env_permission("dev", "production")
    print(f"get_env_permission('dev', 'production'): {env_perm}")

    print("\nAll tests passed!")
