"""
Matrix Tab - Permission Matrix Design
======================================

This module renders Tab 2: Design Matrix.

Responsibilities:
- Per-Project permissions matrix
- Per-Environment permissions matrix
- Matrix sync with teams/env groups
"""

import streamlit as st
import pandas as pd
from typing import List, Optional

# =============================================================================
# LESSON: Permission Column Constants
# =============================================================================
# Defining permissions as constants makes it easy to:
# 1. Add new permissions in one place
# 2. Reference in tests
# 3. Generate default matrices consistently

# =============================================================================
# Project-Level Permissions (Impact ALL environments)
# =============================================================================
# These actions are NOT scoped to a specific environment.
# Example: "Create Flags" creates a flag visible in all environments.

PROJECT_PERMISSIONS = [
    "Create Flags",                    # Flags created in all envs, default to off
    "Update Flags",                    # Metadata only, can not impact evaluation
    "Archive Flags",                   # Impacts all envs, can be undone
    "Update Client Side Availability", # Determines if flags served to client SDKs
    "Manage Metrics",                  # For experimentation and guarded rollouts
    "Manage Release Pipelines",        # Can not delete/modify in-use pipelines
    "Create AI Configs",               # Create new AI configs
    "Update AI Configs",               # Update existing AI configs
    "Delete AI Configs",               # Delete AI configs (destructive)
    "Manage AI Variations",            # Update and delete AI config variations
    "View Project",                    # All roles include this by default
]

# =============================================================================
# Environment-Level Permissions (Scoped to specific environment)
# =============================================================================
# These actions are scoped to a specific environment (Test, Production, etc.)

ENV_PERMISSIONS = [
    "Update Targeting",           # updateOn, updateFallthrough, updateTargets, updateRules
    "Review Changes",             # reviewApprovalRequest
    "Apply Changes",              # applyApprovalRequest
    "Manage Segments",            # Full segment CRUD + targeting
    "Manage Experiments",         # createExperiment, updateExperiment, etc.
    "Update AI Config Targeting", # updateAIConfigTargeting
    "View SDK Key",               # viewSdkKey
]


# =============================================================================
# Matrix Creation Functions (Public - for testing)
# =============================================================================

def create_default_project_matrix(teams: List[str]) -> pd.DataFrame:
    """
    Create a default project-level permission matrix.

    Args:
        teams: List of team names

    Returns:
        DataFrame with Team column and permission columns (all False except View Project)
    """
    if not teams:
        return pd.DataFrame({"Team": []})

    data = {"Team": teams}

    # Add all permission columns with defaults
    for perm in PROJECT_PERMISSIONS:
        if perm == "View Project":
            data[perm] = [True] * len(teams)  # View is granted by default
        else:
            data[perm] = [False] * len(teams)

    return pd.DataFrame(data)


def create_default_env_matrix(teams: List[str], env_groups: List[str]) -> pd.DataFrame:
    """
    Create a default environment-level permission matrix.

    Creates one row for each team × environment combination.

    Args:
        teams: List of team names
        env_groups: List of environment group keys

    Returns:
        DataFrame with Team, Environment, and permission columns
    """
    if not teams or not env_groups:
        return pd.DataFrame({"Team": [], "Environment": []})

    rows = []
    for team in teams:
        for env in env_groups:
            row = {
                "Team": team,
                "Environment": env,
            }
            # Add all permission columns as False
            for perm in ENV_PERMISSIONS:
                row[perm] = False
            rows.append(row)

    return pd.DataFrame(rows)


def sync_project_matrix(
    existing_matrix: pd.DataFrame,
    current_teams: List[str]
) -> pd.DataFrame:
    """
    Sync project matrix with current team list.

    - Removes rows for deleted teams
    - Adds rows for new teams (with default permissions)
    - Preserves permissions for existing teams

    Args:
        existing_matrix: Current project matrix DataFrame
        current_teams: Current list of team names

    Returns:
        Updated DataFrame synced with team list
    """
    if existing_matrix.empty or "Team" not in existing_matrix.columns:
        return create_default_project_matrix(current_teams)

    # Get existing teams from matrix
    existing_teams = existing_matrix["Team"].tolist()

    # Start with rows for teams that still exist
    result = existing_matrix[existing_matrix["Team"].isin(current_teams)].copy()

    # Add rows for new teams
    for team in current_teams:
        if team not in existing_teams:
            new_row = {"Team": team}
            for perm in PROJECT_PERMISSIONS:
                if perm == "View Project":
                    new_row[perm] = True
                else:
                    new_row[perm] = False
            result = pd.concat([result, pd.DataFrame([new_row])], ignore_index=True)

    # Reorder to match current_teams order
    result = result.set_index("Team").reindex(current_teams).reset_index()

    return result


