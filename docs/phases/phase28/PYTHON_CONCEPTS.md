# Phase 28: Python Concepts

Concepts introduced when building config upload and session restoration.

---

## Table of Contents

1. [`st.file_uploader` — Accepting File Uploads](#1-stfile_uploader--accepting-file-uploads)
2. [`json.load` vs `json.loads` — File vs String](#2-jsonload-vs-jsonloads--file-vs-string)
3. [Permission Key Mapping — UI Names vs JSON Keys](#3-permission-key-mapping--ui-names-vs-json-keys)
4. [Session State Hydration — Rebuilding State from Data](#4-session-state-hydration--rebuilding-state-from-data)
5. [Quick Reference Card](#quick-reference-card)

---

## 1. `st.file_uploader` — Accepting File Uploads

### The concept

`st.file_uploader` creates a file picker widget. When the user selects a file,
it returns an `UploadedFile` object (file-like). When no file is selected, it returns `None`.

```python
uploaded = st.file_uploader("Upload config", type=["json"])

if uploaded is not None:
    # uploaded is a file-like object — has .read(), .name, .size
    content = uploaded.read()       # bytes
    text = uploaded.getvalue().decode("utf-8")  # string
    data = json.load(uploaded)      # parse directly as JSON
```

### Key behaviors

```python
# type parameter restricts accepted file extensions
uploaded = st.file_uploader("Upload", type=["json"])      # only .json
uploaded = st.file_uploader("Upload", type=["json", "csv"])  # .json or .csv

# key parameter prevents widget ID conflicts
uploaded = st.file_uploader("Upload", key="config_uploader")

# After reading, the file pointer is at the end. Reset for re-reading:
uploaded.seek(0)
data1 = json.load(uploaded)
uploaded.seek(0)   # reset
data2 = json.load(uploaded)  # can read again
```

### GOTCHA: File uploader resets on rerun

```python
# BAD — file disappears after st.rerun()
uploaded = st.file_uploader("Upload", type=["json"])
if uploaded:
    process(uploaded)
    st.rerun()  # uploaded is now None on the next render!

# GOOD — parse the file BEFORE rerunning, store result in session_state
uploaded = st.file_uploader("Upload", type=["json"])
if uploaded:
    config = json.load(uploaded)   # parse immediately
    st.session_state["uploaded_config"] = config  # persist in session_state
    st.rerun()  # config survives the rerun
```

---

## 2. `json.load` vs `json.loads` — File vs String

### The difference

```python
import json

# json.load(file) — reads from a FILE-LIKE OBJECT
with open("config.json") as f:
    data = json.load(f)

# Also works with st.file_uploader (returns a file-like object)
uploaded = st.file_uploader("Upload", type=["json"])
data = json.load(uploaded)

# json.loads(string) — reads from a STRING
json_string = '{"key": "value"}'
data = json.loads(json_string)
```

### Memory trick

```
json.load  → load from File    (no 's')
json.loads → load from String  (with 's')
json.dump  → dump to File      (no 's')
json.dumps → dump to String    (with 's')
```

---

## 3. Permission Key Mapping — UI Names vs JSON Keys

### The problem

The UI uses human-readable names (`"Create Flags"`), but the saved JSON uses
snake_case keys (`"create_flags"`). We need a mapping between them.

```python
# UI column name → JSON config key
PROJ_PERM_KEY_MAP = {
    "Create Flags": "create_flags",
    "Update Flags": "update_flags",
    "Archive Flags": "archive_flags",
    "View Project": "view_project",
    "Manage Metrics": "manage_metrics",
    ...
}

# Usage: look up the JSON key for a UI permission name
json_key = PROJ_PERM_KEY_MAP.get("Create Flags")  # "create_flags"
value = config_data.get(json_key, False)            # True/False from JSON
```

### Why not just convert automatically?

```python
# This would be fragile:
json_key = perm_name.lower().replace(" ", "_")
# "Create Flags" → "create_flags" ✓
# "Update Client Side Availability" → "update_client_side_availability" ✓
# "View SDK Key" → "view_sdk_key" ✓ ...but what about future edge cases?

# Explicit mapping is safer — no surprises
PROJ_PERM_KEY_MAP = {"Create Flags": "create_flags", ...}
```

### Two-direction mapping

```python
# Forward: UI → JSON (for saving/restoring)
json_key = PROJ_PERM_KEY_MAP["Create Flags"]  # "create_flags"

# Reverse: JSON → UI (if needed)
REVERSE_MAP = {v: k for k, v in PROJ_PERM_KEY_MAP.items()}
ui_name = REVERSE_MAP["create_flags"]  # "Create Flags"
```

---

## 4. Session State Hydration — Rebuilding State from Data

### The concept

"Hydration" means taking serialized data (JSON) and rebuilding the live application
state (DataFrames, widget values) from it. It's the reverse of serialization.

```
Serialize:   session_state → RBACConfig → JSON file (download)
Hydrate:     JSON file → parsed dict → session_state (upload)
```

### The pattern

```python
def _restore_config_to_session(config: dict) -> None:
    """Hydrate session_state from a config dict."""

    # Step 1: Scalar values
    st.session_state["project"] = config["project_key"]
    st.session_state["_advisor_customer_name"] = config["customer_name"]

    # Step 2: DataFrames from lists of dicts
    st.session_state.teams = pd.DataFrame({
        "Key": [t["key"] for t in config["teams"]],
        "Name": [t["name"] for t in config["teams"]],
    })

    # Step 3: Permission matrices (need key mapping)
    # ... build project_matrix and env_matrix ...

    # Step 4: Fresh widget keys (critical!)
    st.session_state["_matrix_version"] += 1
```

### Why widget key versioning is needed here too

Same Streamlit caching issue from Phase 27. When we programmatically write DataFrames,
the checkbox widgets cache old values. Bumping `_matrix_version` forces fresh widgets.

```python
# Must do this EVERY TIME we programmatically write to matrices
st.session_state["_matrix_version"] = st.session_state.get("_matrix_version", 0) + 1

# Also clear stale widget keys
for k in list(st.session_state.keys()):
    if k.startswith("proj_") or k.startswith("env_") or k.startswith("teams_editor"):
        del st.session_state[k]
```

### GOTCHA: Restore order matters

```python
# BAD — matrix references teams that don't exist yet
st.session_state.project_matrix = build_matrix(config)  # needs teams!
st.session_state.teams = build_teams(config)              # too late

# GOOD — restore in dependency order
st.session_state.teams = build_teams(config)              # 1. teams first
st.session_state.env_groups = build_envs(config)          # 2. then envs
st.session_state.project_matrix = build_proj_matrix(config)  # 3. then matrices
st.session_state.env_matrix = build_env_matrix(config)    # 4. last
```

---

## Quick Reference Card

```python
# === File uploader ===
uploaded = st.file_uploader("Upload", type=["json"], key="uploader")
if uploaded:
    config = json.load(uploaded)  # json.load for file, json.loads for string

# === Permission key mapping ===
PERM_MAP = {"Create Flags": "create_flags", "Update Flags": "update_flags"}
value = config.get(PERM_MAP["Create Flags"], False)

# === Session state hydration ===
st.session_state.teams = pd.DataFrame({"Key": [...], "Name": [...]})
st.session_state.project_matrix = pd.DataFrame({"Team": [...], "Create Flags": [...]})

# === Widget key versioning (reused from Phase 27) ===
st.session_state["_matrix_version"] += 1
st.session_state["_advisor_applied"] = True

# === Parse before rerun (file_uploader resets) ===
config = json.load(uploaded)           # parse NOW
st.session_state["config"] = config    # persist
st.rerun()                             # file is gone, but config survives
```

---

## Next Steps

- [← DESIGN.md](./DESIGN.md)
