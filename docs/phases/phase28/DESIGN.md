# Phase 28: Design Document — Config Upload & Resume

| Field | Value |
|-------|-------|
| **Phase** | 28 |
| **Status** | 📋 Design Complete — Ready for Implementation |
| **Goal** | Upload a saved JSON config and restore the full session (teams, envs, matrices) |
| **Dependencies** | Phase 2 (Storage Service / RBACConfig model), Phase 1 (Data Models) |

## Related Documents

| Document | Link |
|----------|------|
| Phase README | [README.md](./README.md) |
| Python Concepts | [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) |
| RBACConfig model | `models/config.py` |
| Storage Service | `services/storage.py` |
| Existing save/download | `ui/deploy_tab.py` lines 264-292 |

---

## High-Level Design (HLD)

### What Are We Building and Why?

SAs design RBAC configs across multiple sessions. Today they can download a JSON config
but can't upload it back to resume. On Streamlit Cloud, server storage is ephemeral —
configs are lost on restart. Upload/resume is the missing piece.

### Where It Goes

The uploader lives at the **top of the Setup tab** (Tab 1), before the existing
customer info and team editors. This is the natural entry point — "resume previous
work OR start fresh."

### Architecture

```
SA has a saved config JSON file (from previous session's Download)
        │
        ▼
Setup Tab (Tab 1) — top section
  st.file_uploader("Upload config", type=["json"])
        │
        ▼
_parse_uploaded_config(uploaded_file)
  → json.load(file)
  → Validate: has required keys (customer_name, project_key, teams, etc.)
  → Return parsed dict
        │
        ▼
_restore_config_to_session(config_dict)
  → session_state.teams = DataFrame from config["teams"]
  → session_state.env_groups = DataFrame from config["env_groups"]
  → session_state.project = config["project_key"]
  → session_state._advisor_customer_name = config["customer_name"]
  → session_state.project_matrix = build from config["project_permissions"]
  → session_state.env_matrix = build from config["env_permissions"]
  → session_state._matrix_version += 1  (fresh widget keys)
  → Clear data_editor widget keys
        │
        ▼
st.rerun() → all tabs reflect the restored data
```

### Data Flow: Save → Download → Upload → Restore

```
Session 1 (design phase):
  Setup tab → teams, envs configured
  Matrix tab → permissions checked
  Deploy tab → "Download JSON" → saves to user's computer
  File: voya_rbac_config.json

Session 2 (resume):
  Setup tab → "Upload config" → selects voya_rbac_config.json
  → _parse_uploaded_config() validates JSON
  → _restore_config_to_session() populates session_state
  → st.rerun()
  → Setup tab shows Voya teams/envs
  → Matrix tab shows Voya permissions (all checkboxes restored)
  → Ready to continue or deploy
```

---

## Detailed Low-Level Design (DLD)

### 1. JSON Config Format (existing)

The downloaded JSON follows the `RBACConfig.to_dict()` format:

```json
{
  "version": "1.0",
  "customer_name": "Voya",
  "project_key": "voya-web",
  "mode": "Manual",
  "created_at": "2026-03-24T10:30:00",
  "updated_at": "2026-03-24T14:15:00",
  "teams": [
    {"key": "dev", "name": "Developer", "description": "Development team"},
    {"key": "qa", "name": "QA Engineer", "description": "Quality assurance"}
  ],
  "env_groups": [
    {"key": "test", "requires_approval": false, "is_critical": false, "notes": ""},
    {"key": "production", "requires_approval": true, "is_critical": true, "notes": ""}
  ],
  "project_permissions": [
    {"team_key": "dev", "create_flags": true, "update_flags": true, ...},
    {"team_key": "qa", "create_flags": false, ...}
  ],
  "env_permissions": [
    {"team_key": "dev", "environment_key": "test", "update_targeting": true, ...},
    {"team_key": "dev", "environment_key": "production", "update_targeting": false, ...}
  ]
}
```

### 2. File Uploader Section

```python
def _render_upload_section() -> None:
    """Render the config upload section at the top of Setup tab."""
    with st.expander("📂 Resume Previous Work", expanded=False):
        st.markdown("Upload a previously saved config to resume where you left off.")

        uploaded_file = st.file_uploader(
            "Upload config JSON",
            type=["json"],
            key="config_uploader",
            help="Select a *_rbac_config.json file downloaded from a previous session",
        )

        if uploaded_file is not None:
            try:
                config_dict = _parse_uploaded_config(uploaded_file)
                if st.button("📥 Restore This Config", type="primary"):
                    _restore_config_to_session(config_dict)
                    st.rerun()
            except ConfigUploadError as e:
                st.error(f"Invalid config file: {e}")
```