def sync_env_matrix(
    existing_matrix: pd.DataFrame,
    current_teams: List[str],
    current_envs: List[str]
) -> pd.DataFrame:
    """
    Sync environment matrix with current team and env lists.

    Args:
        existing_matrix: Current env matrix DataFrame
        current_teams: Current list of team names
        current_envs: Current list of environment keys

    Returns:
        Updated DataFrame synced with team and env lists
    """
    if existing_matrix.empty:
        return create_default_env_matrix(current_teams, current_envs)

    # Build lookup for existing permissions
    existing_perms = {}
    for _, row in existing_matrix.iterrows():
        key = (row.get("Team"), row.get("Environment"))
        existing_perms[key] = {col: row[col] for col in ENV_PERMISSIONS if col in row}

    # Build new matrix
    rows = []
    for team in current_teams:
        for env in current_envs:
            key = (team, env)
            row = {"Team": team, "Environment": env}

            # Use existing permissions if available
            if key in existing_perms:
                for perm in ENV_PERMISSIONS:
                    row[perm] = existing_perms[key].get(perm, False)
            else:
                for perm in ENV_PERMISSIONS:
                    row[perm] = False

            rows.append(row)

    return pd.DataFrame(rows)


# =============================================================================
# Private Render Functions
# =============================================================================

def _ensure_matrix_columns(matrix: pd.DataFrame, permissions: List[str]) -> pd.DataFrame:
    """
    Ensure matrix has all required permission columns.

    Adds missing columns (e.g., when new features like AI Configs are added).
    """
    for col in permissions:
        if col not in matrix.columns:
            matrix[col] = False
    return matrix


def _render_project_matrix_with_checkboxes() -> None:
    """Render the per-project permissions matrix using individual checkboxes."""
    st.subheader("🏗️ Per-Project Permissions")
    st.caption("These permissions impact ALL environments in the project")

    # Get team names from session state
    team_names = [n for n in st.session_state.teams["Name"].tolist() if n]

    if not team_names:
        st.warning("No teams defined. Add teams in the Setup tab.")
        return

    # Initialize project matrix if needed
    if "project_matrix" not in st.session_state:
        st.session_state.project_matrix = create_default_project_matrix(team_names)
    elif not isinstance(st.session_state.project_matrix, pd.DataFrame):
        st.session_state.project_matrix = create_default_project_matrix(team_names)
    else:
        st.session_state.project_matrix = _ensure_matrix_columns(
            st.session_state.project_matrix,
            PROJECT_PERMISSIONS
        )

    # Sync matrix with current teams
    matrix_teams = st.session_state.project_matrix["Team"].tolist() if "Team" in st.session_state.project_matrix.columns else []
    if set(matrix_teams) != set(team_names):
        st.session_state.project_matrix = sync_project_matrix(
            st.session_state.project_matrix,
            team_names
        )

    # =============================================================================
    # LESSON: Using st.checkbox for Single-Click Behavior
    # =============================================================================
    # st.data_editor can require double-click. Using individual checkboxes
    # guarantees single-click toggle behavior.

    # Create header row
    # Map full names to shorter display names for the header
    SHORT_NAMES = {
        "Create Flags": "Create Flags",
        "Update Flags": "Update Flags",
        "Archive Flags": "Archive Flags",
        "Update Client Side Availability": "Client Side",
        "Manage Metrics": "Metrics",
        "Manage Release Pipelines": "Pipelines",
        "Create AI Configs": "Create AI",
        "Update AI Configs": "Update AI",
        "Delete AI Configs": "Delete AI",
        "Manage AI Variations": "AI Variations",
        "View Project": "View Project",
    }

    cols = st.columns([2] + [1] * len(PROJECT_PERMISSIONS))
    cols[0].markdown("**Team**")
    for i, perm in enumerate(PROJECT_PERMISSIONS):
        short_name = SHORT_NAMES.get(perm, perm)
        cols[i + 1].markdown(f"**{short_name}**")

    # Create checkbox rows for each team
    for team_idx, team in enumerate(team_names):
        cols = st.columns([2] + [1] * len(PROJECT_PERMISSIONS))
        cols[0].write(team)

        for perm_idx, perm in enumerate(PROJECT_PERMISSIONS):
            # Get current value from matrix
            current_value = False
            if team in st.session_state.project_matrix["Team"].values:
                row = st.session_state.project_matrix[st.session_state.project_matrix["Team"] == team]
                if perm in row.columns:
                    current_value = bool(row[perm].iloc[0])

            # Create checkbox with unique key
            key = f"proj_{team_idx}_{perm_idx}"
            new_value = cols[perm_idx + 1].checkbox(
                perm,
                value=current_value,
                key=key,
                label_visibility="collapsed"
            )

            # Update matrix if value changed
            if new_value != current_value:
                st.session_state.project_matrix.loc[
                    st.session_state.project_matrix["Team"] == team, perm
                ] = new_value


