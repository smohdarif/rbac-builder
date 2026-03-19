# Phase 1: Python Concepts Deep Dive

> **Purpose:** This document explains the Python concepts used in Phase 1 (Data Models) in detail. Read this if you want to understand the "why" behind the code.

---

## Table of Contents

1. [Python Classes - The Basics](#1-python-classes---the-basics)
2. [Dataclasses - The Modern Way](#2-dataclasses---the-modern-way)
3. [Type Hints - Declaring Types](#3-type-hints---declaring-types)
4. [Default Values and field()](#4-default-values-and-field)
5. [Validation with __post_init__](#5-validation-with-__post_init__)
6. [Serialization - To and From JSON](#6-serialization---to-and-from-json)
7. [Python Packages and __init__.py](#7-python-packages-and-__init__py)

---

## 1. Python Classes - The Basics

### What is a Class?

A **class** is a blueprint for creating objects. Think of it like a cookie cutter - the class is the cutter, and objects are the cookies.

```python
# A simple class (the old way)
class Team:
    def __init__(self, key, name, description):
        self.key = key
        self.name = name
        self.description = description

    def __repr__(self):
        return f"Team(key='{self.key}', name='{self.name}')"

    def __eq__(self, other):
        return (self.key == other.key and
                self.name == other.name and
                self.description == other.description)

# Creating an object (instance) of the class
dev_team = Team(key="dev", name="Developer", description="Dev team")
print(dev_team)  # Team(key='dev', name='Developer')
```

### The Problem with Regular Classes

You have to write a LOT of boilerplate code:
- `__init__` - Constructor to set attributes
- `__repr__` - String representation for debugging
- `__eq__` - Equality comparison
- `__hash__` - If you want to use it in sets/dicts

**This is repetitive and error-prone!**

---

## 2. Dataclasses - The Modern Way

### What is a Dataclass?

A **dataclass** is a decorator that automatically generates the boilerplate methods for you.

```python
from dataclasses import dataclass

# Same class, but with dataclass (the modern way)
@dataclass
class Team:
    key: str
    name: str
    description: str

# That's it! Python auto-generates __init__, __repr__, __eq__ for you!
dev_team = Team(key="dev", name="Developer", description="Dev team")
print(dev_team)  # Team(key='dev', name='Developer', description='Dev team')
```

### What @dataclass Generates Automatically

| Method | What it does | Generated? |
|--------|--------------|------------|
| `__init__` | Constructor | ✅ Yes |
| `__repr__` | String representation | ✅ Yes |
| `__eq__` | Equality comparison | ✅ Yes |
| `__hash__` | Hash for sets/dicts | ❌ No (unless frozen=True) |

### Dataclass Options

```python
@dataclass(frozen=True)      # Makes instances immutable (can't change after creation)
@dataclass(order=True)       # Adds comparison methods (<, >, <=, >=)
@dataclass(slots=True)       # Uses __slots__ for memory efficiency (Python 3.10+)
```

### When to Use Dataclasses

```
USE dataclass when:                 DON'T use when:
─────────────────────              ─────────────────────
• Storing data                     • Complex behavior/methods
• Simple data containers           • Inheritance hierarchies
• DTOs (Data Transfer Objects)     • Need full control over __init__
• Configuration objects            • Performance-critical code
```

---

## 3. Type Hints - Declaring Types

### What are Type Hints?

Type hints tell Python (and your IDE) what type a variable should be. They're **optional** but highly recommended.

```python
# Without type hints
def greet(name):
    return f"Hello, {name}"

# With type hints
def greet(name: str) -> str:
    return f"Hello, {name}"
```

### Basic Types

```python
# Primitive types
name: str = "Alice"
age: int = 30
price: float = 19.99
is_active: bool = True

# None type
value: None = None
```

### Collection Types

```python
from typing import List, Dict, Set, Tuple

# Lists - ordered, mutable
names: list[str] = ["Alice", "Bob"]

# Dictionaries - key-value pairs
scores: dict[str, int] = {"Alice": 100, "Bob": 85}

# Sets - unique values
tags: set[str] = {"python", "coding"}

# Tuples - fixed size, immutable
point: tuple[int, int] = (10, 20)
```

### Optional Types (can be None)

```python
from typing import Optional

# These two are equivalent:
name: Optional[str] = None
name: str | None = None  # Python 3.10+ syntax (preferred)
```

### Complex Types

```python
from dataclasses import dataclass

@dataclass
class Team:
    key: str
    name: str

@dataclass
class Config:
    # A list of Team objects
    teams: list[Team]

    # A dictionary mapping string to list of strings
    permissions: dict[str, list[str]]
```

### Why Use Type Hints?

```
Benefits:
─────────
1. IDE Autocomplete    → team.n  [IDE suggests: name]
2. Error Detection     → team.naem  [IDE shows: "naem" not found]
3. Documentation       → Code is self-documenting
4. Refactoring Safety  → IDE can find all usages
```

---

## 4. Default Values and field()

### Simple Default Values

```python
from dataclasses import dataclass

@dataclass
class Team:
    key: str                        # Required (no default)
    name: str                       # Required (no default)
    description: str = ""           # Optional (default: empty string)
    is_active: bool = True          # Optional (default: True)

# Usage:
team1 = Team(key="dev", name="Developer")  # Uses defaults
team2 = Team(key="qa", name="QA", description="Quality team", is_active=False)
```

### The Mutable Default Problem ⚠️

```python
# ❌ WRONG - Don't do this!
@dataclass
class Config:
    teams: list[str] = []  # This will cause bugs!

# Why? All instances share the SAME list!
config1 = Config()
config2 = Config()
config1.teams.append("dev")
print(config2.teams)  # ["dev"] - OOPS! config2 also has "dev"!
```

### The Solution: field(default_factory=...)

```python
from dataclasses import dataclass, field

# ✅ CORRECT - Use field() for mutable defaults
@dataclass
class Config:
    teams: list[str] = field(default_factory=list)  # Creates NEW list each time

# Now each instance gets its own list
config1 = Config()
config2 = Config()
config1.teams.append("dev")
print(config2.teams)  # [] - config2 has its own empty list
```

### Other field() Options

```python
from dataclasses import dataclass, field

@dataclass
class Team:
    key: str
    name: str

    # Field that doesn't appear in __init__
    _internal_id: int = field(init=False, default=0)

    # Field excluded from __repr__
    password: str = field(repr=False, default="secret")

    # Field with custom comparison behavior
    timestamp: float = field(compare=False, default=0.0)
```

### Quick Reference: field() Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `default` | MISSING | Default value |
| `default_factory` | MISSING | Function to create default |
| `init` | True | Include in `__init__`? |
| `repr` | True | Include in `__repr__`? |
| `compare` | True | Include in comparisons? |
| `hash` | None | Include in `__hash__`? |

---

## 5. Validation with __post_init__

### What is __post_init__?

A special method that runs **after** `__init__` completes. Perfect for validation!

```python
from dataclasses import dataclass

@dataclass
class Team:
    key: str
    name: str

    def __post_init__(self):
        # This runs AFTER __init__ sets all the attributes

        # Validate key format
        if not self.key:
            raise ValueError("Key cannot be empty")

        if " " in self.key:
            raise ValueError("Key cannot contain spaces")

        if self.key != self.key.lower():
            raise ValueError("Key must be lowercase")

# Usage:
team = Team(key="dev", name="Developer")  # ✅ Works

team = Team(key="", name="Developer")      # ❌ ValueError: Key cannot be empty
team = Team(key="Dev Team", name="Dev")    # ❌ ValueError: Key cannot contain spaces
team = Team(key="Dev", name="Developer")   # ❌ ValueError: Key must be lowercase
```

### Auto-Transformation in __post_init__

```python
@dataclass
class Team:
    key: str
    name: str

    def __post_init__(self):
        # Auto-fix the key instead of raising error
        self.key = self.key.lower().replace(" ", "-")

# Usage:
team = Team(key="Dev Team", name="Developer")
print(team.key)  # "dev-team" (auto-fixed!)
```

### Validation Pattern

```python
from dataclasses import dataclass

@dataclass
class EnvironmentGroup:
    key: str
    requires_approval: bool = False
    is_critical: bool = False
    notes: str = ""

    def __post_init__(self):
        # Validation 1: Key format
        if not self.key:
            raise ValueError("Environment group key is required")

        # Validation 2: Business rule
        if self.is_critical and not self.requires_approval:
            # Critical environments should require approval
            # Auto-fix instead of error:
            self.requires_approval = True

        # Validation 3: Normalize key
        self.key = self.key.lower().strip()
```

---

## 6. Serialization - To and From JSON

### What is Serialization?

Converting Python objects to a format that can be saved (like JSON) and loaded back.

```
Python Object  ──serialize──►  JSON String  ──save──►  File
Python Object  ◄──deserialize── JSON String  ◄──load──  File
```

### Using asdict()

```python
from dataclasses import dataclass, asdict
import json

@dataclass
class Team:
    key: str
    name: str
    description: str

# Create object
team = Team(key="dev", name="Developer", description="Dev team")

# Convert to dictionary
team_dict = asdict(team)
print(team_dict)
# {'key': 'dev', 'name': 'Developer', 'description': 'Dev team'}

# Convert to JSON string
json_string = json.dumps(team_dict, indent=2)
print(json_string)
# {
#   "key": "dev",
#   "name": "Developer",
#   "description": "Dev team"
# }
```

### Creating from Dictionary

```python
# From dictionary
data = {'key': 'dev', 'name': 'Developer', 'description': 'Dev team'}
team = Team(**data)  # ** unpacks the dictionary

# From JSON string
json_string = '{"key": "dev", "name": "Developer", "description": "Dev team"}'
data = json.loads(json_string)
team = Team(**data)
```

### Custom Serialization Methods

```python
from dataclasses import dataclass, asdict, field
from datetime import datetime
import json

@dataclass
class RBACConfig:
    customer_name: str
    created_at: datetime
    teams: list[Team] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary (for JSON serialization)."""
        return {
            "customer_name": self.customer_name,
            "created_at": self.created_at.isoformat(),  # datetime → string
            "teams": [asdict(t) for t in self.teams]
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "RBACConfig":
        """Create from dictionary."""
        return cls(
            customer_name=data["customer_name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            teams=[Team(**t) for t in data["teams"]]
        )

    @classmethod
    def from_json(cls, json_string: str) -> "RBACConfig":
        """Create from JSON string."""
        data = json.loads(json_string)
        return cls.from_dict(data)
```

### Usage Example

```python
# Create config
config = RBACConfig(
    customer_name="Acme Inc",
    created_at=datetime.now(),
    teams=[
        Team(key="dev", name="Developer", description="Dev team"),
        Team(key="qa", name="QA", description="QA team")
    ]
)

# Save to file
with open("config.json", "w") as f:
    f.write(config.to_json())

# Load from file
with open("config.json", "r") as f:
    loaded_config = RBACConfig.from_json(f.read())
```

---

## 7. Python Packages and __init__.py

### What is a Package?

A **package** is a folder containing Python modules. The `__init__.py` file marks a folder as a package.

```
models/                    ◄── This is a package
├── __init__.py           ◄── Makes it a package (can be empty)
├── team.py               ◄── Module
├── environment.py        ◄── Module
└── permissions.py        ◄── Module
```

### Why __init__.py?

```python
# Without __init__.py:
from models.team import Team           # Works
from models.environment import EnvGroup  # Works
from models import Team                 # ❌ Doesn't work!

# With __init__.py that exports classes:
from models import Team, EnvGroup       # ✅ Works!
```

### What to Put in __init__.py

```python
# models/__init__.py

# Import classes from submodules
from .team import Team
from .environment import EnvironmentGroup
from .permissions import ProjectPermission, EnvironmentPermission
from .config import RBACConfig

# Define what gets exported when someone does "from models import *"
__all__ = [
    "Team",
    "EnvironmentGroup",
    "ProjectPermission",
    "EnvironmentPermission",
    "RBACConfig"
]
```

### Import Patterns

```python
# After setting up __init__.py, you can import like this:

# Import specific classes
from models import Team, RBACConfig

# Import everything (uses __all__)
from models import *

# Import the module itself
import models
team = models.Team(key="dev", name="Developer")
```

### The Dot (.) in Imports

```python
# In models/config.py

# Absolute import (full path from project root)
from models.team import Team

# Relative import (relative to current package)
from .team import Team          # Same folder
from ..utils import helper      # Parent folder (if it exists)
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PYTHON CONCEPTS CHEAT SHEET                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DATACLASS BASICS                                                    │
│  ─────────────────                                                   │
│  from dataclasses import dataclass, field, asdict                   │
│                                                                      │
│  @dataclass                                                          │
│  class MyClass:                                                      │
│      required_field: str                    # No default = required │
│      optional_field: str = "default"        # With default          │
│      list_field: list[str] = field(default_factory=list)  # Lists  │
│                                                                      │
│  TYPE HINTS                                                          │
│  ──────────                                                          │
│  name: str                    # String                               │
│  count: int                   # Integer                              │
│  items: list[str]             # List of strings                     │
│  data: dict[str, int]         # Dict with string keys, int values   │
│  maybe: str | None            # Optional string (can be None)       │
│                                                                      │
│  VALIDATION                                                          │
│  ──────────                                                          │
│  def __post_init__(self):                                           │
│      if not self.key:                                               │
│          raise ValueError("Key required")                           │
│                                                                      │
│  SERIALIZATION                                                       │
│  ─────────────                                                       │
│  asdict(obj)                  # Object → Dictionary                 │
│  json.dumps(dict)             # Dictionary → JSON string            │
│  json.loads(string)           # JSON string → Dictionary            │
│  MyClass(**dict)              # Dictionary → Object                 │
│                                                                      │
│  PACKAGE STRUCTURE                                                   │
│  ─────────────────                                                   │
│  models/                                                             │
│  ├── __init__.py    # from .team import Team                        │
│  └── team.py        # @dataclass class Team: ...                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

After understanding these concepts, you're ready to implement the models:

1. **[DESIGN.md](./DESIGN.md)** - High-level and low-level design
2. **Implementation** - Create the actual model files

Each model file will include lesson comments referencing this document.
