"""
UI Modules for RBAC Builder
===========================

Each module exports a render function that draws one tab.

Usage:
    from ui import render_setup_tab, render_matrix_tab, render_deploy_tab, render_reference_tab

    with tab1:
        render_setup_tab()
"""

# =============================================================================
# LESSON: Package Exports
# =============================================================================
# This file controls what's available when someone imports from the ui package.
# The dot (.) means "current package" - this is a relative import.

from .setup_tab import render_setup_tab
from .matrix_tab import (
    render_matrix_tab,
    create_default_project_matrix,
    create_default_env_matrix,
    sync_project_matrix,
    PROJECT_PERMISSIONS,
    ENV_PERMISSIONS,
)
from .deploy_tab import render_deploy_tab, build_config_from_session
from .advisor_tab import render_advisor_tab
from .reference_tab import (
    render_reference_tab,
    HIERARCHY_DIAGRAM,
    KEY_TERMS,
    BUILTIN_ROLES,
)

# =============================================================================
# LESSON: __all__ defines public API
# =============================================================================
# This list defines what gets exported with "from ui import *"
# Though "import *" is generally discouraged, this documents the public API

__all__ = [
    # Render functions
    "render_setup_tab",
    "render_matrix_tab",
    "render_deploy_tab",
    "render_advisor_tab",
    "render_reference_tab",
    # Matrix helpers (for testing)
    "create_default_project_matrix",
    "create_default_env_matrix",
    "sync_project_matrix",
    "PROJECT_PERMISSIONS",
    "ENV_PERMISSIONS",
    # Deploy helpers (for testing)
    "build_config_from_session",
    # Reference content (for testing)
    "HIERARCHY_DIAGRAM",
    "KEY_TERMS",
    "BUILTIN_ROLES",
]