### 3. Parse & Validate

```python
class ConfigUploadError(Exception):
    """Raised when uploaded config is invalid."""
    pass

def _parse_uploaded_config(uploaded_file) -> dict:
    """
    Parse and validate an uploaded JSON config file.

    Validates:
    - Valid JSON syntax
    - Required keys present (customer_name, project_key, teams, env_groups)
    - teams is a list with at least one entry
    - Each team has "key" and "name" fields

    Returns:
        Parsed config dict

    Raises:
        ConfigUploadError if validation fails
    """
    try:
        config = json.load(uploaded_file)
    except json.JSONDecodeError as e:
        raise ConfigUploadError(f"Invalid JSON: {e}")

    # Required keys
    required = ["customer_name", "project_key", "teams", "env_groups"]
    missing = [k for k in required if k not in config]
    if missing:
        raise ConfigUploadError(f"Missing required fields: {', '.join(missing)}")

    # Teams validation
    if not isinstance(config["teams"], list) or len(config["teams"]) == 0:
        raise ConfigUploadError("Config must have at least one team")

    for team in config["teams"]:
        if "key" not in team or "name" not in team:
            raise ConfigUploadError(f"Team missing 'key' or 'name': {team}")

    # Env groups validation
    if not isinstance(config["env_groups"], list):
        raise ConfigUploadError("env_groups must be a list")

    # Show preview before restoring
    st.info(
        f"**{config['customer_name']}** — project `{config['project_key']}` | "
        f"{len(config['teams'])} teams, {len(config['env_groups'])} environments"
    )

    return config
```

### 4. Restore to Session State

```python
def _restore_config_to_session(config: dict) -> None:
    """
    Populate session_state from a parsed config dict.

    Restores:
    - Customer name (sidebar)
    - Project key
    - Teams DataFrame
    - Environment Groups DataFrame
    - Project permissions matrix
    - Environment permissions matrix
    - Generation mode
    """
    import pandas as pd
    from core.ld_actions import get_all_project_permissions, get_all_env_permissions

    # --- Customer name + project key ---
    st.session_state["_advisor_customer_name"] = config["customer_name"]
    st.session_state["project"] = config["project_key"]
    st.session_state["generation_mode"] = config.get("mode", "role_attributes")

    # --- Teams ---
    teams = config["teams"]
    st.session_state.teams = pd.DataFrame({
        "Key": [t["key"] for t in teams],
        "Name": [t["name"] for t in teams],
        "Description": [t.get("description", "") for t in teams],
    })

    # --- Environment Groups ---
    envs = config["env_groups"]
    st.session_state.env_groups = pd.DataFrame({
        "Key": [e["key"] for e in envs],
        "Requires Approvals": [e.get("requires_approval", False) for e in envs],
        "Critical": [e.get("is_critical", False) for e in envs],
        "Notes": [e.get("notes", "") for e in envs],
    })

    # --- Project permissions matrix ---
    team_names = [t["name"] for t in teams]
    all_proj_perms = get_all_project_permissions()

    # Build a lookup: team_key → permission values
    proj_perm_lookup = {}
    for pp in config.get("project_permissions", []):
        proj_perm_lookup[pp["team_key"]] = pp

    # Map UI permission names to config JSON keys
    PROJ_PERM_KEY_MAP = {
        "Create Flags": "create_flags",
        "Update Flags": "update_flags",
        "Archive Flags": "archive_flags",
        "Update Client Side Availability": "update_client_side_availability",
        "Manage Metrics": "manage_metrics",
        "Manage Release Pipelines": "manage_release_pipelines",
        "View Project": "view_project",
        # Add more as needed
    }

    project_data = {"Team": team_names}
    for perm in all_proj_perms:
        json_key = PROJ_PERM_KEY_MAP.get(perm)
        project_data[perm] = [
            proj_perm_lookup.get(t["key"], {}).get(json_key, False)
            if json_key else False
            for t in teams
        ]
    st.session_state.project_matrix = pd.DataFrame(project_data)

    # --- Environment permissions matrix ---
    env_keys = [e["key"] for e in envs]
    all_env_perms = get_all_env_permissions()

    ENV_PERM_KEY_MAP = {
        "Update Targeting": "update_targeting",
        "Review Changes": "review_changes",
        "Apply Changes": "apply_changes",
        "Manage Segments": "manage_segments",
        "Manage Experiments": "manage_experiments",
        "Update AI Config Targeting": "update_ai_config_targeting",
        "View SDK Key": "view_sdk_key",
    }

    env_perm_lookup = {}
    for ep in config.get("env_permissions", []):
        key = (ep["team_key"], ep["environment_key"])
        env_perm_lookup[key] = ep

    env_rows = []
    for t in teams:
        for env_key in env_keys:
            row = {"Team": t["name"], "Environment": env_key}
            ep = env_perm_lookup.get((t["key"], env_key), {})
            for perm in all_env_perms:
                json_key = ENV_PERM_KEY_MAP.get(perm)
                row[perm] = ep.get(json_key, False) if json_key else False
            env_rows.append(row)
    st.session_state.env_matrix = pd.DataFrame(env_rows)

    # --- Fresh widget keys ---
    st.session_state["_matrix_version"] = st.session_state.get("_matrix_version", 0) + 1
    st.session_state["_advisor_applied"] = True  # matrix tab trusts this data

    # Clear stale widget keys
    stale = [k for k in list(st.session_state.keys()) if isinstance(k, str) and (
        k.startswith("proj_") or k.startswith("env_") or
        k.startswith("teams_editor") or k.startswith("env_groups_editor")
    )]
    for k in stale:
        del st.session_state[k]
```

