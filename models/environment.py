"""
Environment Group Model
=======================

Represents a category of environments for permission scoping.

Instead of defining permissions for each individual environment (dev, staging, prod),
we group them into categories like "critical" and "non-critical".

Examples:
    - "critical" group: production (requires approvals)
    - "non-critical" group: development, test, staging (more permissive)

This maps to LaunchDarkly's environment tags for resource specifiers:
    proj/*:env/*;critical:flag/*  (all flags in critical environments)

Learn more: docs/phases/phase1/PYTHON_CONCEPTS.md
"""

from dataclasses import dataclass, asdict
import re


@dataclass
class EnvironmentGroup:
    """
    Represents a category of environments.

    Environment groups allow you to apply permissions to multiple environments
    at once using LaunchDarkly's tag-based resource specifiers.

    Attributes:
        key: Unique identifier (e.g., "critical", "non-critical", "production")
        requires_approval: If True, changes in this group need approval workflow
        is_critical: If True, this is a critical environment (e.g., production)
        notes: Description of which environments belong to this group

    Example:
        >>> prod = EnvironmentGroup(
        ...     key="production",
        ...     requires_approval=True,
        ...     is_critical=True,
        ...     notes="Production environment only"
        ... )
        >>> print(prod)
        production (critical, requires approval)
    """

    # =========================================================================
    # LESSON 24: Boolean Fields with Defaults
    # =========================================================================
    # Boolean fields typically have sensible defaults.
    # False is usually the safer default (deny by default, require opt-in)

    key: str                            # Required - unique identifier
    requires_approval: bool = False     # Default: no approval required
    is_critical: bool = False           # Default: not critical
    notes: str = ""                     # Default: empty notes

    def __post_init__(self) -> None:
        """Validate and normalize environment group data."""

        # Validation: Key cannot be empty
        if not self.key or not self.key.strip():
            raise ValueError("Environment group key cannot be empty")

        # Normalize key: lowercase, replace spaces with hyphens
        normalized_key = self.key.lower().strip()
        normalized_key = re.sub(r'\s+', '-', normalized_key)
        normalized_key = re.sub(r'[^a-z0-9-]', '', normalized_key)
        self.key = normalized_key

        # Strip whitespace from notes
        self.notes = self.notes.strip() if self.notes else ""

        # =====================================================================
        # LESSON 25: Business Logic Validation
        # =====================================================================
        # Sometimes we want to enforce business rules in our models.
        # Here's a common pattern: if an environment is critical,
        # it probably should require approvals.
        #
        # Options:
        # 1. Raise an error (strict)
        # 2. Auto-fix (lenient) - what we do here
        # 3. Just warn (logging)

        # Auto-fix: Critical environments should require approval
        if self.is_critical and not self.requires_approval:
            # Option A: Raise error
            # raise ValueError("Critical environments must require approval")

            # Option B: Auto-fix (we'll use this)
            self.requires_approval = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "EnvironmentGroup":
        """Create an EnvironmentGroup from a dictionary."""
        return cls(
            key=data.get("key", ""),
            requires_approval=data.get("requires_approval", False),
            is_critical=data.get("is_critical", False),
            notes=data.get("notes", "")
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        flags = []
        if self.is_critical:
            flags.append("critical")
        if self.requires_approval:
            flags.append("requires approval")

        flag_str = f" ({', '.join(flags)})" if flags else ""
        return f"{self.key}{flag_str}"

    # =========================================================================
    # LESSON 26: Utility Methods
    # =========================================================================
    # Add methods that make the model more useful in real code.
    # Think about what operations you'll commonly need.

    def to_resource_tag(self) -> str:
        """
        Convert to LaunchDarkly resource tag format.

        In LaunchDarkly, you can tag environments and reference them in policies:
            proj/*:env/*;{tag}:flag/*

        Returns:
            str: The tag to use in resource specifiers

        Example:
            >>> group = EnvironmentGroup(key="critical", is_critical=True)
            >>> group.to_resource_tag()
            'critical'
        """
        return self.key


# =============================================================================
# Testing
# =============================================================================
if __name__ == "__main__":
    print("Testing EnvironmentGroup model...")

    # Test 1: Create non-critical group
    dev = EnvironmentGroup(
        key="development",
        requires_approval=False,
        is_critical=False,
        notes="Dev, test, staging environments"
    )
    print(f"Created: {dev}")

    # Test 2: Create critical group
    prod = EnvironmentGroup(
        key="production",
        requires_approval=True,
        is_critical=True,
        notes="Production only"
    )
    print(f"Created: {prod}")

    # Test 3: Auto-fix critical without approval
    auto_fixed = EnvironmentGroup(
        key="critical-no-approval",
        is_critical=True,
        requires_approval=False  # Will be auto-fixed to True
    )
    print(f"Auto-fixed: {auto_fixed}")
    print(f"  requires_approval: {auto_fixed.requires_approval}")  # Should be True

    # Test 4: Key normalization
    normalized = EnvironmentGroup(key="My Environment Group")
    print(f"Normalized key: '{normalized.key}'")  # Should be 'my-environment-group'

    # Test 5: to_dict and from_dict
    data = prod.to_dict()
    print(f"To dict: {data}")

    restored = EnvironmentGroup.from_dict(data)
    print(f"From dict: {restored}")

    # Test 6: Resource tag
    print(f"Resource tag: {prod.to_resource_tag()}")

    print("\nAll tests passed!")
