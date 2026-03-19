"""
Matrix Tab - Permission Matrix Design
======================================

This module renders Tab 2: Design Matrix.

Responsibilities:
- Per-Project permissions matrix (tab-grouped by feature domain)
- Per-Environment permissions matrix (tab-grouped by feature domain)
- Matrix sync with teams/env groups

LESSON: Phase 15 — Tab-Based Layout
======================================
Permissions are grouped into feature tabs (Flag Lifecycle, Metrics,
AI Configs, Observability) to avoid horizontal scroll and truncated headers.
Groups are defined in core/ld_actions.py as PROJECT_PERMISSION_GROUPS
and ENV_PERMISSION_GROUPS — single source of truth.
"""

import streamlit as st
import pandas as pd
from typing import List

from core.ld_actions import PROJECT_PERMISSION_GROUPS, ENV_PERMISSION_GROUPS

# =============================================================================
# Derived permission lists (flattened from groups — single source of truth)
# =============================================================================
# LESSON: List comprehension with nested loops
# [item for sublist in outer for item in sublist] flattens a list of lists.

PROJECT_PERMISSIONS: List[str] = [
    perm
    for perms in PROJECT_PERMISSION_GROUPS.values()
    for perm in perms
]

ENV_PERMISSIONS: List[str] = [
    perm
    for perms in ENV_PERMISSION_GROUPS.values()
    for perm in perms
]

# =============================================================================
# Short display names for column headers (avoids truncation in narrow columns)
# =============================================================================

SHORT_NAMES = {
    # Flag Lifecycle
    "Create Flags":                    "Create",
    "Update Flags":                    "Update",
    "Archive Flags":                   "Archive",
    "Update Client Side Availability": "Client Side",
    # Metrics & Pipelines
    "Manage Metrics":                  "Metrics",
    "Manage Release Pipelines":        "Pipelines",
    "View Project":                    "View Proj",
    # AI Configs
    "Create AI Configs":               "Create",
    "Update AI Configs":               "Update",
    "Delete AI Configs":               "Delete",
    "Manage AI Variations":            "Variations",
    # Observability
    "View Sessions":                   "Sessions",
    "View Errors":                     "Errors",
    "View Logs":                       "Logs",
    "View Traces":                     "Traces",
    "Manage Alerts":                   "Alerts",
    "Manage Observability Dashboards": "Dashboards",
    "Talk to Vega":                    "Vega AI",
    # Env — Targeting & Approvals
    "Update Targeting":                "Targeting",
    "Review Changes":                  "Review",
    "Apply Changes":                   "Apply",
    # Env — Segments / Experiments / SDK
    "Manage Segments":                 "Segments",
    "Manage Experiments":              "Experiments",
    "View SDK Key":                    "SDK Key",
    "Update AI Config Targeting":      "AI Targeting",
}


# =============================================================================
# Matrix Creation Functions (Public - for testing)
# =============================================================================

def create_default_project_matrix(teams: List[str]) -> pd.DataFrame:
    """
    Create a default project-level permission matrix.

    Args:
        teams: List of team names

    Returns:
        DataFrame with Team column and all permission columns
        (all False except View Project which defaults to True)
    """
    if not teams:
        return pd.DataFrame({"Team": []})

    data = {"Team": teams}
    for perm in PROJECT_PERMISSIONS:
        data[perm] = [perm == "View Project"] * len(teams)

    return pd.DataFrame(data)


