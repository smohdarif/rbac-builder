"""
Environment Detection Utility
=============================

Detects whether the app is running on Streamlit Cloud or localhost.
This helps provide appropriate warnings and behaviors for each environment.

Learn more: docs/phases/phase2/DESIGN.md
"""

import os
from enum import Enum
from dataclasses import dataclass


# =============================================================================
# LESSON 69: Detecting Runtime Environment
# =============================================================================
# Streamlit Cloud sets certain environment variables that we can check.
# This allows us to show different warnings or behaviors based on where
# the app is running.
#
# Common indicators of Streamlit Cloud:
#   - STREAMLIT_SHARING_MODE environment variable
#   - HOSTNAME contains 'streamlit'
#   - HOME is /home/appuser
#
# Why this matters:
#   - Streamlit Cloud has ephemeral storage (files are lost on restart)
#   - Localhost has persistent storage
#   - We need to warn users about data persistence


class RuntimeEnvironment(Enum):
    """
    Enum representing where the app is running.

    Values:
        STREAMLIT_CLOUD: Running on Streamlit Community Cloud
        LOCALHOST: Running locally (development)
        UNKNOWN: Can't determine environment
    """
    STREAMLIT_CLOUD = "streamlit_cloud"
    LOCALHOST = "localhost"
    UNKNOWN = "unknown"


@dataclass
class EnvironmentInfo:
    """
    Information about the current runtime environment.

    Attributes:
        environment: The detected runtime environment
        has_persistent_storage: Whether files are persisted across restarts
        warning_message: User-friendly warning message (if any)
    """
    environment: RuntimeEnvironment
    has_persistent_storage: bool
    warning_message: str | None = None


def detect_environment() -> EnvironmentInfo:
    """
    Detect the current runtime environment.

    Returns:
        EnvironmentInfo with details about the environment

    Example:
        >>> info = detect_environment()
        >>> if not info.has_persistent_storage:
        ...     st.warning(info.warning_message)
    """
    # ==========================================================================
    # LESSON 70: Environment Variable Checks
    # ==========================================================================
    # os.environ is a dict-like object containing all environment variables.
    # We use .get() for safe access (returns None if not found).

    # Check for Streamlit Cloud indicators
    is_streamlit_cloud = False

    # Method 1: Check for STREAMLIT_SHARING_MODE
    if os.environ.get("STREAMLIT_SHARING_MODE"):
        is_streamlit_cloud = True

    # Method 2: Check HOME directory (Streamlit Cloud uses /home/appuser)
    home_dir = os.environ.get("HOME", "")
    if "/home/appuser" in home_dir:
        is_streamlit_cloud = True

    # Method 3: Check HOSTNAME contains 'streamlit'
    hostname = os.environ.get("HOSTNAME", "")
    if "streamlit" in hostname.lower():
        is_streamlit_cloud = True

    # Method 4: Check for Streamlit Cloud specific paths
    if os.path.exists("/home/appuser"):
        is_streamlit_cloud = True

    if is_streamlit_cloud:
        return EnvironmentInfo(
            environment=RuntimeEnvironment.STREAMLIT_CLOUD,
            has_persistent_storage=False,
            warning_message=(
                "Running on Streamlit Cloud. Saved configurations are temporary "
                "and will be lost when the app restarts. Use **Download Config** "
                "to save your work locally, and **Upload Config** to restore it."
            )
        )

    # Check if running locally
    # If we can write to the configs directory, assume localhost
    try:
        from pathlib import Path
        config_path = Path(__file__).parent.parent / "configs"
        if config_path.exists() or config_path.parent.exists():
            return EnvironmentInfo(
                environment=RuntimeEnvironment.LOCALHOST,
                has_persistent_storage=True,
                warning_message=None
            )
    except Exception:
        pass

    # Unknown environment
    return EnvironmentInfo(
        environment=RuntimeEnvironment.UNKNOWN,
        has_persistent_storage=False,
        warning_message=(
            "Could not detect runtime environment. "
            "Configurations may not persist across sessions."
        )
    )


def is_streamlit_cloud() -> bool:
    """
    Quick check if running on Streamlit Cloud.

    Returns:
        True if running on Streamlit Cloud, False otherwise

    Example:
        >>> if is_streamlit_cloud():
        ...     st.info("Running in the cloud!")
    """
    info = detect_environment()
    return info.environment == RuntimeEnvironment.STREAMLIT_CLOUD


def is_localhost() -> bool:
    """
    Quick check if running locally.

    Returns:
        True if running locally, False otherwise
    """
    info = detect_environment()
    return info.environment == RuntimeEnvironment.LOCALHOST


def get_storage_warning() -> str | None:
    """
    Get the storage warning message for the current environment.

    Returns:
        Warning message string, or None if no warning needed

    Example:
        >>> warning = get_storage_warning()
        >>> if warning:
        ...     st.warning(warning)
    """
    info = detect_environment()
    return info.warning_message


# =============================================================================
# Module-level constant for easy access
# =============================================================================
ENVIRONMENT_INFO = detect_environment()
