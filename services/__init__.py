"""
RBAC Builder - Services Package
===============================

This package contains business logic services for the RBAC Builder.

Services:
    - StorageService: Save/load configurations to/from JSON files
    - PayloadBuilder: Generate LaunchDarkly API payloads (Phase 3)
    - ConfigValidator: Validate configurations (Phase 4)
    - LDClient/MockLDClient: LaunchDarkly API integration (Phase 6)
    - Deployer: Execute deployments (Phase 7)

Usage:
    from services import StorageService, PayloadBuilder

    # Initialize storage
    storage = StorageService()

    # Save configuration
    storage.save(config)

    # Build LD payloads from session state
    from services import build_payload_from_session
    payload = build_payload_from_session(
        customer_name="Acme",
        project_key="mobile-app",
        session_state=st.session_state
    )

Learn more: docs/phases/phase2/PYTHON_CONCEPTS.md
"""

# =============================================================================
# LESSON 40: Service Layer Pattern
# =============================================================================
# The "services" package contains business logic that sits between:
#   - UI Layer (app.py) - handles user interaction
#   - Data Layer (models/) - defines data structures
#
# Services handle:
#   - File operations (StorageService)
#   - API calls (ld_client.py - future)
#   - Complex business rules (validation.py - future)
#
# This separation makes code easier to test and maintain.
# UI doesn't know HOW data is saved, it just calls storage.save()

# Import public classes from submodules
from .storage import StorageService
from .payload_builder import (
    PayloadBuilder,
    DeployPayload,
    build_payload_from_session,
    # Phase 11: Role Attributes support
    RoleAttributePayloadBuilder,
    build_role_attribute_payload_from_session,
)
from .validation import (
    ConfigValidator,
    ValidationResult,
    ValidationIssue,
    Severity,
    validate_from_session,
)

# Also export custom exceptions for error handling in UI
from .storage import (
    StorageError,
    ConfigNotFoundError,
    ConfigParseError,
    ConfigWriteError,
)

# LaunchDarkly Client (Phase 6)
from .ld_client_interface import (
    LDClientInterface,
    LDProject,
    LDEnvironment,
    LDTeam,
    LDCustomRole,
)
from .ld_client import LDClient, MockLDClient
from .ld_exceptions import (
    LDClientError,
    LDAuthenticationError,
    LDNotFoundError,
    LDConflictError,
    LDRateLimitError,
    LDValidationError,
    LDServerError,
)

# Deployer (Phase 7)
from .deployer import (
    Deployer,
    DeployResult,
    DeployStepResult,
    DeployStep,
)

from .doc_generator import generate_deployment_guide
from .package_generator import PackageGenerator, PackageGenerationError

# =============================================================================
# LESSON 41: Exporting Exceptions
# =============================================================================
# We export both the service AND its exceptions.
# This allows the UI to catch specific errors:
#
#   from services import StorageService, ConfigNotFoundError
#
#   try:
#       config = storage.load("customer")
#   except ConfigNotFoundError:
#       st.error("Customer not found!")
#
# Without exporting, UI would need verbose imports:
#   from services.storage import ConfigNotFoundError  # Ugly!

__all__ = [
    # Service classes
    "StorageService",
    "PayloadBuilder",
    "DeployPayload",
    "build_payload_from_session",
    # Phase 11: Role Attributes support
    "RoleAttributePayloadBuilder",
    "build_role_attribute_payload_from_session",
    # Validation (Phase 4)
    "ConfigValidator",
    "ValidationResult",
    "ValidationIssue",
    "Severity",
    "validate_from_session",
    # LD Client (Phase 6)
    "LDClientInterface",
    "LDProject",
    "LDEnvironment",
    "LDTeam",
    "LDCustomRole",
    "LDClient",
    "MockLDClient",
    # Storage Exceptions
    "StorageError",
    "ConfigNotFoundError",
    "ConfigParseError",
    "ConfigWriteError",
    # LD Client Exceptions
    "LDClientError",
    "LDAuthenticationError",
    "LDNotFoundError",
    "LDConflictError",
    "LDRateLimitError",
    "LDValidationError",
    "LDServerError",
    # Deployer (Phase 7)
    "Deployer",
    "DeployResult",
    "DeployStepResult",
    "DeployStep",
]

# Package version
__version__ = "1.0.0"
