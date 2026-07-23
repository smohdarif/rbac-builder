"""
Config Importer Service (Phase 28)
==================================

Normalises an uploaded RBAC config JSON — in EITHER of the two on-disk schemas the
app produces — into a single canonical in-memory shape the Setup tab can restore from.

The app persists configs in TWO different schemas:

    Schema A ("storage")   RBACConfig.to_dict() — snake_case keys, teams referenced by
                           `team_key`. Written by `services/storage.py` (the Save button).
                           Example: configs/customers/voya/config.json

    Schema B ("download")  ui/deploy_tab._build_config_dict() — Title-Case keys with
                           spaces (the DataFrame column labels), permissions reference a
                           team by its DISPLAY NAME in a "Team" field.
                           Example: configs/customers/iseatz/2026.05.12iseatz_rbac_config.json

This service accepts either and returns a `NormalizedConfig`.

Why a NormalizedConfig as well as an RBACConfig?
------------------------------------------------
`NormalizedConfig` is a schema-agnostic intermediate keyed by UI label — it is what the
Setup-tab restore hydrates from (the matrix DataFrames use UI labels), and it keeps every
column verbatim. `to_rbac_config()` converts it to the canonical `RBACConfig`.

Historically the `ProjectPermission` model only held 10 of the 18 project columns, so
`to_rbac_config()` was lossy. As of the Phase 28 unification the model holds ALL columns
(observability + "Manage AI Variations" included), so `to_rbac_config()` is now lossless —
which is what lets the Download button emit Schema A without dropping data.

Learn more: docs/phases/phase28/DESIGN.md
"""

from __future__ import annotations

# =============================================================================
# LESSON: `from __future__ import annotations`
# =============================================================================
# This makes all type hints lazy (strings), so we can reference `pd.DataFrame`
# and our own classes in annotations without import-order headaches. It's a
# common modern-Python convenience at the top of a module.

from dataclasses import dataclass, field
from typing import Any, Optional
import json

import pandas as pd

from core.ld_actions import get_all_project_permissions, get_all_env_permissions
from models import (
    RBACConfig,
    Team,
    EnvironmentGroup,
    ProjectPermission,
    EnvironmentPermission,
)


# =============================================================================
# Constants — schema identifiers + the canonical permission label lists
# =============================================================================
# LESSON: We treat core/ld_actions.py as the single source of truth for which
# permission columns exist. Deriving the lists here (instead of hardcoding)
# means new permissions automatically flow through the importer.

SCHEMA_STORAGE = "A"    # snake_case (RBACConfig.to_dict / storage)
SCHEMA_DOWNLOAD = "B"   # Title-Case (DataFrame dump / download button)

PROJECT_PERMISSION_LABELS: list[str] = get_all_project_permissions()  # 18 UI labels
ENV_PERMISSION_LABELS: list[str] = get_all_env_permissions()          # 7 UI labels

# UI label -> RBACConfig model field. As of the Phase 28 unification, the model holds
# EVERY project-permission column (incl. observability), so this map is complete and
# to_rbac_config() is lossless for project permissions.
PROJECT_LABEL_TO_FIELD: dict[str, str] = {
    "Create Flags": "create_flags",
    "Update Flags": "update_flags",
    "Archive Flags": "archive_flags",
    "Update Client Side Availability": "update_client_side_availability",
    "Manage Metrics": "manage_metrics",
    "Manage Release Pipelines": "manage_release_pipelines",
    "View Project": "view_project",
    "Create AI Configs": "create_ai_configs",
    "Update AI Configs": "update_ai_configs",
    "Delete AI Configs": "delete_ai_configs",
    "Manage AI Variations": "manage_ai_variations",
    # Observability (Phase 14)
    "View Sessions": "view_sessions",
    "View Errors": "view_errors",
    "View Logs": "view_logs",
    "View Traces": "view_traces",
    "Manage Alerts": "manage_alerts",
    "Manage Observability Dashboards": "manage_observability_dashboards",
    "Talk to Vega": "talk_to_vega",
}

ENV_LABEL_TO_FIELD: dict[str, str] = {
    "Update Targeting": "update_targeting",
    "Review Changes": "review_changes",
    "Apply Changes": "apply_changes",
    "Manage Segments": "manage_segments",
    "Manage Experiments": "manage_experiments",
    "View SDK Key": "view_sdk_key",
    "Update AI Config Targeting": "update_ai_config_targeting",
}


class ConfigImportError(Exception):
    """Raised when an uploaded config cannot be parsed or normalised."""
    pass


# =============================================================================
# NormalizedConfig — the canonical, lossless intermediate
# =============================================================================