### 5. Integration in Setup Tab

```python
def render_setup_tab(customer_name: str = "", mode: str = "Manual") -> None:
    _initialize_session_state()
    st.header("Step 1: Setup")

    # Upload section — FIRST, before anything else
    _render_upload_section()

    st.divider()

    # Existing setup UI...
    _render_customer_info(customer_name, mode)
    ...
```

---

## Pseudo Logic

### 1. Upload Flow

```
FUNCTION _render_upload_section():

  WITH st.expander("📂 Resume Previous Work"):
    DISPLAY "Upload a previously saved config..."

    uploaded_file = st.file_uploader(type=["json"])

    IF uploaded_file is not None:
      TRY:
        config_dict = _parse_uploaded_config(uploaded_file)
        DISPLAY preview: customer name, project, team count, env count
        IF st.button("Restore This Config"):
          _restore_config_to_session(config_dict)
          st.rerun()
      CATCH ConfigUploadError:
        DISPLAY error message
```

### 2. Parse & Validate

```
FUNCTION _parse_uploaded_config(file) -> dict:

  TRY:
    config = json.load(file)
  CATCH JSONDecodeError:
    RAISE "Invalid JSON"

  IF missing required keys (customer_name, project_key, teams, env_groups):
    RAISE "Missing required fields: ..."

  IF teams is empty:
    RAISE "Must have at least one team"

  FOR each team:
    IF missing "key" or "name":
      RAISE "Team missing key or name"

  DISPLAY preview info
  RETURN config
```

### 3. Restore to Session

```
FUNCTION _restore_config_to_session(config):

  # Customer + project
  session_state._advisor_customer_name = config.customer_name
  session_state.project = config.project_key

  # Teams DataFrame
  session_state.teams = DataFrame from config.teams

  # Env Groups DataFrame
  session_state.env_groups = DataFrame from config.env_groups

  # Project matrix
  FOR each team:
    FOR each project permission:
      look up value from config.project_permissions by team_key
  session_state.project_matrix = DataFrame

  # Env matrix
  FOR each team:
    FOR each env:
      FOR each env permission:
        look up value from config.env_permissions by (team_key, env_key)
  session_state.env_matrix = DataFrame

  # Fresh widget keys (same pattern as Sage Apply)
  _matrix_version += 1
  _advisor_applied = True
  Clear stale widget keys
```

---

## Test Cases

**Test file:** `tests/test_config_upload.py`

### Group 1: Parse & Validate

#### TC-UP-01: Valid config parses successfully
```
GIVEN: A valid JSON config with customer_name, project_key, teams, env_groups
WHEN:  _parse_uploaded_config(file) is called
THEN:  Returns a dict with all fields
       No exception raised
```

#### TC-UP-02: Invalid JSON raises error
```
GIVEN: A file containing "not valid json {"
WHEN:  _parse_uploaded_config(file) is called
THEN:  Raises ConfigUploadError("Invalid JSON...")
```

#### TC-UP-03: Missing required keys raises error
```
GIVEN: JSON with {"customer_name": "Acme"} (missing project_key, teams, env_groups)
WHEN:  _parse_uploaded_config(file) is called
THEN:  Raises ConfigUploadError("Missing required fields: project_key, teams, env_groups")
```