def create_default_env_matrix(teams: List[str], env_groups: List[str]) -> pd.DataFrame:
    """
    Create a default environment-level permission matrix.

    Creates one row for each team × environment combination.

    Args:
        teams:      List of team names
        env_groups: List of environment group keys

    Returns:
        DataFrame with Team, Environment, and permission columns
    """
    if not teams or not env_groups:
        return pd.DataFrame({"Team": [], "Environment": []})

    rows = []
    for team in teams:
        for env in env_groups:
            row = {"Team": team, "Environment": env}
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
    """
    if existing_matrix.empty or "Team" not in existing_matrix.columns:
        return create_default_project_matrix(current_teams)

    existing_teams = existing_matrix["Team"].tolist()
    result = existing_matrix[existing_matrix["Team"].isin(current_teams)].copy()

    for team in current_teams:
        if team not in existing_teams:
            new_row = {"Team": team}
            for perm in PROJECT_PERMISSIONS:
                new_row[perm] = perm == "View Project"
            result = pd.concat([result, pd.DataFrame([new_row])], ignore_index=True)

    result = result.set_index("Team").reindex(current_teams).reset_index()
    return result


def sync_env_matrix(
    existing_matrix: pd.DataFrame,
    current_teams: List[str],
    current_envs: List[str]
) -> pd.DataFrame:
    """Sync environment matrix with current team and env lists."""
    if existing_matrix.empty:
        return create_default_env_matrix(current_teams, current_envs)

    existing_perms = {}
    for _, row in existing_matrix.iterrows():
        key = (row.get("Team"), row.get("Environment"))
        existing_perms[key] = {col: row[col] for col in ENV_PERMISSIONS if col in row}

    rows = []
    for team in current_teams:
        for env in current_envs:
            key = (team, env)
            row = {"Team": team, "Environment": env}
            if key in existing_perms:
                for perm in ENV_PERMISSIONS:
                    row[perm] = existing_perms[key].get(perm, False)
            else:
                for perm in ENV_PERMISSIONS:
                    row[perm] = False
            rows.append(row)

    return pd.DataFrame(rows)


# =============================================================================
# Private helpers
# =============================================================================

def _ensure_matrix_columns(matrix: pd.DataFrame, permissions: List[str]) -> pd.DataFrame:
    """Add missing permission columns to a matrix DataFrame."""
    for col in permissions:
        if col not in matrix.columns:
            matrix[col] = False
    return matrix


def _get_proj_value(team: str, perm: str) -> bool:
    """Get current checkbox value from the project matrix."""
    df = st.session_state.project_matrix
    if team in df["Team"].values and perm in df.columns:
        return bool(df.loc[df["Team"] == team, perm].iloc[0])
    return False


def _set_proj_value(team: str, perm: str, value: bool) -> None:
    """Write a changed checkbox value back to the project matrix."""
    st.session_state.project_matrix.loc[
        st.session_state.project_matrix["Team"] == team, perm
    ] = value


def _get_env_value(team: str, env: str, perm: str) -> bool:
    """Get current checkbox value from the env matrix."""
    df = st.session_state.env_matrix
    mask = (df["Team"] == team) & (df["Environment"] == env)
    if mask.any() and perm in df.columns:
        return bool(df.loc[mask, perm].iloc[0])
    return False


def _set_env_value(team: str, env: str, perm: str, value: bool) -> None:
    """Write a changed checkbox value back to the env matrix."""
    mask = (
        (st.session_state.env_matrix["Team"] == team) &
        (st.session_state.env_matrix["Environment"] == env)
    )
    st.session_state.env_matrix.loc[mask, perm] = value


# =============================================================================
# LESSON 53: Shared group renderer (DRY — Don't Repeat Yourself)
# =============================================================================
# Both project and env matrices need the same checkbox-grid pattern.
# We extract the rendering logic into one function that works for both,
# driven by the getter/setter callbacks passed as arguments.

def _render_group_checkboxes(
    perms: List[str],
    row_labels: List[str],
    extra_col_label: str,
    extra_col_values: List[str],
    get_fn,
    set_fn,
    key_prefix: str,
) -> None:
    """
    Render a mini permission matrix for one tab group.

    Args:
        perms:            Permission columns to show
        row_labels:       Primary row label values (team names)
        extra_col_label:  Second column label (e.g. "Environment") or ""
        extra_col_values: Second column values per row (e.g. env names) or []
        get_fn:           Callable(row_label, [extra], perm) → bool
        set_fn:           Callable(row_label, [extra], perm, value) → None
        key_prefix:       Unique prefix for widget keys
    """
    has_extra = bool(extra_col_values)
    n_label_cols = 3 if has_extra else 2
    col_widths = [2] * (n_label_cols - 1) + [1] * len(perms)
    if has_extra:
        col_widths = [2, 2] + [1] * len(perms)

    # Header row
    header_cols = st.columns(col_widths)
    header_cols[0].markdown("**Team**")
    if has_extra:
        header_cols[1].markdown(f"**{extra_col_label}**")
    for i, perm in enumerate(perms):
        header_cols[(1 if not has_extra else 2) + i].markdown(
            f"**{SHORT_NAMES.get(perm, perm)}**"
        )

    # Data rows
    if has_extra:
        # env matrix: one row per team × env
        row_idx = 0
        for team in row_labels:
            for extra_val in extra_col_values:
                data_cols = st.columns(col_widths)
                data_cols[0].write(team)
                data_cols[1].write(extra_val)
                for p_idx, perm in enumerate(perms):
                    cur = get_fn(team, extra_val, perm)
                    key = f"{key_prefix}_{row_idx}_{p_idx}"
                    new = data_cols[2 + p_idx].checkbox(
                        perm, value=cur, key=key, label_visibility="collapsed"
                    )
                    if new != cur:
                        set_fn(team, extra_val, perm, new)
                row_idx += 1
    else:
        # project matrix: one row per team
        for t_idx, team in enumerate(row_labels):
            data_cols = st.columns(col_widths)
            data_cols[0].write(team)
            for p_idx, perm in enumerate(perms):
                cur = get_fn(team, perm)
                key = f"{key_prefix}_{t_idx}_{p_idx}"
                new = data_cols[1 + p_idx].checkbox(
                    perm, value=cur, key=key, label_visibility="collapsed"
                )
                if new != cur:
                    set_fn(team, perm, new)


# =============================================================================
# Private Render Functions
# =============================================================================

def _render_project_matrix_with_checkboxes() -> None:
    """
    Render the per-project permissions matrix using tabs grouped by feature domain.

    LESSON: st.tabs() — tabbed layout
    ====================================
    st.tabs() returns a list of tab objects. Use 'with tab:' to put
    content inside each tab. Only one tab is visible at a time.
    """
    st.subheader("🏗️ Per-Project Permissions")
    st.caption("These permissions impact ALL environments in the project")

    team_names = [n for n in st.session_state.teams["Name"].tolist() if n]
    if not team_names:
        st.warning("No teams defined. Add teams in the Setup tab.")
        return

    # Initialise / sync matrix
    if "project_matrix" not in st.session_state or \
            not isinstance(st.session_state.project_matrix, pd.DataFrame):
        st.session_state.project_matrix = create_default_project_matrix(team_names)
    else:
        st.session_state.project_matrix = _ensure_matrix_columns(
            st.session_state.project_matrix, PROJECT_PERMISSIONS
        )

    matrix_teams = st.session_state.project_matrix["Team"].tolist() \
        if "Team" in st.session_state.project_matrix.columns else []
    if set(matrix_teams) != set(team_names):
        st.session_state.project_matrix = sync_project_matrix(
            st.session_state.project_matrix, team_names
        )

    # ==========================================================================
    # LESSON: st.tabs() with dynamic tab names from a dict
    # ==========================================================================
    # list(dict.keys()) gives the tab labels.
    # zip(tabs[:-1], dict.items()) pairs each tab (except Summary) with its group.
    # tabs[-1] is always the Summary tab.

    group_names = list(PROJECT_PERMISSION_GROUPS.keys())
    tab_labels  = group_names + ["📋 Summary"]
    tabs        = st.tabs(tab_labels)

    # Render one tab per permission group
    for tab, (group_name, perms) in zip(tabs[:-1], PROJECT_PERMISSION_GROUPS.items()):
        with tab:
            _render_group_checkboxes(
                perms=perms,
                row_labels=team_names,
                extra_col_label="",
                extra_col_values=[],
                get_fn=_get_proj_value,
                set_fn=_set_proj_value,
                key_prefix=f"proj_{group_name}",
            )

    # Summary tab — read-only overview of all project permissions
    with tabs[-1]:
        _render_project_summary()


def _render_project_summary() -> None:
    """
    Read-only summary of all project permissions across all groups.

    LESSON: DataFrame.replace() for display formatting
    ====================================================
    .replace() returns a NEW DataFrame with values swapped.
    The original session state DataFrame is unchanged — still has True/False
    for the payload builder to use.
    """
    st.caption("Read-only overview — edit permissions in the tabs above.")

    if "project_matrix" not in st.session_state:
        st.info("No permissions configured yet.")
        return

    display = st.session_state.project_matrix.replace({True: "✅", False: "—"})
    st.dataframe(display, use_container_width=True, hide_index=True)


def _render_env_matrix_with_checkboxes() -> None:
    """
    Render the per-environment permissions matrix using tabs grouped by feature domain.
    """
    st.subheader("🌍 Per-Environment Permissions")

    env_group_keys = [k for k in st.session_state.env_groups["Key"].tolist() if k]
    team_names     = [n for n in st.session_state.teams["Name"].tolist() if n]

    if not team_names or not env_group_keys:
        st.warning("Define teams and environment groups in the Setup tab first.")
        return

    st.caption(
        f"Environment groups: **{', '.join(env_group_keys)}** | "
        f"Teams: **{', '.join(team_names)}**"
    )

    if st.button("🔄 Regenerate Matrix from Setup",
                 help="Rebuild matrix using current Teams and Environment Groups"):
        for key in ("env_matrix", "project_matrix"):
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    # Initialise / sync matrix
    if "env_matrix" not in st.session_state or \
            not isinstance(st.session_state.env_matrix, pd.DataFrame):
        st.session_state.env_matrix = create_default_env_matrix(team_names, env_group_keys)
    else:
        st.session_state.env_matrix = _ensure_matrix_columns(
            st.session_state.env_matrix, ENV_PERMISSIONS
        )

    group_names = list(ENV_PERMISSION_GROUPS.keys())
    tab_labels  = group_names + ["📋 Summary"]
    tabs        = st.tabs(tab_labels)

    for tab, (group_name, perms) in zip(tabs[:-1], ENV_PERMISSION_GROUPS.items()):
        with tab:
            _render_group_checkboxes(
                perms=perms,
                row_labels=team_names,
                extra_col_label="Environment",
                extra_col_values=env_group_keys,
                get_fn=_get_env_value,
                set_fn=_set_env_value,
                key_prefix=f"env_{group_name}",
            )

    with tabs[-1]:
        _render_env_summary()


def _render_env_summary() -> None:
    """Read-only summary of all env permissions."""
    st.caption("Read-only overview — edit permissions in the tabs above.")

    if "env_matrix" not in st.session_state:
        st.info("No permissions configured yet.")
        return

    display = st.session_state.env_matrix.replace({True: "✅", False: "—"})
    st.dataframe(display, use_container_width=True, hide_index=True)


# =============================================================================
# Main Render Function (Public)
# =============================================================================

def render_matrix_tab(customer_name: str = "") -> None:
    """
    Render the Design Matrix tab UI.

    Entry point for Tab 2. Manages session state for:
    - project_matrix: pd.DataFrame (project-level permissions)
    - env_matrix:     pd.DataFrame (environment-level permissions)

    Args:
        customer_name: Customer name from sidebar (for display/validation)
    """
    st.header("Step 2: Design Permission Matrix")

    if not customer_name:
        st.info("Complete Step 1 first.")
        return

    st.markdown("""
    Design your RBAC matrix below. Click checkboxes to toggle permissions.
    - **Rows** = Teams/Personas
    - **Columns** = Permissions
    - **✓** = Permission granted
    """)

    _render_project_matrix_with_checkboxes()
    st.divider()
    _render_env_matrix_with_checkboxes()
