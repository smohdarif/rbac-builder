# Phase 2: Storage Service Design Document

> **Phase:** 2 of 10
> **Status:** 📋 Planning
> **Goal:** Save and load RBAC configurations to/from JSON files
> **Depends On:** Phase 1 (Data Models)

---

## Related Documents

| Document | Description |
|----------|-------------|
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Deep dive into file I/O, pathlib, JSON, error handling |
| [README.md](./README.md) | Phase 2 overview and quick reference |
| [../phase1/](../phase1/) | Phase 1 - Data Models (dependency) |

---

## Table of Contents

1. [High-Level Design (HLD)](#high-level-design-hld)
2. [Detailed Low-Level Design (DLD)](#detailed-low-level-design-dld)
3. [Pseudo Logic](#pseudo-logic)
4. [Implementation Plan](#implementation-plan)
5. [Learning Resources](#learning-resources)

---

## High-Level Design (HLD)

### What Are We Building?

A **Storage Service** that handles saving and loading RBAC configurations to/from the file system. This enables:
- **Persistence**: Save work and continue later
- **Sharing**: Export configs to share with others
- **Versioning**: Keep history of configuration changes
- **Templates**: Load pre-built starter configurations

### Why Do We Need Storage?

```
WITHOUT Storage:                      WITH Storage:
──────────────────                   ──────────────────
• Data lost on browser refresh       • Data persists across sessions
• Can't share configurations         • Export/import configs as JSON
• No history of changes              • Version history maintained
• Start from scratch each time       • Load templates to start quickly
```

### Where Does Storage Fit in Our Architecture?

```
┌─────────────────────────────────────────────────────────────────────┐
│                           RBAC BUILDER                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐         ┌──────────────────────────────────────┐ │
│  │   UI Layer   │         │         SERVICES LAYER               │ │
│  │   (app.py)   │         │  ┌──────────────┐  ┌──────────────┐ │ │
│  │              │ ──────► │  │   STORAGE    │  │  (Future)    │ │ │
│  │  Save button │         │  │   SERVICE    │  │  Deployer    │ │ │
│  │  Load button │         │  │              │  │  Validator   │ │ │
│  └──────────────┘         │  │  ◄── HERE    │  │  LD Client   │ │ │
│                           │  └──────┬───────┘  └──────────────┘ │ │
│                           └─────────┼───────────────────────────┘ │
│                                     │                              │
│                                     ▼                              │
│                           ┌──────────────────┐                     │
│                           │   FILE SYSTEM    │                     │
│                           │                  │                     │
│                           │  configs/        │                     │
│                           │  ├── acme/       │                     │
│                           │  │   └── config.json                  │
│                           │  └── templates/  │                     │
│                           └──────────────────┘                     │
│                                                                      │
│                           ┌──────────────────┐                     │
│                           │   DATA MODELS    │                     │
│                           │   (Phase 1) ✅   │                     │
│                           └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Features

| Feature | Description |
|---------|-------------|
| **Save Config** | Save RBACConfig to a JSON file |
| **Load Config** | Load RBACConfig from a JSON file |
| **List Configs** | List all saved customer configurations |
| **Delete Config** | Remove a saved configuration |
| **Export** | Generate downloadable JSON |
| **Templates** | Load pre-built starter configurations |
| **History** | Keep backup of previous versions |

### Data Flow

```
SAVE FLOW:
──────────

    User clicks "Save"
           │
           ▼
    ┌─────────────────┐
    │  UI (app.py)    │
    │                 │
    │  Build config   │
    │  from session   │
    │  state          │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Storage Service │
    │                 │
    │ storage.save()  │
    │                 │
    │ 1. Validate     │
    │ 2. Create dirs  │
    │ 3. Backup old   │
    │ 4. Write JSON   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  File System    │
    │                 │
    │  configs/       │
    │  └── acme/      │
    │      └── config.json
    └─────────────────┘


LOAD FLOW:
──────────

    User selects config
           │
           ▼
    ┌─────────────────┐
    │  UI (app.py)    │
    │                 │
    │  Call load()    │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Storage Service │
    │                 │
    │ storage.load()  │
    │                 │
    │ 1. Read file    │
    │ 2. Parse JSON   │
    │ 3. Create       │
    │    RBACConfig   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  UI (app.py)    │
    │                 │
    │  Populate       │
    │  session_state  │
    │  from config    │
    └─────────────────┘
```

---

## Detailed Low-Level Design (DLD)

### File Structure

```
rbac-builder/
├── services/
│   ├── __init__.py           # Package exports
│   └── storage.py            # Storage service (THIS PHASE)
│
├── configs/                   # Saved configurations
│   ├── customers/
│   │   ├── acme-corp/
│   │   │   ├── config.json           # Current configuration
│   │   │   └── history/
│   │   │       ├── 2024-03-10_14-30.json
│   │   │       └── 2024-03-08_09-15.json
│   │   │
│   │   └── another-customer/
│   │       └── config.json
│   │
│   └── templates/             # Reusable starter templates
│       ├── standard-4-env.json
│       ├── minimal-2-env.json
│       └── enterprise.json
│
└── models/                    # (Phase 1 - Done)
    └── ...
```

### Storage Directory Structure

```
configs/
├── customers/                    ◄── Customer configurations
│   └── {customer_name}/          ◄── Folder per customer (slugified)
│       ├── config.json           ◄── Current/active config
│       └── history/              ◄── Previous versions
│           └── {timestamp}.json  ◄── Backup with timestamp
│
└── templates/                    ◄── Starter templates
    └── {template_name}.json
```

### Class Design: StorageService

```
┌─────────────────────────────────────────────────────────────────────┐
│                         StorageService                               │
├─────────────────────────────────────────────────────────────────────┤
│  Attributes:                                                         │
│  ┌─────────────────┬──────────────┬─────────────────────────────┐  │
│  │ Attribute       │ Type         │ Description                  │  │
│  ├─────────────────┼──────────────┼─────────────────────────────┤  │
│  │ base_path       │ Path         │ Root path for configs/      │  │
│  │ customers_path  │ Path         │ Path to customers/ folder   │  │
│  │ templates_path  │ Path         │ Path to templates/ folder   │  │
│  │ max_history     │ int          │ Max backups to keep (10)    │  │
│  └─────────────────┴──────────────┴─────────────────────────────┘  │
│                                                                      │
│  Methods:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ CORE OPERATIONS                                                  ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ save(config: RBACConfig) -> Path                                ││
│  │   Save configuration to file, creating backup if exists         ││
│  │                                                                  ││
│  │ load(customer_name: str) -> RBACConfig                          ││
│  │   Load configuration from file                                  ││
│  │                                                                  ││
│  │ delete(customer_name: str) -> bool                              ││
│  │   Delete a customer's configuration                             ││
│  │                                                                  ││
│  │ exists(customer_name: str) -> bool                              ││
│  │   Check if a configuration exists                               ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ LISTING OPERATIONS                                               ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ list_customers() -> list[str]                                   ││
│  │   Get list of all saved customer names                          ││
│  │                                                                  ││
│  │ list_templates() -> list[str]                                   ││
│  │   Get list of available templates                               ││
│  │                                                                  ││
│  │ list_history(customer_name: str) -> list[Path]                  ││
│  │   Get list of backup files for a customer                       ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ TEMPLATE OPERATIONS                                              ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ load_template(template_name: str) -> RBACConfig                 ││
│  │   Load a template configuration                                 ││
│  │                                                                  ││
│  │ save_as_template(config: RBACConfig, name: str) -> Path         ││
│  │   Save current config as a reusable template                    ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ EXPORT OPERATIONS                                                ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ export_json(config: RBACConfig) -> str                          ││
│  │   Generate JSON string for download                             ││
│  │                                                                  ││
│  │ import_json(json_string: str) -> RBACConfig                     ││
│  │   Parse JSON string into RBACConfig                             ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ HISTORY OPERATIONS                                               ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ load_from_history(customer_name: str, timestamp: str)           ││
│  │   -> RBACConfig                                                 ││
│  │   Load a specific version from history                          ││
│  │                                                                  ││
│  │ _create_backup(customer_name: str) -> Path                      ││
│  │   Create a timestamped backup of current config                 ││
│  │                                                                  ││
│  │ _cleanup_old_backups(customer_name: str) -> None                ││
│  │   Remove old backups exceeding max_history                      ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Helper Functions

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Helper Functions                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  slugify(name: str) -> str                                          │
│    Convert "Acme Corporation" → "acme-corporation"                  │
│    Used for folder names                                            │
│                                                                      │
│  get_timestamp() -> str                                             │
│    Generate "2024-03-11_14-30-00" format for backups                │
│                                                                      │
│  ensure_directory(path: Path) -> None                               │
│    Create directory if it doesn't exist                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Error Handling

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Custom Exceptions                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  class StorageError(Exception):                                      │
│      """Base exception for storage operations."""                   │
│      pass                                                            │
│                                                                      │
│  class ConfigNotFoundError(StorageError):                           │
│      """Raised when a configuration file doesn't exist."""          │
│      pass                                                            │
│                                                                      │
│  class ConfigParseError(StorageError):                              │
│      """Raised when JSON parsing fails."""                          │
│      pass                                                            │
│                                                                      │
│  class ConfigWriteError(StorageError):                              │
│      """Raised when writing to file fails."""                       │
│      pass                                                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### JSON File Format

```json
{
  "version": "1.0",
  "customer_name": "Acme Corporation",
  "project_key": "mobile-app",
  "mode": "Manual",
  "created_at": "2024-03-11T10:00:00",
  "updated_at": "2024-03-11T14:30:00",

  "teams": [
    {
      "key": "dev",
      "name": "Developer",
      "description": "Development team"
    }
  ],

  "env_groups": [
    {
      "key": "production",
      "requires_approval": true,
      "is_critical": true,
      "notes": "Production environment"
    }
  ],

  "project_permissions": [
    {
      "team_key": "dev",
      "create_flags": true,
      "update_flags": true,
      "archive_flags": false,
      "..."
    }
  ],

  "env_permissions": [
    {
      "team_key": "dev",
      "environment_key": "production",
      "update_targeting": false,
      "review_changes": true,
      "..."
    }
  ]
}
```

---

## Pseudo Logic

### 1. Save Configuration

```
FUNCTION save(config: RBACConfig) -> Path:
    """Save configuration to file system."""

    # Step 1: Validate the config
    IF config.customer_name is empty:
        RAISE ValueError("Customer name is required")

    # Step 2: Create folder path
    customer_slug = slugify(config.customer_name)
    customer_path = base_path / "customers" / customer_slug

    # Step 3: Ensure directory exists
    ensure_directory(customer_path)
    ensure_directory(customer_path / "history")

    # Step 4: If config exists, create backup first
    config_file = customer_path / "config.json"
    IF config_file exists:
        _create_backup(customer_slug)

    # Step 5: Update the timestamp
    config.mark_updated()

    # Step 6: Write JSON to file
    json_string = config.to_json()
    TRY:
        write config_file with json_string
    CATCH IOError:
        RAISE ConfigWriteError("Failed to write config")

    # Step 7: Cleanup old backups
    _cleanup_old_backups(customer_slug)

    RETURN config_file
```

### 2. Load Configuration

```
FUNCTION load(customer_name: str) -> RBACConfig:
    """Load configuration from file system."""

    # Step 1: Build the file path
    customer_slug = slugify(customer_name)
    config_file = base_path / "customers" / customer_slug / "config.json"

    # Step 2: Check if file exists
    IF NOT config_file exists:
        RAISE ConfigNotFoundError(f"No config for '{customer_name}'")

    # Step 3: Read the file
    TRY:
        json_string = read config_file
    CATCH IOError:
        RAISE StorageError("Failed to read config file")

    # Step 4: Parse JSON into RBACConfig
    TRY:
        config = RBACConfig.from_json(json_string)
    CATCH JSONDecodeError:
        RAISE ConfigParseError("Invalid JSON in config file")

    RETURN config
```

### 3. List Customers

```
FUNCTION list_customers() -> list[str]:
    """Get list of all saved customer names."""

    customers_path = base_path / "customers"

    # Ensure the directory exists
    IF NOT customers_path exists:
        RETURN []

    # Get all subdirectories that have a config.json
    customers = []
    FOR folder IN customers_path.iterdir():
        IF folder is directory:
            config_file = folder / "config.json"
            IF config_file exists:
                # Load config to get actual customer name
                TRY:
                    config = load(folder.name)
                    customers.append(config.customer_name)
                CATCH:
                    # Skip invalid configs
                    CONTINUE

    RETURN sorted(customers)
```

### 4. Create Backup

```
FUNCTION _create_backup(customer_slug: str) -> Path:
    """Create timestamped backup of current config."""

    customer_path = base_path / "customers" / customer_slug
    config_file = customer_path / "config.json"
    history_path = customer_path / "history"

    # Generate timestamp: 2024-03-11_14-30-00
    timestamp = get_timestamp()
    backup_file = history_path / f"{timestamp}.json"

    # Copy current config to history
    copy config_file TO backup_file

    RETURN backup_file
```

### 5. Cleanup Old Backups

```
FUNCTION _cleanup_old_backups(customer_slug: str) -> None:
    """Remove backups exceeding max_history limit."""

    history_path = base_path / "customers" / customer_slug / "history"

    IF NOT history_path exists:
        RETURN

    # Get all backup files sorted by name (oldest first)
    backups = sorted(history_path.glob("*.json"))

    # Remove oldest backups if exceeding limit
    WHILE len(backups) > max_history:
        oldest = backups.pop(0)
        delete oldest
```

### 6. Load Template

```
FUNCTION load_template(template_name: str) -> RBACConfig:
    """Load a starter template."""

    template_file = base_path / "templates" / f"{template_name}.json"

    IF NOT template_file exists:
        RAISE ConfigNotFoundError(f"Template '{template_name}' not found")

    json_string = read template_file
    config = RBACConfig.from_json(json_string)

    # Clear timestamps so it's treated as new
    config.created_at = now()
    config.updated_at = now()

    RETURN config
```

### 7. Integration with UI (app.py)

```
PSEUDO CODE for app.py integration:

# Initialize storage service
storage = StorageService(base_path="./configs")

# SAVE BUTTON HANDLER
IF st.button("Save Configuration"):
    # Build config from session state
    config = build_config_from_session_state()

    TRY:
        path = storage.save(config)
        st.success(f"Saved to {path}")
    CATCH StorageError as e:
        st.error(f"Failed to save: {e}")


# LOAD DROPDOWN
customers = storage.list_customers()
selected = st.selectbox("Load Configuration", customers)

IF st.button("Load"):
    TRY:
        config = storage.load(selected)
        populate_session_state(config)
        st.success("Loaded successfully")
    CATCH ConfigNotFoundError:
        st.error("Configuration not found")


# TEMPLATE DROPDOWN
templates = storage.list_templates()
selected_template = st.selectbox("Start from Template", templates)

IF st.button("Load Template"):
    config = storage.load_template(selected_template)
    populate_session_state(config)
    st.info("Template loaded - customize and save as new config")
```

---

## Implementation Plan

### Step-by-Step Implementation

```
STEP 1: Create services/__init__.py
        └── Empty package file

STEP 2: Create services/storage.py
        ├── Import dependencies (pathlib, json, etc.)
        ├── Define custom exceptions
        ├── Define helper functions (slugify, etc.)
        └── Create StorageService class

STEP 3: Implement core methods
        ├── save()
        ├── load()
        ├── exists()
        └── delete()

STEP 4: Implement listing methods
        ├── list_customers()
        └── list_templates()

STEP 5: Implement history methods
        ├── _create_backup()
        ├── _cleanup_old_backups()
        └── list_history()

STEP 6: Implement template methods
        ├── load_template()
        └── save_as_template()

STEP 7: Create starter templates
        ├── templates/standard-4-env.json
        └── templates/minimal-2-env.json

STEP 8: Update services/__init__.py
        └── Export StorageService

STEP 9: Test the service
        └── Manual testing with Python REPL
```

### Python Concepts You'll Learn

| Concept | What It Does | Example |
|---------|--------------|---------|
| `pathlib.Path` | Object-oriented file paths | `Path("configs") / "file.json"` |
| `with open()` | Safe file handling | Context manager pattern |
| `json.dumps/loads` | JSON serialization | Already used in Phase 1 |
| Custom exceptions | Domain-specific errors | `class ConfigNotFoundError` |
| `glob()` | Find files by pattern | `path.glob("*.json")` |
| `shutil.copy` | Copy files | For creating backups |

### Estimated Learning Topics

```
┌─────────────────────────────────────────────────────────────────┐
│                  PYTHON LESSONS IN PHASE 2                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LESSON 40: pathlib.Path                                        │
│  ├── Creating paths with / operator                             │
│  ├── Path.exists(), Path.is_file(), Path.is_dir()              │
│  └── Path.mkdir(), Path.glob(), Path.iterdir()                 │
│                                                                  │
│  LESSON 41: File I/O with Context Managers                      │
│  ├── The 'with' statement                                       │
│  ├── Why context managers prevent resource leaks               │
│  └── read_text() and write_text() methods                      │
│                                                                  │
│  LESSON 42: Custom Exceptions                                   │
│  ├── When to create custom exceptions                          │
│  ├── Exception hierarchy                                        │
│  └── Adding context to exceptions                              │
│                                                                  │
│  LESSON 43: Working with Directories                            │
│  ├── Creating directories with mkdir(parents=True)             │
│  ├── Listing contents with iterdir() and glob()                │
│  └── Checking existence before operations                      │
│                                                                  │
│  LESSON 44: File Copying and Backup Strategies                  │
│  ├── shutil.copy vs shutil.copy2                               │
│  ├── Timestamp-based backup naming                             │
│  └── Rotation/cleanup of old files                             │
│                                                                  │
│  LESSON 45: Slugify and String Normalization                    │
│  ├── Converting names to valid filenames                       │
│  ├── Handling special characters                               │
│  └── Unicode considerations                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary

### What We're Building

- **StorageService class** with methods for save/load/delete
- **File structure** for organized config storage
- **Backup system** with automatic history
- **Templates** for quick-start configurations
- **Error handling** with custom exceptions

### Why This Matters

```
Without Storage:                     With Storage:
────────────────                    ──────────────
• Data lost on refresh              • Persistent configurations
• Manual JSON handling              • Automated save/load
• No version history                • Backup and restore
• No templates                      • Quick-start templates
• Error-prone                       • Robust error handling
```

### Integration Points

| Component | How Storage Connects |
|-----------|---------------------|
| **app.py** | Calls save(), load(), list_customers() |
| **RBACConfig** | Uses to_json(), from_json() for serialization |
| **UI buttons** | Save, Load, Export trigger storage methods |
| **Session state** | Populated from loaded config |

---

## Learning Resources

### Deep Dive Documents

| Topic | Document | Description |
|-------|----------|-------------|
| **All Phase 2 Concepts** | [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | File I/O, pathlib, exceptions |
| pathlib | [Section 1](./PYTHON_CONCEPTS.md#1-pathlib---modern-file-paths) | Path operations |
| File I/O | [Section 2](./PYTHON_CONCEPTS.md#2-file-io-with-context-managers) | Reading and writing files |
| Exceptions | [Section 3](./PYTHON_CONCEPTS.md#3-custom-exceptions) | Creating custom exceptions |

### External Resources

| Resource | Link |
|----------|------|
| Python pathlib Docs | https://docs.python.org/3/library/pathlib.html |
| Context Managers | https://realpython.com/python-with-statement/ |
| Custom Exceptions | https://realpython.com/python-exceptions/ |

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Phase 1: Data Models](../phase1/) | **Phase 2: Storage** | Phase 3: Payload Builder |

[← Back to Phases Index](../) | [View Python Concepts →](./PYTHON_CONCEPTS.md)