#### TC-UP-04: Empty teams list raises error
```
GIVEN: JSON with "teams": []
WHEN:  _parse_uploaded_config(file) is called
THEN:  Raises ConfigUploadError("Config must have at least one team")
```

#### TC-UP-05: Team missing name raises error
```
GIVEN: JSON with teams: [{"key": "dev"}] (no "name")
WHEN:  _parse_uploaded_config(file) is called
THEN:  Raises ConfigUploadError("Team missing 'key' or 'name'")
```

### Group 2: Session Restore

#### TC-UP-06: Customer name and project restored
```
GIVEN: Config with customer_name="Voya", project_key="voya-web"
WHEN:  _restore_config_to_session(config) is called
THEN:  session_state._advisor_customer_name == "Voya"
       session_state.project == "voya-web"
```

#### TC-UP-07: Teams DataFrame restored
```
GIVEN: Config with 3 teams (dev, qa, admin)
WHEN:  _restore_config_to_session(config) is called
THEN:  session_state.teams is a DataFrame with 3 rows
       columns: Key, Name, Description
       teams["Name"].tolist() == ["Developer", "QA Engineer", "Administrator"]
```

#### TC-UP-08: Env Groups DataFrame restored
```
GIVEN: Config with 2 env_groups (test, production)
WHEN:  _restore_config_to_session(config) is called
THEN:  session_state.env_groups is a DataFrame with 2 rows
       columns: Key, Requires Approvals, Critical, Notes
       production row has Critical=True
```

#### TC-UP-09: Project matrix restored with correct values
```
GIVEN: Config with project_permissions where dev has create_flags=True
WHEN:  _restore_config_to_session(config) is called
THEN:  session_state.project_matrix has "Create Flags" column
       Developer row Create Flags == True
       QA row Create Flags == False (if not in config)
```

#### TC-UP-10: Env matrix restored with correct values
```
GIVEN: Config with env_permissions where dev/test has update_targeting=True
WHEN:  _restore_config_to_session(config) is called
THEN:  session_state.env_matrix has Developer/test row
       Developer/test/Update Targeting == True
       Developer/production/Update Targeting == False
```

#### TC-UP-11: Widget keys bumped after restore
```
GIVEN: _matrix_version was 5 before restore
WHEN:  _restore_config_to_session(config) is called
THEN:  _matrix_version == 6
       _advisor_applied == True
       No stale proj_*/env_*/editor keys in session_state
```

### Group 3: Edge Cases

#### TC-UP-12: Config with empty project_permissions works
```
GIVEN: Config with project_permissions: [] (no permissions configured yet)
WHEN:  _restore_config_to_session(config) is called
THEN:  project_matrix has all False values (default)
       No exception raised
```

#### TC-UP-13: Config with empty env_permissions works
```
GIVEN: Config with env_permissions: []
WHEN:  _restore_config_to_session(config) is called
THEN:  env_matrix has all False values (default)
       No exception raised
```

#### TC-UP-14: Config from standard-4-env template restores correctly
```
GIVEN: The actual standard-4-env.json template file
WHEN:  Uploaded and restored
THEN:  4 teams (dev, qa, po, release-manager)
       4 environments (development, test, staging, production)
       All permission values match the template
```

---

## Implementation Plan

| Step | Task | File |
|------|------|------|
| 1 | Create `ConfigUploadError` exception | `ui/setup_tab.py` |
| 2 | Implement `_parse_uploaded_config()` | `ui/setup_tab.py` |
| 3 | Implement `_restore_config_to_session()` | `ui/setup_tab.py` |
| 4 | Implement `_render_upload_section()` | `ui/setup_tab.py` |
| 5 | Add `_render_upload_section()` call in `render_setup_tab()` | `ui/setup_tab.py` |
| 6 | Write all 14 tests | `tests/test_config_upload.py` |
| 7 | Run full test suite | `pytest tests/ -v` |
| 8 | Manual test: download → refresh → upload → verify | — |

### Python Concepts in This Phase

| Concept | Used for |
|---------|---------|
| `st.file_uploader` | File upload widget |
| `json.load(file)` | Parse uploaded file (file-like object, not string) |
| Permission key mapping | Map UI names ("Create Flags") to JSON keys ("create_flags") |
| Widget key versioning (reused) | Same pattern as Phase 27 — bump version for fresh checkboxes |
| Two-pass restore | First restore DataFrames, then build matrices from permissions |

---

## Navigation

- [← README](./README.md)
- [Python Concepts →](./PYTHON_CONCEPTS.md)
