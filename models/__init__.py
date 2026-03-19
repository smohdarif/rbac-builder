"""
RBAC Builder - Data Models Package
==================================

This package contains dataclass models for RBAC configuration.

Models:
    - Team: Represents a functional role/persona
    - EnvironmentGroup: Category of environments (critical/non-critical)
    - ProjectPermission: Project-level permissions for a team
    - EnvironmentPermission: Environment-level permissions
    - RBACConfig: Complete configuration container

Usage:
    from models import Team, EnvironmentGroup, RBACConfig

    # Create a team
    team = Team(key="dev", name="Developer", description="Dev team")

    # Create an environment group
    env = EnvironmentGroup(key="production", is_critical=True)

    # Create complete config
    config = RBACConfig(
        customer_name="Acme",
        project_key="mobile-app",
        teams=[team],
        env_groups=[env]
    )

    # Serialize to JSON
    json_str = config.to_json()

    # Load from JSON
    loaded = RBACConfig.from_json(json_str)

Learn more: docs/phases/phase1/PYTHON_CONCEPTS.md#7-python-packages-and-__init__py
"""

# =============================================================================
# LESSON 38: Package Exports via __init__.py
# =============================================================================
# This file controls what gets exported when someone imports from 'models'.
#
# Without these imports:
#   from models import Team  # ❌ ImportError
#   from models.team import Team  # ✅ Works but verbose
#
# With these imports:
#   from models import Team  # ✅ Works!
#   from models import *  # ✅ Imports everything in __all__

# Import all public classes from submodules
from .team import Team
from .environment import EnvironmentGroup
from .permissions import ProjectPermission, EnvironmentPermission
from .config import RBACConfig

# =============================================================================
# LESSON 39: The __all__ Variable
# =============================================================================
# __all__ defines what gets exported when someone does:
#   from models import *
#
# It's also used by IDEs for autocomplete suggestions.
# Only include public API - don't export internal helpers.

__all__ = [
    # Core models
    "Team",
    "EnvironmentGroup",
    "ProjectPermission",
    "EnvironmentPermission",
    "RBACConfig",
]

# Package version
__version__ = "1.0.0"