def _render_env_matrix_with_checkboxes() -> None:
    """Render the per-environment permissions matrix using individual checkboxes."""
    st.subheader("🌍 Per-Environment Permissions")

    # Get current teams and env groups from session state
    env_group_keys = [k for k in st.session_state.env_groups["Key"].tolist() if k]
    team_names = [n for n in st.session_state.teams["Name"].tolist() if n]

    if not team_names or not env_group_keys:
        st.warning("Define teams and environment groups in the Setup tab first.")
        return

    st.caption(f"Environment groups: **{', '.join(env_group_keys)}** | Teams: **{', '.join(team_names)}**")

    # Button to regenerate matrix
    if st.button(
        "🔄 Regenerate Matrix from Setup",
        help="Rebuild matrix using current Teams and Environment Groups"
    ):
        if "env_matrix" in st.session_state:
            del st.session_state.env_matrix
        if "project_matrix" in st.session_state:
            del st.session_state.project_matrix
        st.rerun()

    # Initialize or sync env matrix
    if "env_matrix" not in st.session_state:
        st.session_state.env_matrix = create_default_env_matrix(team_names, env_group_keys)
    elif not isinstance(st.session_state.env_matrix, pd.DataFrame):
        st.session_state.env_matrix = create_default_env_matrix(team_names, env_group_keys)
    else:
        st.session_state.env_matrix = _ensure_matrix_columns(
            st.session_state.env_matrix,
            ENV_PERMISSIONS
        )

    # Create header row
    # Map full names to shorter display names for the header
    ENV_SHORT_NAMES = {
        "Update Targeting": "Targeting",
        "Review Changes": "Review",
        "Apply Changes": "Apply",
        "Manage Segments": "Segments",
        "Manage Experiments": "Experiments",
        "Update AI Config Targeting": "AI Targeting",
        "View SDK Key": "SDK Key",
    }

    cols = st.columns([2, 2] + [1] * len(ENV_PERMISSIONS))
    cols[0].markdown("**Team**")
    cols[1].markdown("**Environment**")
    for i, perm in enumerate(ENV_PERMISSIONS):
        short_name = ENV_SHORT_NAMES.get(perm, perm)
        cols[i + 2].markdown(f"**{short_name}**")

    # Create checkbox rows for each team/env combination
    row_idx = 0
    for team in team_names:
        for env in env_group_keys:
            cols = st.columns([2, 2] + [1] * len(ENV_PERMISSIONS))
            cols[0].write(team)
            cols[1].write(env)

            for perm_idx, perm in enumerate(ENV_PERMISSIONS):
                # Get current value from matrix
                current_value = False
                mask = (st.session_state.env_matrix["Team"] == team) & \
                       (st.session_state.env_matrix["Environment"] == env)
                if mask.any():
                    row = st.session_state.env_matrix[mask]
                    if perm in row.columns:
                        current_value = bool(row[perm].iloc[0])

                # Create checkbox with unique key
                key = f"env_{row_idx}_{perm_idx}"
                new_value = cols[perm_idx + 2].checkbox(
                    perm,
                    value=current_value,
                    key=key,
                    label_visibility="collapsed"
                )

                # Update matrix if value changed
                if new_value != current_value:
                    st.session_state.env_matrix.loc[mask, perm] = new_value

            row_idx += 1


def _render_matrix_summary() -> None:
    """Render summary view of both matrices."""
    st.subheader("📋 Matrix Summary")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("**Per-Project Permissions**")
        if "project_matrix" in st.session_state:
            st.dataframe(
                st.session_state.project_matrix,
                use_container_width=True,
                hide_index=True
            )

    with col2:
        st.caption("**Per-Environment Permissions**")
        if "env_matrix" in st.session_state:
            st.dataframe(
                st.session_state.env_matrix,
                use_container_width=True,
                hide_index=True
            )


# =============================================================================
# Main Render Function (Public)
# =============================================================================

def render_matrix_tab(customer_name: str = "") -> None:
    """
    Render the Design Matrix tab UI.

    This is the main entry point for Tab 2. It manages session state for:
    - project_matrix: pd.DataFrame (project-level permissions)
    - env_matrix: pd.DataFrame (environment-level permissions)

    Args:
        customer_name: Customer name from sidebar (for validation)
    """
    st.header("Step 2: Design Permission Matrix")

    if not customer_name:
        st.info("Complete Step 1 first.")
        return

    # Instructions
    st.markdown("""
    Design your RBAC matrix below. Click checkboxes to toggle permissions.
    - **Rows** = Teams/Personas
    - **Columns** = Permissions
    - **✓** = Permission granted
    """)

    # Render project matrix with checkboxes
    _render_project_matrix_with_checkboxes()

    st.divider()

    # Render env matrix with checkboxes
    _render_env_matrix_with_checkboxes()

    st.divider()

    # Summary view
    _render_matrix_summary()
