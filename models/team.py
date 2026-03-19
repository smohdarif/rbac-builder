"""
Team Model
==========

Represents a functional role or persona in the organization.

Examples:
    - Developer team
    - QA Engineer team
    - Product Owner team
    - Administrator team

Learn more: docs/phases/phase1/PYTHON_CONCEPTS.md
"""

# =============================================================================
# LESSON 16: Imports for Dataclasses
# =============================================================================
# We import from the 'dataclasses' module which is part of Python's standard library
# (no need to pip install anything - it comes with Python 3.7+)

from dataclasses import dataclass, field, asdict
from typing import Optional
import re


# =============================================================================
# LESSON 17: The @dataclass Decorator
# =============================================================================
# A decorator is a function that modifies another function or class.
# The @dataclass decorator automatically generates these methods:
#   - __init__()  : Constructor to set attributes
#   - __repr__()  : String representation for debugging
#   - __eq__()    : Equality comparison (team1 == team2)
#
# Without @dataclass, we'd have to write all these methods manually!

@dataclass
class Team:
    """
    Represents a functional role or persona.

    Attributes:
        key: Unique identifier (lowercase, no spaces, e.g., "dev", "qa-team")
        name: Display name (e.g., "Developer", "QA Engineer")
        description: What this team does (optional)

    Example:
        >>> team = Team(key="dev", name="Developer", description="Development team")
        >>> print(team)
        Team(key='dev', name='Developer', description='Development team')
    """

    # =========================================================================
    # LESSON 18: Type Hints in Dataclasses
    # =========================================================================
    # Each field has a name and a type hint (name: type)
    # Type hints tell Python (and your IDE) what type the value should be
    #
    # Fields WITHOUT defaults must come BEFORE fields WITH defaults
    # (Python rule: positional args before keyword args)

    key: str                    # Required - unique identifier
    name: str                   # Required - display name
    description: str = ""       # Optional - defaults to empty string

    # =========================================================================
    # LESSON 19: The __post_init__ Method
    # =========================================================================
    # This special method runs AFTER __init__ finishes.
    # Perfect for:
    #   1. Validating field values
    #   2. Transforming/normalizing data
    #   3. Computing derived fields
    #
    # The flow is: __init__ sets fields → __post_init__ validates/transforms

    def __post_init__(self) -> None:
        """Validate and normalize the team data after initialization."""

        # Validation 1: Key cannot be empty
        if not self.key or not self.key.strip():
            raise ValueError("Team key cannot be empty")

        # Validation 2: Name cannot be empty
        if not self.name or not self.name.strip():
            raise ValueError("Team name cannot be empty")

        # =====================================================================
        # LESSON 20: String Normalization
        # =====================================================================
        # We "normalize" the key to ensure consistency:
        #   - Lowercase: "Dev" → "dev"
        #   - Replace spaces with hyphens: "qa team" → "qa-team"
        #   - Remove special characters
        #   - Strip whitespace
        #
        # This prevents issues like "Dev" and "dev" being treated as different teams

        # Normalize key: lowercase, replace spaces with hyphens, remove special chars
        normalized_key = self.key.lower().strip()
        normalized_key = re.sub(r'\s+', '-', normalized_key)  # spaces → hyphens
        normalized_key = re.sub(r'[^a-z0-9-]', '', normalized_key)  # remove special chars

        # GOTCHA: In a dataclass, you CAN modify self in __post_init__
        # (unlike some other patterns where objects are immutable)
        self.key = normalized_key

        # Strip whitespace from name and description
        self.name = self.name.strip()
        self.description = self.description.strip() if self.description else ""

    # =========================================================================
    # LESSON 21: Custom Methods on Dataclasses
    # =========================================================================
    # Dataclasses are just regular classes with auto-generated methods.
    # You can add your own methods just like any class!

    def to_dict(self) -> dict:
        """
        Convert the Team to a dictionary.

        Useful for:
            - JSON serialization
            - Passing to APIs
            - Storing in databases

        Returns:
            dict: Dictionary with key, name, description

        Example:
            >>> team = Team(key="dev", name="Developer")
            >>> team.to_dict()
            {'key': 'dev', 'name': 'Developer', 'description': ''}
        """
        # asdict() is a helper function from dataclasses module
        # It converts a dataclass instance to a dictionary
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Team":
        """
        Create a Team from a dictionary.

        This is a "factory method" - a class method that creates new instances.
        Useful for loading data from JSON files or APIs.

        Args:
            data: Dictionary with 'key', 'name', and optionally 'description'

        Returns:
            Team: A new Team instance

        Example:
            >>> data = {'key': 'dev', 'name': 'Developer'}
            >>> team = Team.from_dict(data)
        """
        # =====================================================================
        # LESSON 22: @classmethod and cls
        # =====================================================================
        # @classmethod is a decorator that makes this a "class method"
        # - Regular methods receive 'self' (the instance)
        # - Class methods receive 'cls' (the class itself)
        #
        # Why use @classmethod?
        # - Factory methods (create instances in special ways)
        # - Alternative constructors
        # - Methods that work with the class, not a specific instance

        return cls(
            key=data.get("key", ""),
            name=data.get("name", ""),
            description=data.get("description", "")
        )

    def __str__(self) -> str:
        """
        Human-readable string representation.

        __str__ is called by str() and print()
        __repr__ (auto-generated) is for debugging

        Example:
            >>> team = Team(key="dev", name="Developer")
            >>> print(team)  # calls __str__
            Developer (dev)
        """
        return f"{self.name} ({self.key})"


# =============================================================================
# LESSON 23: Module-Level Code and __name__
# =============================================================================
# This block only runs when you execute this file directly:
#   python models/team.py
#
# It does NOT run when the file is imported:
#   from models.team import Team
#
# This is useful for testing during development!

if __name__ == "__main__":
    # Quick test - only runs when executing this file directly
    print("Testing Team model...")

    # Test 1: Create a valid team
    team1 = Team(key="dev", name="Developer", description="Development team")
    print(f"Created: {team1}")
    print(f"Dict: {team1.to_dict()}")

    # Test 2: Key normalization
    team2 = Team(key="QA Team", name="QA Engineer")
    print(f"Normalized key: '{team2.key}'")  # Should be 'qa-team'

    # Test 3: Create from dict
    team3 = Team.from_dict({"key": "admin", "name": "Administrator"})
    print(f"From dict: {team3}")

    # Test 4: Validation error
    try:
        invalid_team = Team(key="", name="No Key")
    except ValueError as e:
        print(f"Validation error (expected): {e}")

    print("\nAll tests passed!")
