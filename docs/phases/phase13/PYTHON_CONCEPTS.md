# Phase 13: Python Concepts

Concepts used in generating the client delivery ZIP package.

---

## Table of Contents

1. [In-Memory ZIP with BytesIO](#1-in-memory-zip-with-bytesio)
2. [zipfile.ZipFile](#2-zipfilezipfile)
3. [str.zfill() — Zero-Padding Numbers](#3-strzfill--zero-padding-numbers)
4. [Code Generation as Strings](#4-code-generation-as-strings)
5. [pathlib.Path for File Operations](#5-pathlibpath-for-file-operations)
6. [textwrap.dedent for Multiline Strings](#6-textwrapdedent-for-multiline-strings)
7. [Quick Reference Card](#quick-reference-card)

---

## 1. In-Memory ZIP with BytesIO

### The problem

`st.download_button` needs the file content as `bytes` in memory. We don't want to write a file to disk (ephemeral on Streamlit Cloud) and we don't want the user to have to download from a path.

### The solution: `io.BytesIO`

`BytesIO` is an in-memory buffer that behaves like a file — you can write to it, then read the bytes back.

```python
import io
import zipfile

# Create an in-memory buffer (acts like a file, but in RAM)
buffer = io.BytesIO()

# Write a ZIP into the buffer instead of a file on disk
with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("hello.txt", "Hello, World!")
    zf.writestr("data/config.json", '{"key": "value"}')

# Get the bytes from the buffer
zip_bytes = buffer.getvalue()

# Pass directly to Streamlit download button
st.download_button(
    label="📦 Download",
    data=zip_bytes,                    # ← bytes, no file on disk needed
    file_name="package.zip",
    mime="application/zip"
)
```

### Why `ZIP_DEFLATED`?

`ZIP_DEFLATED` applies gzip compression. For JSON files (highly repetitive text), this typically reduces file size by 60-80%.

```python
# No compression (larger file)
zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_STORED)

# With compression (smaller file) ← use this
zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED)
```

---

## 2. zipfile.ZipFile

### Writing files into a ZIP

```python
with zipfile.ZipFile(buffer, mode="w") as zf:

    # Write a string as a file in the ZIP
    zf.writestr("folder/filename.txt", "file content here")

    # Write bytes as a file
    zf.writestr("data/image.png", b"\x89PNG...")

    # Write a file from disk into the ZIP
    zf.write("/path/to/file.py", arcname="deploy.py")
    #                             ^ arcname = name inside the ZIP
```

### Reading files from a ZIP

```python
with zipfile.ZipFile("package.zip", mode="r") as zf:

    # List all files
    print(zf.namelist())

    # Read a specific file
    content = zf.read("folder/filename.txt")
    text = content.decode("utf-8")
```

### ZipFile structure matters

The `arcname` (archive name) is the path inside the ZIP. Structure it carefully:
```python
# All files inside a root folder = clean unzip experience
zf.writestr("voya_deployment/README.md", content)
zf.writestr("voya_deployment/deploy.py", script)
zf.writestr("voya_deployment/01_roles/01_create-flags.json", role_json)

# User unzips → gets a single "voya_deployment" folder, not a mess of files
```

---

## 3. str.zfill() — Zero-Padding Numbers

### The problem

Files sort alphabetically in most file browsers. If role 10 is named `10_update-flags.json`, it sorts BEFORE `2_archive-flags.json` because `"1" < "2"` alphabetically.

### The solution: zero-pad the number prefix

```python
# str.zfill(width) pads with zeros on the left to reach the given width

str(1).zfill(2)   # → "01"
str(9).zfill(2)   # → "09"
str(10).zfill(2)  # → "10"   ← already 2 chars, no padding needed
str(5).zfill(3)   # → "005"

# Usage in package generator
for index, role in enumerate(payload.roles, start=1):
    prefix = str(index).zfill(2)                        # 1→"01", 10→"10"
    filename = f"01_roles/{prefix}_{role['key']}.json"  # "01_create-flags.json"
```

### Result: files sort correctly

```
01_create-flags.json
02_update-flags.json
03_archive-flags.json
...
10_view-sdk-key.json   ← sorts AFTER 09, not before 02
```

---

## 4. Code Generation as Strings

### The concept

`deploy.py` is generated dynamically by the RBAC Builder — it's a Python script **stored as a Python string**.

This is called **code generation** — writing code that writes code.

```python
def _build_deploy_script(self, customer_name: str, project_key: str) -> str:
    """Returns a complete Python script as a string."""

    return f"""#!/usr/bin/env python3
\"\"\"
LaunchDarkly RBAC Deployment Script
Customer: {customer_name}
Project:  {project_key}
\"\"\"

import json
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent

def load_settings():
    with open(BASE_DIR / "settings.json") as f:
        return json.load(f)

class LDClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {{
            "Authorization": api_key,
            "Content-Type": "application/json"
        }}
    ...
"""
# Note: {{ and }} for literal braces in the generated script
```

### Gotcha: escaping braces in generated code

The generated script itself uses `{...}` for Python dict literals. Since we're generating it with an f-string, we need `{{}}`:

```python
# In the generator (f-string):
f"self.headers = {{\"Authorization\": api_key}}"

# Generates this output in deploy.py:
self.headers = {"Authorization": api_key}
```

---

## 5. pathlib.Path for File Operations

### The concept

`pathlib.Path` is the modern Python way to work with file paths. It's cleaner than string concatenation.

Used in `deploy.py` so the client's script can find its own files:

```python
from pathlib import Path

# __file__ = the path of the currently running script
BASE_DIR = Path(__file__).parent     # folder containing deploy.py

ROLES_DIR  = BASE_DIR / "01_roles"  # / operator joins paths (not string division!)
TEAMS_DIR  = BASE_DIR / "02_teams"
SETTINGS   = BASE_DIR / "settings.json"

# Loading a settings file relative to the script
with open(BASE_DIR / "settings.json") as f:
    settings = json.load(f)

# Listing files in a directory, sorted
role_files = sorted(ROLES_DIR.glob("*.json"))
#                             ^ glob pattern matches all .json files
```

### Why not os.path?

```python
# Old way (os.path — verbose)
import os
roles_dir = os.path.join(os.path.dirname(__file__), "01_roles")
files = sorted([f for f in os.listdir(roles_dir) if f.endswith(".json")])

# New way (pathlib — readable)
ROLES_DIR = Path(__file__).parent / "01_roles"
files = sorted(ROLES_DIR.glob("*.json"))
```

---

## 6. textwrap.dedent for Multiline Strings

### The problem

Long multiline strings inside a function are indented to match the code, but that indentation becomes part of the string content.

```python
def generate_readme():
    return """
    # Title
    Some content
    """
    # Result has leading spaces on every line — looks wrong in Markdown
```

### The solution: textwrap.dedent

```python
import textwrap

def generate_readme():
    return textwrap.dedent("""
        # Title
        Some content
    """).strip()
    # strip() removes leading/trailing newlines
    # dedent() removes common leading whitespace from all lines
```

---

## Quick Reference Card

```python
# In-memory ZIP
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("folder/file.txt", "content")
bytes_data = buffer.getvalue()

# Zero-padded numbers
str(1).zfill(2)    → "01"
str(10).zfill(2)   → "10"

# Paths relative to script
BASE_DIR = Path(__file__).parent
config = BASE_DIR / "settings.json"
files = sorted(BASE_DIR.glob("*.json"))

# Escaped braces in f-strings (for generated code)
f"dict = {{\"key\": \"value\"}}"  → 'dict = {"key": "value"}'

# Clean multiline strings
textwrap.dedent("""
    line one
    line two
""").strip()
```
