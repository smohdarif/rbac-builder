# Phase 2: Storage Service

> **Goal:** Save and load RBAC configurations to/from JSON files
> **Depends On:** Phase 1 (Data Models) ✅

---

## Quick Links

| Document | Purpose |
|----------|---------|
| [DESIGN.md](./DESIGN.md) | HLD, DLD, pseudo logic, implementation plan |
| [PYTHON_CONCEPTS.md](./PYTHON_CONCEPTS.md) | Deep dive into file I/O, pathlib, exceptions |

---

## Overview

### What We're Building

```
services/
├── __init__.py           # Package exports
└── storage.py            # StorageService class

configs/
├── customers/            # Saved customer configurations
│   └── {customer}/
│       ├── config.json   # Current config
│       └── history/      # Backups
└── templates/            # Starter templates
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Save** | Save RBACConfig to JSON file |
| **Load** | Load RBACConfig from JSON file |
| **List** | List all saved customers |
| **Delete** | Remove a configuration |
| **History** | Automatic backups on save |
| **Templates** | Pre-built starter configs |

### StorageService Methods

```python
from services import StorageService

storage = StorageService()

# Save configuration
storage.save(config)

# Load configuration
config = storage.load("acme-corp")

# List all customers
customers = storage.list_customers()

# Check if exists
exists = storage.exists("acme-corp")

# Delete configuration
storage.delete("acme-corp")

# Load template
config = storage.load_template("standard-4-env")
```

---

## Python Concepts Used

| Concept | What It Does | Learn More |
|---------|--------------|------------|
| `pathlib.Path` | Modern file path handling | [Section 1](./PYTHON_CONCEPTS.md#1-pathlib---modern-file-paths) |
| Context managers | Safe file I/O with `with` | [Section 2](./PYTHON_CONCEPTS.md#2-file-io-with-context-managers) |
| Custom exceptions | Domain-specific errors | [Section 3](./PYTHON_CONCEPTS.md#3-custom-exceptions) |
| `glob()` | Find files by pattern | [Section 4](./PYTHON_CONCEPTS.md#4-working-with-directories) |
| `shutil` | Copy files for backups | [Section 5](./PYTHON_CONCEPTS.md#5-file-copying-and-backups) |
| Slugify | Safe folder names | [Section 6](./PYTHON_CONCEPTS.md#6-slugify-and-string-normalization) |

---

## File Structure

```
configs/
├── customers/
│   ├── acme-corporation/
│   │   ├── config.json           # Current config
│   │   └── history/
│   │       ├── 2024-03-10_14-30-00.json
│   │       └── 2024-03-08_09-15-00.json
│   │
│   └── another-customer/
│       └── config.json
│
└── templates/
    ├── standard-4-env.json
    └── minimal-2-env.json
```

---

## Implementation Checklist

- [x] `services/__init__.py` - Package setup
- [x] `services/storage.py` - StorageService class
  - [x] `save()` - Save configuration
  - [x] `load()` - Load configuration
  - [x] `exists()` - Check if exists
  - [x] `delete()` - Delete configuration
  - [x] `list_customers()` - List all customers
  - [x] `list_templates()` - List templates
  - [x] `load_template()` - Load a template
  - [x] `_create_backup()` - Create timestamped backup
  - [x] `_cleanup_old_backups()` - Remove old backups
- [x] `configs/templates/standard-4-env.json` - Starter template
- [x] `configs/templates/minimal-2-env.json` - Minimal template

---

## Status

| Item | Status |
|------|--------|
| HLD | ✅ Complete |
| DLD | ✅ Complete |
| Pseudo Logic | ✅ Complete |
| Python Concepts Doc | ✅ Complete |
| Implementation | ✅ Complete |

---

## Integration with UI

```python
# In app.py sidebar or Deploy tab

# Save button
if st.button("💾 Save Configuration"):
    config = build_config_from_session_state()
    storage.save(config)
    st.success("Saved!")

# Load dropdown
customers = storage.list_customers()
selected = st.selectbox("Load Configuration", customers)
if st.button("📂 Load"):
    config = storage.load(selected)
    populate_session_state(config)
```

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Phase 1: Data Models](../phase1/) ✅ | **Phase 2: Storage** | Phase 3: Payload Builder |

[← Back to Phases Index](../)