@dataclass
class NormalizedConfig:
    """
    A schema-agnostic, lossless view of an uploaded config.

    Attributes:
        customer_name: Customer/organization name
        project_key:   LaunchDarkly project key
        mode:          "Manual" or "Connected" (sidebar mode from the source file)
        teams:         [{"key","name","description"}]
        env_groups:    [{"key","requires_approval","is_critical","notes"}]
        project_permissions: [{"team_key", <UI label>: bool, ...}]  (all 18 labels)
        env_permissions:     [{"team_key","environment_key", <UI label>: bool, ...}]
    """

    customer_name: str
    project_key: str
    mode: str = "Manual"
    teams: list[dict] = field(default_factory=list)
    env_groups: list[dict] = field(default_factory=list)
    project_permissions: list[dict] = field(default_factory=list)
    env_permissions: list[dict] = field(default_factory=list)

    # ------------------------------------------------------------------ helpers
    def name_by_key(self) -> dict[str, str]:
        """Map team key -> display name (matrix rows are keyed by NAME)."""
        return {t["key"]: t["name"] for t in self.teams}

    def to_rbac_config(self) -> RBACConfig:
        """
        Build a canonical RBACConfig (Schema A).

        Lossless as of the Phase 28 unification — the models now carry every project and
        environment permission column, so nothing is dropped. This is what the Save and
        Download paths serialise via RBACConfig.to_dict().
        """
        teams = [
            Team(key=t["key"], name=t["name"], description=t.get("description", ""))
            for t in self.teams
        ]
        env_groups = [
            EnvironmentGroup(
                key=e["key"],
                requires_approval=e.get("requires_approval", False),
                is_critical=e.get("is_critical", False),
                notes=e.get("notes", ""),
            )
            for e in self.env_groups
        ]

        proj_perms = []
        for pp in self.project_permissions:
            kwargs: dict[str, Any] = {"team_key": pp["team_key"]}
            for label, model_field in PROJECT_LABEL_TO_FIELD.items():
                if label in pp:
                    kwargs[model_field] = pp[label]
            proj_perms.append(ProjectPermission(**kwargs))

        env_perms = []
        for ep in self.env_permissions:
            kwargs = {
                "team_key": ep["team_key"],
                "environment_key": ep["environment_key"],
            }
            for label, model_field in ENV_LABEL_TO_FIELD.items():
                if label in ep:
                    kwargs[model_field] = ep[label]
            env_perms.append(EnvironmentPermission(**kwargs))

        return RBACConfig(
            customer_name=self.customer_name,
            project_key=self.project_key,
            mode=self.mode if self.mode in ("Manual", "Connected") else "Manual",
            teams=teams,
            env_groups=env_groups,
            project_permissions=proj_perms,
            env_permissions=env_perms,
        )


# =============================================================================
# Tiny value coercers — tolerate nulls and either casing
# =============================================================================

def _pick(d: dict, *keys: str) -> Any:
    """Return the value of the first key that EXISTS in d (any casing), else None.

    LESSON: `in` checks key presence regardless of the value's truthiness, so a
    stored `False`/`""`/`None` is still picked up (unlike `d.get(a) or d.get(b)`).
    """
    for k in keys:
        if k in d:
            return d[k]
    return None


