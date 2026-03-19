# Phase 2: Python Concepts Deep Dive

> **Purpose:** This document explains the Python concepts used in Phase 2 (Storage Service) in detail. Read this if you want to understand the "why" behind the code.

---

## Table of Contents

1. [pathlib - Modern File Paths](#1-pathlib---modern-file-paths)
2. [File I/O with Context Managers](#2-file-io-with-context-managers)
3. [Custom Exceptions](#3-custom-exceptions)
4. [Working with Directories](#4-working-with-directories)
5. [File Copying and Backups](#5-file-copying-and-backups)
6. [Slugify and String Normalization](#6-slugify-and-string-normalization)
7. [Type Hints for Paths](#7-type-hints-for-paths)

---

## 1. pathlib - Modern File Paths

### The Old Way vs The New Way

```python
# OLD WAY (os.path) - String-based, error-prone
import os

path = os.path.join("configs", "customers", "acme", "config.json")
if os.path.exists(path):
    with open(path, "r") as f:
        data = f.read()

# NEW WAY (pathlib) - Object-oriented, cleaner
from pathlib import Path

path = Path("configs") / "customers" / "acme" / "config.json"
if path.exists():
    data = path.read_text()
```

### Why pathlib is Better

| Feature | os.path | pathlib |
|---------|---------|---------|
| Joining paths | `os.path.join("a", "b")` | `Path("a") / "b"` |
| Check exists | `os.path.exists(path)` | `path.exists()` |
| Read file | `open(path).read()` | `path.read_text()` |
| Cross-platform | Manual handling | Automatic |
| Type hints | `str` | `Path` |

### Common Path Operations

```python
from pathlib import Path

# Creating paths
path = Path("configs")                    # Relative path
path = Path("/home/user/configs")         # Absolute path
path = Path.cwd()                         # Current working directory
path = Path.home()                        # User's home directory

# Joining paths with /
config_path = Path("configs") / "customers" / "acme" / "config.json"
# Result: configs/customers/acme/config.json

# Path components
path = Path("configs/customers/acme/config.json")
print(path.name)      # "config.json"
print(path.stem)      # "config"
print(path.suffix)    # ".json"
print(path.parent)    # Path("configs/customers/acme")
print(path.parts)     # ("configs", "customers", "acme", "config.json")

# Checking path properties
path.exists()         # True if path exists
path.is_file()        # True if it's a file
path.is_dir()         # True if it's a directory

# Converting to string (when needed for legacy APIs)
str(path)             # "configs/customers/acme/config.json"
```

### Creating Directories

```python
from pathlib import Path

path = Path("configs/customers/acme/history")

# Create directory (fails if parent doesn't exist)
path.mkdir()

# Create directory and all parents (like mkdir -p)
path.mkdir(parents=True)

# Create only if doesn't exist (no error if exists)
path.mkdir(parents=True, exist_ok=True)
```

### Finding Files with glob

```python
from pathlib import Path

configs = Path("configs/customers")

# Find all JSON files
for json_file in configs.glob("*.json"):
    print(json_file)

# Find recursively (all subdirectories)
for json_file in configs.glob("**/*.json"):
    print(json_file)

# Get as list
json_files = list(configs.glob("*.json"))
```

---

## 2. File I/O with Context Managers

### What is a Context Manager?

A **context manager** is a pattern that ensures resources are properly managed (opened and closed). The `with` statement is how you use it.

```python
# WITHOUT context manager (dangerous!)
f = open("file.txt", "r")
data = f.read()
f.close()  # What if an error happens before this line?

# WITH context manager (safe!)
with open("file.txt", "r") as f:
    data = f.read()
# File is automatically closed, even if an error occurs
```

### Why Context Managers Matter

```
WITHOUT 'with':                      WITH 'with':
───────────────                     ─────────────
1. Open file                        1. Open file
2. Read data                        2. Read data
3. ERROR OCCURS! ⚠️                 3. ERROR OCCURS! ⚠️
4. close() never called             4. File auto-closed ✓
5. File handle leaked               5. No resource leak
6. Possible data corruption         6. Safe and clean
```

### Reading Files

```python
from pathlib import Path

path = Path("config.json")

# Method 1: Using with statement (traditional)
with open(path, "r", encoding="utf-8") as f:
    data = f.read()

# Method 2: Using pathlib (simpler for text files)
data = path.read_text(encoding="utf-8")

# Method 3: Read as bytes (for binary files)
binary_data = path.read_bytes()

# Method 4: Read line by line (memory efficient for large files)
with open(path, "r") as f:
    for line in f:
        process(line)
```

### Writing Files

```python
from pathlib import Path
import json

path = Path("config.json")
data = {"name": "test", "value": 123}

# Method 1: Using with statement
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

# Method 2: Using pathlib
path.write_text(json.dumps(data, indent=2), encoding="utf-8")

# Method 3: Append to file
with open(path, "a") as f:
    f.write("\nNew line")
```

### File Modes

| Mode | Description |
|------|-------------|
| `"r"` | Read (default) |
| `"w"` | Write (creates/overwrites) |
| `"a"` | Append |
| `"x"` | Exclusive create (fails if exists) |
| `"b"` | Binary mode (add to others: `"rb"`, `"wb"`) |
| `"t"` | Text mode (default, add to others: `"rt"`) |

---

## 3. Custom Exceptions

### Why Create Custom Exceptions?

```python
# WITHOUT custom exceptions
def load_config(name):
    if not file_exists(name):
        raise Exception("Config not found")  # Generic, unhelpful

# WITH custom exceptions
def load_config(name):
    if not file_exists(name):
        raise ConfigNotFoundError(f"No config for '{name}'")  # Specific!
```

### Creating Custom Exceptions

```python
# Base exception for your module
class StorageError(Exception):
    """Base exception for storage operations."""
    pass


# Specific exceptions that inherit from base
class ConfigNotFoundError(StorageError):
    """Raised when a configuration file doesn't exist."""

    def __init__(self, customer_name: str):
        self.customer_name = customer_name
        super().__init__(f"Configuration not found for '{customer_name}'")


class ConfigParseError(StorageError):
    """Raised when JSON parsing fails."""

    def __init__(self, file_path: str, original_error: Exception):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(f"Failed to parse '{file_path}': {original_error}")


class ConfigWriteError(StorageError):
    """Raised when writing to file fails."""
    pass
```

### Using Custom Exceptions

```python
def load_config(customer_name: str) -> RBACConfig:
    config_path = get_config_path(customer_name)

    if not config_path.exists():
        raise ConfigNotFoundError(customer_name)

    try:
        json_string = config_path.read_text()
        return RBACConfig.from_json(json_string)
    except json.JSONDecodeError as e:
        raise ConfigParseError(str(config_path), e) from e


# Handling in UI
try:
    config = storage.load_config("acme")
except ConfigNotFoundError as e:
    st.error(f"Config not found: {e.customer_name}")
except ConfigParseError as e:
    st.error(f"Invalid config file: {e}")
except StorageError as e:
    st.error(f"Storage error: {e}")  # Catch all storage errors
```

### Exception Hierarchy

```
Exception (built-in)
└── StorageError (our base)
    ├── ConfigNotFoundError
    ├── ConfigParseError
    └── ConfigWriteError
```

### The `from e` Pattern

```python
try:
    data = json.loads(text)
except json.JSONDecodeError as e:
    # 'from e' chains exceptions - preserves original traceback
    raise ConfigParseError(path, e) from e
```

---

## 4. Working with Directories

### Listing Directory Contents

```python
from pathlib import Path

directory = Path("configs/customers")

# List all items (files and folders)
for item in directory.iterdir():
    print(item.name)

# Filter to only directories
for folder in directory.iterdir():
    if folder.is_dir():
        print(f"Folder: {folder.name}")

# Filter to only files
for file in directory.iterdir():
    if file.is_file():
        print(f"File: {file.name}")

# Using list comprehension
folders = [f for f in directory.iterdir() if f.is_dir()]
json_files = [f for f in directory.iterdir() if f.suffix == ".json"]
```

### Safe Directory Operations

```python
from pathlib import Path

def ensure_directory(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def safe_list_directory(path: Path) -> list[Path]:
    """List directory contents, return empty if doesn't exist."""
    if not path.exists():
        return []
    if not path.is_dir():
        return []
    return list(path.iterdir())
```

### Deleting Files and Directories

```python
from pathlib import Path
import shutil

# Delete a file
path = Path("config.json")
if path.exists():
    path.unlink()  # Delete file

# Delete empty directory
path = Path("empty_folder")
if path.exists():
    path.rmdir()  # Only works if empty!

# Delete directory with contents
path = Path("folder_with_files")
if path.exists():
    shutil.rmtree(path)  # Deletes everything inside
```

---

## 5. File Copying and Backups

### Copying Files

```python
import shutil
from pathlib import Path

source = Path("config.json")
destination = Path("backup/config.json")

# Method 1: shutil.copy (copies content only)
shutil.copy(source, destination)

# Method 2: shutil.copy2 (copies content + metadata like timestamps)
shutil.copy2(source, destination)

# Method 3: Using pathlib (read and write)
destination.write_text(source.read_text())
```

### Timestamp-Based Backups

```python
from pathlib import Path
from datetime import datetime

def create_backup(source_path: Path, backup_dir: Path) -> Path:
    """Create a timestamped backup of a file."""

    # Ensure backup directory exists
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp: 2024-03-11_14-30-00
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create backup filename
    backup_name = f"{timestamp}.json"
    backup_path = backup_dir / backup_name

    # Copy the file
    shutil.copy2(source_path, backup_path)

    return backup_path
```

### Rotating/Cleaning Old Backups

```python
from pathlib import Path

def cleanup_old_backups(backup_dir: Path, max_keep: int = 10) -> None:
    """Remove old backups, keeping only the most recent ones."""

    if not backup_dir.exists():
        return

    # Get all backup files, sorted by name (oldest first)
    # Timestamp format ensures alphabetical = chronological
    backups = sorted(backup_dir.glob("*.json"))

    # Remove oldest if we have too many
    while len(backups) > max_keep:
        oldest = backups.pop(0)  # Remove from list
        oldest.unlink()          # Delete file
        print(f"Deleted old backup: {oldest.name}")
```

---

## 6. Slugify and String Normalization

### What is Slugify?

Converting a human-readable string into a URL/filename-safe format.

```
"Acme Corporation"  →  "acme-corporation"
"John's Company"    →  "johns-company"
"Test 123!"         →  "test-123"
```

### Simple Slugify Implementation

```python
import re

def slugify(text: str) -> str:
    """
    Convert text to a filename-safe slug.

    Examples:
        >>> slugify("Acme Corporation")
        'acme-corporation'
        >>> slugify("John's Company")
        'johns-company'
    """
    # Lowercase
    slug = text.lower()

    # Replace spaces with hyphens
    slug = slug.replace(" ", "-")

    # Remove special characters (keep only letters, numbers, hyphens)
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Remove multiple consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    return slug
```

### Using the `python-slugify` Library

```python
# Install: pip install python-slugify
from slugify import slugify

slugify("Acme Corporation")  # "acme-corporation"
slugify("Héllo Wörld")       # "hello-world" (handles unicode)
```

### Why Slugify for Filenames?

```
Filesystem restrictions:
────────────────────────
Windows: Can't use  \ / : * ? " < > |
macOS:   Can't use  : /
Linux:   Can't use  /

Safe characters: a-z, 0-9, hyphen, underscore

Slugify ensures your customer names become valid folder names!
```

---

## 7. Type Hints for Paths

### Using Path in Type Hints

```python
from pathlib import Path
from typing import Optional

def save_config(config: RBACConfig, path: Path) -> None:
    """Save configuration to the specified path."""
    path.write_text(config.to_json())


def load_config(path: Path) -> Optional[RBACConfig]:
    """Load configuration from path, return None if not found."""
    if not path.exists():
        return None
    return RBACConfig.from_json(path.read_text())


def list_configs(directory: Path) -> list[Path]:
    """List all config files in directory."""
    return list(directory.glob("*.json"))
```

### Path vs str in Function Parameters

```python
from pathlib import Path
from typing import Union

# Option 1: Accept only Path (strict)
def load(path: Path) -> str:
    return path.read_text()

# Option 2: Accept Path or str (flexible)
def load(path: Union[Path, str]) -> str:
    path = Path(path)  # Convert if string
    return path.read_text()

# Option 3: Python 3.10+ union syntax
def load(path: Path | str) -> str:
    path = Path(path)
    return path.read_text()
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│                 FILE I/O CHEAT SHEET (PHASE 2)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PATHLIB BASICS                                                      │
│  ───────────────                                                     │
│  from pathlib import Path                                           │
│                                                                      │
│  path = Path("folder") / "file.json"   # Join paths                │
│  path.exists()                         # Check exists               │
│  path.is_file()                        # Is it a file?             │
│  path.is_dir()                         # Is it a directory?        │
│  path.mkdir(parents=True, exist_ok=True)  # Create directory       │
│                                                                      │
│  FILE OPERATIONS                                                     │
│  ────────────────                                                    │
│  data = path.read_text()               # Read file                  │
│  path.write_text(data)                 # Write file                 │
│  path.unlink()                         # Delete file                │
│                                                                      │
│  DIRECTORY OPERATIONS                                                │
│  ─────────────────────                                               │
│  list(path.iterdir())                  # List contents              │
│  list(path.glob("*.json"))             # Find by pattern            │
│  list(path.glob("**/*.json"))          # Recursive find             │
│                                                                      │
│  CONTEXT MANAGERS                                                    │
│  ─────────────────                                                   │
│  with open(path, "r") as f:            # Safe file handling         │
│      data = f.read()                                                │
│                                                                      │
│  CUSTOM EXCEPTIONS                                                   │
│  ──────────────────                                                  │
│  class MyError(Exception):             # Define exception           │
│      pass                                                           │
│                                                                      │
│  raise MyError("message")              # Raise exception            │
│  raise NewError() from original        # Chain exceptions           │
│                                                                      │
│  BACKUPS                                                             │
│  ────────                                                            │
│  import shutil                                                       │
│  shutil.copy2(source, dest)            # Copy with metadata         │
│  shutil.rmtree(path)                   # Delete directory           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

After understanding these concepts, you're ready to implement the storage service:

1. **[DESIGN.md](./DESIGN.md)** - Review the HLD, DLD, and pseudo logic
2. **Implementation** - Create the storage service files

Each file will include lesson comments referencing this document.
