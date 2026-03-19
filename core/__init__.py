"""
Core Module
===========

Core utilities, constants, and environment detection for the RBAC Builder.

This module provides:
    - Environment detection (Streamlit Cloud vs localhost)
    - LaunchDarkly action mappings (Phase 3)
    - Shared constants
"""

# =============================================================================
# LESSON 71: Core Module Organization
# =============================================================================
# The core module contains shared utilities that are used across the app.
# Currently includes:
#   - environment.py: Runtime environment detection
#   - ld_actions.py: LaunchDarkly action mappings (Phase 3)

from .environment import (
    RuntimeEnvironment,
    EnvironmentInfo,
    detect_environment,
    is_streamlit_cloud,
    is_localhost,
    get_storage_warning,
    ENVIRONMENT_INFO,
)

from .ld_actions import (
    ProjectAction,
    EnvironmentAction,
    PROJECT_PERMISSION_MAP,
    ENV_PERMISSION_MAP,
    get_project_actions,
    get_env_actions,
    get_all_project_permissions,
    get_all_env_permissions,
    build_project_resource,
    build_flag_resource,
    build_segment_resource,
    build_env_resource,
)

__all__ = [
    # Environment detection
    "RuntimeEnvironment",
    "EnvironmentInfo",
    "detect_environment",
    "is_streamlit_cloud",
    "is_localhost",
    "get_storage_warning",
    "ENVIRONMENT_INFO",
    # LaunchDarkly action mappings
    "ProjectAction",
    "EnvironmentAction",
    "PROJECT_PERMISSION_MAP",
    "ENV_PERMISSION_MAP",
    "get_project_actions",
    "get_env_actions",
    "get_all_project_permissions",
    "get_all_env_permissions",
    "build_project_resource",
    "build_flag_resource",
    "build_segment_resource",
    "build_env_resource",
]