def _as_bool(value: Any) -> bool:
    """Coerce a permission/flag cell to bool. null -> False."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def _as_str(value: Any) -> str:
    """Coerce to a stripped string. null -> ''."""
    return "" if value is None else str(value).strip()


# =============================================================================
# Schema detection (used for the UI banner; parsing itself is casing-agnostic)
# =============================================================================

def _looks_like_ld_payloads(raw: dict) -> bool:
    """
    True if `raw` is the LD Payloads (deployment) export rather than a config.

    That file is produced by 'Download LD Payloads JSON' and is shaped for deploying to
    LaunchDarkly: resolved `custom_roles` (with `policy`), teams carrying `customRoleKeys`,
    and a `deployment_order`. It is a lossy, one-way artifact — not a resumable config.
    """
    if "custom_roles" in raw or "deployment_order" in raw:
        return True
    # Teams shaped for deployment (customRoleKeys) rather than for the config editor.
    teams = raw.get("teams")
    if isinstance(teams, list) and teams and isinstance(teams[0], dict) \
            and "customRoleKeys" in teams[0]:
        return True
    return False


def detect_schema(raw: dict) -> str:
    """Return SCHEMA_DOWNLOAD ('B') or SCHEMA_STORAGE ('A') for a raw config dict."""
    teams = raw.get("teams") or []
    probe = teams[0] if teams else {}
    if not probe:
        egs = raw.get("env_groups") or []
        probe = egs[0] if egs else {}

    if isinstance(probe, dict):
        if "Key" in probe:
            return SCHEMA_DOWNLOAD
        if "key" in probe:
            return SCHEMA_STORAGE

    pps = raw.get("project_permissions") or []
    if pps and isinstance(pps[0], dict) and "Team" in pps[0]:
        return SCHEMA_DOWNLOAD
    return SCHEMA_STORAGE


# =============================================================================
# Normalisation
# =============================================================================

def normalize_config(raw: dict) -> NormalizedConfig:
    """
    Validate and normalise a raw config dict (Schema A or B) into a NormalizedConfig.

    Raises:
        ConfigImportError: if required fields are missing, teams are empty, or a
                           permission row references a team not present in `teams`.
    """
    if not isinstance(raw, dict):
        raise ConfigImportError("Config must be a JSON object.")

    # Friendly guard: users sometimes grab the wrong export. The LD Payloads
    # (deployment) file has custom_roles / deployment_order and is NOT a config.
    if _looks_like_ld_payloads(raw):
        raise ConfigImportError(
            "This looks like an LD Payloads (deployment) file, not a saved config. "
            "Upload the config JSON from the '💾 Save Configuration' or "
            "'📥 Download JSON' button — not 'Download LD Payloads JSON'."
        )

    required = ["customer_name", "project_key", "teams", "env_groups"]
    missing = [k for k in required if k not in raw]
    if missing:
        raise ConfigImportError(f"Missing required fields: {', '.join(missing)}")

    if not isinstance(raw["teams"], list) or len(raw["teams"]) == 0:
        raise ConfigImportError("Config must have at least one team.")
    if not isinstance(raw["env_groups"], list):
        raise ConfigImportError("env_groups must be a list.")

    teams = _normalize_teams(raw["teams"])
    if not teams:
        raise ConfigImportError("No valid teams found (each team needs a key and a name).")

    env_groups = _normalize_env_groups(raw["env_groups"])

    # Team-name -> key map so Schema-B permission rows ("Team": <name>) can join.
    key_by_name = {t["name"]: t["key"] for t in teams}
    known_keys = {t["key"] for t in teams}

    project_permissions = _normalize_project_permissions(
        raw.get("project_permissions", []), key_by_name, known_keys
    )
    env_permissions = _normalize_env_permissions(
        raw.get("env_permissions", []), key_by_name, known_keys
    )

    return NormalizedConfig(
        customer_name=_as_str(raw.get("customer_name")),
        project_key=_as_str(raw.get("project_key")),
        mode=_as_str(raw.get("mode")) or "Manual",
        teams=teams,
        env_groups=env_groups,
        project_permissions=project_permissions,
        env_permissions=env_permissions,
    )


def normalize_json(text: str) -> NormalizedConfig:
    """Parse a JSON string and normalise it. Raises ConfigImportError on bad JSON."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigImportError(f"Invalid JSON: {exc}") from exc
    return normalize_config(raw)


def _normalize_teams(raw_teams: list) -> list[dict]:
    """Normalise team rows from either schema. Skips blank rows (dynamic editor)."""
    teams: list[dict] = []
    for t in raw_teams:
        if not isinstance(t, dict):
            continue
        key = _as_str(_pick(t, "key", "Key")).lower()
        name = _as_str(_pick(t, "name", "Name"))
        if not key or not name:
            continue  # skip empty trailing rows the data_editor may emit
        teams.append({
            "key": key,
            "name": name,
            "description": _as_str(_pick(t, "description", "Description")),
        })
    return teams


def _normalize_env_groups(raw_envs: list) -> list[dict]:
    """Normalise env-group rows; coalesce null approval/critical -> False."""
    env_groups: list[dict] = []
    for e in raw_envs:
        if not isinstance(e, dict):
            continue
        key = _as_str(_pick(e, "key", "Key")).lower()
        if not key:
            continue
        env_groups.append({
            "key": key,
            "requires_approval": _as_bool(_pick(e, "requires_approval", "Requires Approvals")),
            "is_critical": _as_bool(_pick(e, "is_critical", "Critical")),
            "notes": _as_str(_pick(e, "notes", "Notes")),
        })
    return env_groups


def _resolve_team_key(row: dict, key_by_name: dict[str, str], known_keys: set[str]) -> str:
    """
    Resolve a permission row's team reference to a team KEY.

    Schema A rows carry "team_key" (a key); Schema B rows carry "Team" (a display name).
    Raises ConfigImportError if the reference doesn't match a known team.
    """
    if "team_key" in row:
        tk = _as_str(row["team_key"]).lower()
        if tk in known_keys:
            return tk
        raise ConfigImportError(f"Permission references unknown team key '{tk}'.")

    if "Team" in row:
        name = _as_str(row["Team"])
        tk = key_by_name.get(name)
        if tk:
            return tk
        raise ConfigImportError(f"Permission references unknown team '{name}'.")

    raise ConfigImportError("Permission row is missing a team reference ('Team'/'team_key').")


