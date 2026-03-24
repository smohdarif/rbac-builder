"""
Setup Tab - Customer Info, Teams, and Environment Groups
=========================================================

This module renders Tab 1: Setup.

Responsibilities:
- Customer name display (from sidebar)
- Project key input
- Teams DataFrame editor
- Environment Groups DataFrame editor
"""

import streamlit as st
import pandas as pd
from typing import Optional

# =============================================================================
# LESSON: Default Data Constants
# =============================================================================
# These define the initial state when a user first loads the app.
# Using constants makes it easy to reset to defaults.

DEFAULT_ENV_GROUPS = pd.DataFrame({
    "Key": ["Test", "Production"],
    "Requires Approvals": [False, True],
    "Critical": [False, True],
    "Notes": ["Development, QA, Staging", "Production environments"]
})

DEFAULT_TEAMS = pd.DataFrame({
    "Key": ["dev", "qa", "po", "admin"],
    "Name": ["Developer", "QA Engineer", "Product Owner", "Administrator"],
    "Description": ["Development team", "Quality assurance", "Product management", "Full access"]
})


# =============================================================================
# Helper Functions
# =============================================================================

def ensure_dataframe(data, default_data: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure data is a DataFrame, reset to default if corrupted.

    Session state can sometimes get corrupted (e.g., data becomes a list).
    This helper ensures we always have a valid DataFrame.

    Args:
        data: The data to validate
        default_data: Default DataFrame to use if data is invalid

    Returns:
        A valid pandas DataFrame
    """
    if not isinstance(data, pd.DataFrame):
        return default_data.copy()
    return data


def _initialize_session_state() -> None:
    """
    Initialize session state with default values if not already set.

    This is called at the start of render_setup_tab to ensure all
    required session state keys exist.
    """
    # Initialize env_groups
    if "env_groups" not in st.session_state:
        st.session_state.env_groups = DEFAULT_ENV_GROUPS.copy()
    else:
        st.session_state.env_groups = ensure_dataframe(
            st.session_state.env_groups,
            DEFAULT_ENV_GROUPS.copy()
        )

    # Initialize teams
    if "teams" not in st.session_state:
        st.session_state.teams = DEFAULT_TEAMS.copy()
    else:
        st.session_state.teams = ensure_dataframe(
            st.session_state.teams,
            DEFAULT_TEAMS.copy()
        )

    # =================================================================
    # LESSON 39: Role Attributes Mode (Phase 11)
    # =================================================================
    # Initialize generation mode and project isolation options

    if "generation_mode" not in st.session_state:
        st.session_state.generation_mode = "role_attributes"

    # Project isolation options (ps-terraform-private pattern)
    if "prefix_team_keys" not in st.session_state:
        st.session_state.prefix_team_keys = True

    if "team_name_format" not in st.session_state:
        st.session_state.team_name_format = "{project}: {team}"


# =============================================================================
# Render Functions (Private)
# =============================================================================

def _render_customer_info(customer_name: str, mode: str) -> None:
    """
    Render customer and project info section.

    Args:
        customer_name: Customer name from sidebar
        mode: Mode selection (Manual/Connected) from sidebar
    """
    if not customer_name:
        st.warning("👈 Please enter a customer name in the sidebar to continue.")
        return

    st.success(f"Customer: **{customer_name}** | Mode: **{mode}**")


def _render_generation_mode() -> None:
    """
    Render toggle for generation mode (Hardcoded vs Role Attributes).

    LESSON 40: Role Attributes vs Hardcoded Mode
    =============================================
    - Hardcoded: Creates separate roles for each team×environment
      Good for: Single project, simple setup
    - Role Attributes: Creates template roles with placeholders
      Good for: Multi-project, enterprise scale
    """
    st.subheader("Generation Mode")

    mode = st.radio(
        "Select role generation approach:",
        options=["hardcoded", "role_attributes"],
        format_func=lambda x: {
            "hardcoded": "Hardcoded (Project-specific roles)",
            "role_attributes": "Role Attributes (Template roles)"
        }[x],
        help=(
            "**Hardcoded**: Creates separate roles for each team/environment. "
            "Best for single project deployments.\n\n"
            "**Role Attributes**: Creates reusable template roles with placeholders. "
            "Best for multi-project enterprise deployments."
        ),
        index=1 if st.session_state.generation_mode == "role_attributes" else 0,
        key="generation_mode_radio"
    )

    st.session_state.generation_mode = mode

    # Show comparison info
    if mode == "hardcoded":
        st.caption("Creates `dev-production`, `dev-test`, `qa-production`, etc.")
    else:
        st.caption("Creates `update-targeting`, `manage-segments`, etc. (shared by all teams)")


def _render_project_input() -> None:
    """Render project key input field (for hardcoded mode)."""
    st.subheader("Project")

    # Store project key in session state for cross-tab access
    st.session_state.project = st.text_input(
        "Enter project key",
        value=st.session_state.get("project", "default"),
        help="Enter the LaunchDarkly project key (e.g., 'mobile-app', 'web-platform')"
    )


def _render_default_projects_input() -> None:
    """
    Render project isolation options (for role attributes mode).

    Following ps-terraform-private pattern:
    - Each team has ONE project in roleAttributes (isolation)
    - Team keys are prefixed with project name (e.g., "voya-dev")
    - Team names include project prefix (e.g., "Voya: Developer")
    """
    st.subheader("Project Isolation")

    # Project key input (same as hardcoded mode but with different context)
    st.session_state.project = st.text_input(
        "Project Key",
        value=st.session_state.get("project", ""),
        help="Enter the LaunchDarkly project key (e.g. 'voya-web'). Each team is isolated to this project. For multi-project deployments, generate separate payloads per project.",
        key="project_key_role_attr",
        placeholder="e.g. voya-web"
    )

    project_key = st.session_state.get("project", "default") or "default"

    # Team key prefix option
    st.session_state.prefix_team_keys = st.checkbox(
        "Prefix team keys with project name",
        value=st.session_state.get("prefix_team_keys", True),
        help="Creates 'voya-dev' instead of 'dev' for project isolation"
    )

    if st.session_state.prefix_team_keys:
        st.caption(f"Example: 'dev' → '{project_key}-dev'")

        # Name format option
        name_format = st.radio(
            "Team name format",
            options=["{team}", "{project}: {team}"],
            index=0 if st.session_state.get("team_name_format") == "{team}" else 1,
            format_func=lambda x: {
                "{team}": "Plain (Developer)",
                "{project}: {team}": f"Prefixed ({project_key.replace('-', ' ').title()}: Developer)"
            }[x],
            horizontal=True
        )
        st.session_state.team_name_format = name_format
    else:
        st.session_state.team_name_format = "{team}"


def _render_env_groups_editor() -> None:
    """
    Render the environment groups DataFrame editor.

    Environment groups categorize environments (e.g., Test, Production)
    for permission scoping. Production environments typically require approvals.
    """
    st.subheader("Environment Groups")
    st.caption("Define environment categories for permission scoping")

    # =============================================================================
    # LESSON: data_editor captures edits automatically
    # =============================================================================
    # st.data_editor returns the edited DataFrame directly.
    # We capture it and update session_state for cross-tab sharing.

    st.session_state.env_groups = st.data_editor(
        st.session_state.env_groups,
        num_rows="dynamic",  # Allow adding/removing rows
        use_container_width=True,
        key=f"env_groups_editor_v{st.session_state.get('_matrix_version', 0)}",
        column_config={
            "Key": st.column_config.TextColumn(
                "Key",
                help="Environment group identifier (e.g., 'Test', 'Production')"
            ),
            "Requires Approvals": st.column_config.CheckboxColumn(
                "Requires Approvals",
                help="If True, changes require approval workflow"
            ),
            "Critical": st.column_config.CheckboxColumn(
                "Critical",
                help="Critical environments are checked during lifecycle/archive operations"
            ),
            "Notes": st.column_config.TextColumn(
                "Notes",
                help="Which environments belong to this group"
            )
        }
    )

    st.caption(f"🌍 {len(st.session_state.env_groups)} environment group(s) defined")


def _render_teams_editor() -> None:
    """
    Render the teams DataFrame editor.

    Teams represent personas or functional roles in the organization.
    Each team will get different permissions in the matrix.
    """
    st.subheader("Teams / Functional Roles")

    # Editable DataFrame with dynamic rows
    st.session_state.teams = st.data_editor(
        st.session_state.teams,
        num_rows="dynamic",  # Allow adding/removing rows
        use_container_width=True,
        key=f"teams_editor_v{st.session_state.get('_matrix_version', 0)}",
        column_config={
            "Key": st.column_config.TextColumn(
                "Key",
                help="Unique identifier (lowercase, no spaces)"
            ),
            "Name": st.column_config.TextColumn(
                "Name",
                help="Display name for the team"
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                help="Team description"
            )
        }
    )

    st.caption(f"📝 {len(st.session_state.teams)} teams defined")


# =============================================================================
# Main Render Function (Public)
# =============================================================================

def render_setup_tab(customer_name: str = "", mode: str = "Manual") -> None:
    """
    Render the Setup tab UI.

    This is the main entry point for Tab 1. It reads customer_name and mode
    from parameters (passed from sidebar) and manages session state for:
    - project: str (project key)
    - teams: pd.DataFrame (teams/personas)
    - env_groups: pd.DataFrame (environment groups)
    - generation_mode: str ("hardcoded" or "role_attributes")
    - prefix_team_keys: bool (for role attributes mode - prefix teams with project)
    - team_name_format: str (for role attributes mode - format for team names)

    Args:
        customer_name: Customer name from sidebar input
        mode: Mode selection (Manual/Connected) from sidebar
    """
    # Initialize session state with defaults
    _initialize_session_state()

    # Header
    st.header("Step 1: Setup")

    # Customer info section
    _render_customer_info(customer_name, mode)

    # Only show the rest if customer name is provided
    if not customer_name:
        return

    # =================================================================
    # LESSON 41: Conditional UI Based on Generation Mode
    # =================================================================
    # Show different inputs based on whether user selects hardcoded
    # or role_attributes mode.

    # Three-column layout: Generation Mode | Project Isolation | Environment Groups (wider)
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        _render_generation_mode()

    with col2:
        # Show appropriate project input based on mode
        if st.session_state.generation_mode == "hardcoded":
            _render_project_input()
        else:
            _render_default_projects_input()

    with col3:
        _render_env_groups_editor()

    st.divider()

    # Teams section (full width)
    _render_teams_editor()

    # =================================================================
    # Show mode-specific info at bottom
    # =================================================================
    if st.session_state.generation_mode == "role_attributes":
        st.info(
            "**Role Attributes Mode**: Template roles will be created with "
            "`${roleAttribute/...}` placeholders. Teams will specify their "
            "access via roleAttributes. This is ideal for multi-project deployments."
        )
