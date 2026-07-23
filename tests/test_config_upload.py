"""
Tests for Phase 28: Config Upload & Resume (config_importer service)
====================================================================

Covers the importer that normalises BOTH on-disk config schemas:
    Schema A ("storage")  — snake_case, team_key references
    Schema B ("download") — Title-Case, team-by-name references (the iSeatz file)

Run with: pytest tests/test_config_upload.py -v
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from services.config_importer import (
    NormalizedConfig,
    ConfigImportError,
    normalize_config,
    normalize_json,
    detect_schema,
    build_teams_dataframe,
    build_env_groups_dataframe,
    build_project_matrix,
    build_env_matrix,
    SCHEMA_STORAGE,
    SCHEMA_DOWNLOAD,
    PROJECT_PERMISSION_LABELS,
    ENV_PERMISSION_LABELS,
)
from models import RBACConfig


# =============================================================================
# Fixtures
# =============================================================================

ISEATZ_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "configs" / "customers" / "iseatz" / "2026.05.12iseatz_rbac_config.json"
)


@pytest.fixture
def iseatz_raw() -> dict:
    """The real downloaded iSeatz config (Schema B)."""
    with open(ISEATZ_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def storage_raw() -> dict:
    """A minimal Schema-A (snake_case / storage) config."""
    return {
        "customer_name": "Voya",
        "project_key": "voya-web",
        "mode": "Manual",
        "teams": [
            {"key": "dev", "name": "Developer", "description": "Dev team"},
            {"key": "qa", "name": "QA Engineer", "description": ""},
        ],
        "env_groups": [
            {"key": "test", "requires_approval": False, "is_critical": False, "notes": ""},
            {"key": "production", "requires_approval": True, "is_critical": True, "notes": ""},
        ],
        "project_permissions": [
            {"team_key": "dev", "create_flags": True, "update_flags": True, "view_project": True},
        ],
        "env_permissions": [
            {"team_key": "dev", "environment_key": "test", "update_targeting": True},
            {"team_key": "dev", "environment_key": "production", "update_targeting": False},
        ],
    }


# =============================================================================
# Group 1: Parse & Validate
# =============================================================================

def test_missing_required_keys_raises():
    """TC-UP-03: missing project_key/teams/env_groups is rejected."""
    with pytest.raises(ConfigImportError) as exc:
        normalize_config({"customer_name": "Acme"})
    assert "Missing required fields" in str(exc.value)


def test_empty_teams_raises():
    """TC-UP-04: teams: [] is rejected."""
    with pytest.raises(ConfigImportError):
        normalize_config({
            "customer_name": "Acme", "project_key": "p",
            "teams": [], "env_groups": [],
        })


def test_invalid_json_raises():
    """TC-UP-02: bad JSON via normalize_json."""
    with pytest.raises(ConfigImportError) as exc:
        normalize_json("not valid json {")
    assert "Invalid JSON" in str(exc.value)


def test_ld_payloads_file_gives_helpful_error():
    """Uploading the LD Payloads (deployment) export by mistake is caught with guidance."""
    payloads = {
        "metadata": {"customer_name": "iSeatz", "project_key": "amex", "version": "1.0"},
        "custom_roles": [{"key": "create-flags", "name": "Create Flags", "policy": []}],
        "teams": [{"key": "amex-dev", "name": "Amex: Developer", "customRoleKeys": ["update-flags"]}],
        "deployment_order": ["1. Create custom roles first"],
    }
    with pytest.raises(ConfigImportError) as exc:
        normalize_config(payloads)
    assert "LD Payloads" in str(exc.value)


def test_blank_team_rows_are_skipped():
    """Dynamic-editor blank trailing rows (no key/name) are dropped."""
    cfg = normalize_config({
        "customer_name": "Acme", "project_key": "p",
        "teams": [
            {"Key": "dev", "Name": "Developer", "Description": None},
            {"Key": "", "Name": "", "Description": None},  # blank row
        ],
        "env_groups": [],
    })
    assert len(cfg.teams) == 1


# =============================================================================
# Group 2: Schema detection
# =============================================================================

def test_detect_schema_download(iseatz_raw):
    """TC-UP-15: Title-Case teams -> Schema B."""
    assert detect_schema(iseatz_raw) == SCHEMA_DOWNLOAD


def test_detect_schema_storage(storage_raw):
    """TC-UP-15: snake_case teams -> Schema A."""
    assert detect_schema(storage_raw) == SCHEMA_STORAGE


# =============================================================================
# Group 3: Normalisation — Schema B (iSeatz)
# =============================================================================

def test_iseatz_normalizes_with_correct_counts(iseatz_raw):
    """TC-UP-16: iSeatz Schema-B file normalises to the expected object counts."""
    cfg = normalize_config(iseatz_raw)
    assert cfg.customer_name == "iSeatz"
    assert cfg.project_key == "amex"
    assert len(cfg.teams) == 6
    assert len(cfg.env_groups) == 10
    assert len(cfg.project_permissions) == 6
    assert len(cfg.env_permissions) == 60


def test_team_name_resolved_to_key(iseatz_raw):
    """TC-UP-17: project_permissions "Team": "Developer" resolves to key "dev"."""
    cfg = normalize_config(iseatz_raw)
    team_keys = {pp["team_key"] for pp in cfg.project_permissions}
    assert team_keys == {"dev", "qa", "pm", "admin", "pd", "devlead"}


def test_null_env_flags_coalesce_to_false(iseatz_raw):
    """TC-UP-18: env groups with null 'Requires Approvals'/'Critical' become False."""
    cfg = normalize_config(iseatz_raw)
    by_key = {e["key"]: e for e in cfg.env_groups}
    for k in ("qa", "int", "pt"):
        assert by_key[k]["requires_approval"] is False
        assert by_key[k]["is_critical"] is False


def test_null_description_coalesces_to_empty(iseatz_raw):
    """Teams with null Description normalise to ''."""
    cfg = normalize_config(iseatz_raw)
    by_key = {t["key"]: t for t in cfg.teams}
    assert by_key["pd"]["description"] == ""
    assert by_key["devlead"]["description"] == ""


def test_observability_columns_preserved(iseatz_raw):
    """Data-loss guard: observability columns survive normalisation (not on the model)."""
    cfg = normalize_config(iseatz_raw)
    admin = next(pp for pp in cfg.project_permissions if pp["team_key"] == "admin")
    assert admin["Talk to Vega"] is True
    assert admin["Manage Alerts"] is True
    assert admin["View Sessions"] is True
    # A non-admin team should have them False
    dev = next(pp for pp in cfg.project_permissions if pp["team_key"] == "dev")
    assert dev["Talk to Vega"] is False


def test_unknown_team_reference_raises():
    """A permission row naming a team not in `teams` fails safely."""
    with pytest.raises(ConfigImportError) as exc:
        normalize_config({
            "customer_name": "Acme", "project_key": "p",
            "teams": [{"Key": "dev", "Name": "Developer", "Description": ""}],
            "env_groups": [],
            "project_permissions": [{"Team": "Ghost Team", "Create Flags": True}],
        })
    assert "unknown team" in str(exc.value).lower()


# =============================================================================
# Group 4: Normalisation — Schema A (storage)
# =============================================================================

def test_storage_schema_normalizes(storage_raw):
    """Schema-A snake_case config normalises and maps fields to UI labels."""
    cfg = normalize_config(storage_raw)
    assert cfg.customer_name == "Voya"
    assert len(cfg.teams) == 2
    dev_pp = next(pp for pp in cfg.project_permissions if pp["team_key"] == "dev")
    assert dev_pp["Create Flags"] is True
    assert dev_pp["Update Flags"] is True
    assert dev_pp["Archive Flags"] is False  # not in source -> default False


def test_storage_env_permissions_map(storage_raw):
    """Schema-A env perms map snake fields to UI labels."""
    cfg = normalize_config(storage_raw)
    test_row = next(
        ep for ep in cfg.env_permissions
        if ep["team_key"] == "dev" and ep["environment_key"] == "test"
    )
    assert test_row["Update Targeting"] is True
    prod_row = next(
        ep for ep in cfg.env_permissions
        if ep["team_key"] == "dev" and ep["environment_key"] == "production"
    )
    assert prod_row["Update Targeting"] is False


# =============================================================================
# Group 5: to_rbac_config()
# =============================================================================

def test_to_rbac_config_from_iseatz(iseatz_raw):
    """TC-UP-16: canonical RBACConfig is buildable (model-backed subset)."""
    cfg = normalize_config(iseatz_raw)
    rbac = cfg.to_rbac_config()
    assert isinstance(rbac, RBACConfig)
    assert rbac.customer_name == "iSeatz"
    assert rbac.project_key == "amex"
    assert len(rbac.teams) == 6
    assert len(rbac.env_groups) == 10
    assert len(rbac.project_permissions) == 6
    assert len(rbac.env_permissions) == 60
    dev_perm = rbac.get_project_permission("dev")
    assert dev_perm is not None
    assert dev_perm.update_flags is True
    assert dev_perm.create_flags is False


# =============================================================================
# Group 6: DataFrame builders (restore shapes)
# =============================================================================

def test_build_teams_dataframe(iseatz_raw):
    """TC-UP-07: teams DataFrame shape."""
    cfg = normalize_config(iseatz_raw)
    df = build_teams_dataframe(cfg)
    assert list(df.columns) == ["Key", "Name", "Description"]
    assert len(df) == 6
    assert df["Name"].tolist()[0] == "Developer"


def test_build_env_groups_dataframe(iseatz_raw):
    """TC-UP-08: env groups DataFrame shape + null coalescing."""
    cfg = normalize_config(iseatz_raw)
    df = build_env_groups_dataframe(cfg)
    assert list(df.columns) == ["Key", "Requires Approvals", "Critical", "Notes"]
    assert len(df) == 10
    prod = df[df["Key"] == "production"].iloc[0]
    assert bool(prod["Critical"]) is True


def test_build_project_matrix_full_columns(iseatz_raw):
    """TC-UP-09 + data-loss guard: project matrix has ALL 18 labels with correct values."""
    cfg = normalize_config(iseatz_raw)
    df = build_project_matrix(cfg)
    assert df.columns[0] == "Team"
    for label in PROJECT_PERMISSION_LABELS:
        assert label in df.columns
    admin = df[df["Team"] == "Administrator"].iloc[0]
    assert bool(admin["Talk to Vega"]) is True
    assert bool(admin["Create Flags"]) is True
    dev = df[df["Team"] == "Developer"].iloc[0]
    assert bool(dev["Create Flags"]) is False
    assert bool(dev["Update Flags"]) is True


def test_build_env_matrix_rows_and_values(iseatz_raw):
    """TC-UP-10 + TC-UP-19: env matrix has team×env rows with correct values."""
    cfg = normalize_config(iseatz_raw)
    df = build_env_matrix(cfg)
    assert len(df) == 60  # 6 teams × 10 envs
    for label in ENV_PERMISSION_LABELS:
        assert label in df.columns

    def cell(team, env, label):
        row = df[(df["Team"] == team) & (df["Environment"] == env)].iloc[0]
        return bool(row[label])

    assert cell("Administrator", "production", "Update Targeting") is True
    assert cell("Developer", "production", "Update Targeting") is False
    assert cell("Developer", "test", "Update Targeting") is True


def test_env_matrix_all_bool_dtype(iseatz_raw):
    """Permission columns should be bool dtype (Summary tab relies on this)."""
    cfg = normalize_config(iseatz_raw)
    df = build_project_matrix(cfg)
    bool_cols = df.select_dtypes(include=["bool"]).columns
    # All 18 permission columns should be bool (Team is object)
    assert len(bool_cols) == len(PROJECT_PERMISSION_LABELS)


# =============================================================================
# Group 7: Round-trip (download schema -> normalize -> matches source intent)
# =============================================================================

def test_round_trip_preserves_permission_counts(iseatz_raw):
    """Every enabled cell in the source survives into the rebuilt matrices."""
    cfg = normalize_config(iseatz_raw)
    proj_df = build_project_matrix(cfg)

    # Count True cells in source project_permissions (excluding the "Team" field)
    source_true = 0
    for pp in iseatz_raw["project_permissions"]:
        source_true += sum(1 for k, v in pp.items() if k != "Team" and v is True)

    rebuilt_true = int(
        proj_df.drop(columns=["Team"]).sum().sum()
    )
    assert rebuilt_true == source_true


# =============================================================================
# Group 8: Schema-A unification (Phase 28)
# =============================================================================

def test_project_permission_model_carries_observability():
    """The ProjectPermission model now holds observability + AI-variation columns."""
    from models import ProjectPermission

    pp = ProjectPermission(
        team_key="admin",
        talk_to_vega=True,
        view_sessions=True,
        manage_alerts=True,
        manage_ai_variations=True,
    )
    d = pp.to_dict()
    assert d["talk_to_vega"] is True
    assert d["view_sessions"] is True
    assert d["manage_ai_variations"] is True
    # Round-trips through from_dict
    assert ProjectPermission.from_dict(d).talk_to_vega is True
    # Shows up in the enabled list
    assert "talk_to_vega" in pp.get_enabled_permissions()


def test_to_rbac_config_now_preserves_observability(iseatz_raw):
    """to_rbac_config() is lossless: observability columns reach the model."""
    rbac = normalize_config(iseatz_raw).to_rbac_config()
    admin = rbac.get_project_permission("admin")
    assert admin.talk_to_vega is True
    assert admin.manage_alerts is True
    assert admin.view_sessions is True
    dev = rbac.get_project_permission("dev")
    assert dev.talk_to_vega is False


def test_download_emits_schema_a(iseatz_raw):
    """The download format (RBACConfig.to_dict) is Schema A, not Schema B."""
    schema_a = normalize_config(iseatz_raw).to_rbac_config().to_dict()
    assert detect_schema(schema_a) == SCHEMA_STORAGE
    # snake_case + team-by-key markers
    assert "key" in schema_a["teams"][0]
    assert "team_key" in schema_a["project_permissions"][0]


def test_critical_env_auto_sets_requires_approval_on_download(iseatz_raw):
    """
    Affirmed business rule: a Critical environment auto-sets Requires Approval = True.

    iSeatz's 'stage' env is Critical=true with Requires Approvals=null (False) on screen.
    Once Download routes through the model, the canonical Schema A output must show
    requires_approval=True for it — and leave a non-critical env (qa) untouched.
    """
    schema_a = normalize_config(iseatz_raw).to_rbac_config().to_dict()
    by_key = {e["key"]: e for e in schema_a["env_groups"]}
    assert by_key["stage"]["is_critical"] is True
    assert by_key["stage"]["requires_approval"] is True   # auto-set
    assert by_key["qa"]["is_critical"] is False
    assert by_key["qa"]["requires_approval"] is False      # unchanged


def test_download_schema_a_reimports_losslessly(iseatz_raw):
    """
    Round-trip: iSeatz (Schema B) -> normalize -> Schema A (new download) -> normalize.
    The rebuilt permission matrices must be identical, proving no data is lost when the
    download switches to Schema A.
    """
    cfg_b = normalize_config(iseatz_raw)
    schema_a = cfg_b.to_rbac_config().to_dict()
    cfg_a = normalize_config(schema_a)

    pd.testing.assert_frame_equal(
        build_project_matrix(cfg_b).sort_index(axis=1).reset_index(drop=True),
        build_project_matrix(cfg_a).sort_index(axis=1).reset_index(drop=True),
    )
    pd.testing.assert_frame_equal(
        build_env_matrix(cfg_b).sort_index(axis=1).reset_index(drop=True),
        build_env_matrix(cfg_a).sort_index(axis=1).reset_index(drop=True),
    )