def _perm_value(row: dict, label: str, label_to_field: dict[str, str]) -> bool:
    """
    Read a permission cell for `label`, trying the UI label (Schema B) first, then the
    snake_case model field (Schema A). Missing/null -> False.
    """
    if label in row:
        return _as_bool(row[label])
    model_field = label_to_field.get(label)
    if model_field and model_field in row:
        return _as_bool(row[model_field])
    return False


def _normalize_project_permissions(
    raw_perms: list, key_by_name: dict[str, str], known_keys: set[str]
) -> list[dict]:
    """Normalise project-permission rows to {team_key, <all 18 labels>: bool}."""
    result: list[dict] = []
    for pp in raw_perms:
        if not isinstance(pp, dict):
            continue
        team_key = _resolve_team_key(pp, key_by_name, known_keys)
        row: dict[str, Any] = {"team_key": team_key}
        for label in PROJECT_PERMISSION_LABELS:
            row[label] = _perm_value(pp, label, PROJECT_LABEL_TO_FIELD)
        result.append(row)
    return result


def _normalize_env_permissions(
    raw_perms: list, key_by_name: dict[str, str], known_keys: set[str]
) -> list[dict]:
    """Normalise env-permission rows to {team_key, environment_key, <all 7 labels>: bool}."""
    result: list[dict] = []
    for ep in raw_perms:
        if not isinstance(ep, dict):
            continue
        team_key = _resolve_team_key(ep, key_by_name, known_keys)
        env_key = _as_str(_pick(ep, "environment_key", "Environment")).lower()
        if not env_key:
            raise ConfigImportError(
                f"Environment permission for team '{team_key}' is missing an environment."
            )
        row: dict[str, Any] = {"team_key": team_key, "environment_key": env_key}
        for label in ENV_PERMISSION_LABELS:
            row[label] = _perm_value(ep, label, ENV_LABEL_TO_FIELD)
        result.append(row)
    return result


# =============================================================================
# DataFrame builders — reproduce the exact session_state shapes the UI expects
# =============================================================================
# LESSON: These are PURE functions (no Streamlit) so they can be unit-tested.
# ui/setup_tab.py just assigns their output into st.session_state.

def build_teams_dataframe(cfg: NormalizedConfig) -> pd.DataFrame:
    """Setup tab `teams` editor shape: columns Key / Name / Description."""
    return pd.DataFrame({
        "Key": [t["key"] for t in cfg.teams],
        "Name": [t["name"] for t in cfg.teams],
        "Description": [t.get("description", "") for t in cfg.teams],
    })


def build_env_groups_dataframe(cfg: NormalizedConfig) -> pd.DataFrame:
    """Setup tab `env_groups` editor shape: Key / Requires Approvals / Critical / Notes."""
    return pd.DataFrame({
        "Key": [e["key"] for e in cfg.env_groups],
        "Requires Approvals": [e.get("requires_approval", False) for e in cfg.env_groups],
        "Critical": [e.get("is_critical", False) for e in cfg.env_groups],
        "Notes": [e.get("notes", "") for e in cfg.env_groups],
    })


def build_project_matrix(cfg: NormalizedConfig) -> pd.DataFrame:
    """
    Matrix-tab `project_matrix` shape: a "Team" column (by NAME) + all 18 labels.

    Teams with no permission row default to all-False except "View Project"=True,
    matching create_default_project_matrix().
    """
    name_by_key = cfg.name_by_key()
    perms_by_key = {pp["team_key"]: pp for pp in cfg.project_permissions}

    data: dict[str, list] = {"Team": [t["name"] for t in cfg.teams]}
    for label in PROJECT_PERMISSION_LABELS:
        column = []
        for t in cfg.teams:
            pp = perms_by_key.get(t["key"])
            if pp is not None:
                column.append(bool(pp.get(label, False)))
            else:
                column.append(label == "View Project")
        data[label] = column
    return pd.DataFrame(data)


def build_env_matrix(cfg: NormalizedConfig) -> pd.DataFrame:
    """
    Matrix-tab `env_matrix` shape: one row per team × env group.

    Columns: Team (by NAME), Environment (env key), + all 7 env labels.
    """
    perms_by_pair = {
        (ep["team_key"], ep["environment_key"]): ep for ep in cfg.env_permissions
    }

    rows: list[dict] = []
    for t in cfg.teams:
        for e in cfg.env_groups:
            row: dict[str, Any] = {"Team": t["name"], "Environment": e["key"]}
            ep = perms_by_pair.get((t["key"], e["key"]))
            for label in ENV_PERMISSION_LABELS:
                row[label] = bool(ep.get(label, False)) if ep is not None else False
            rows.append(row)
    return pd.DataFrame(rows)
