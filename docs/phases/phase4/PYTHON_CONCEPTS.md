# Phase 4: Python Concepts - Validation Patterns

> Deep dive into Python concepts used in the Validation Service

---

## Table of Contents

1. [Enum for Severity Levels](#1-enum-for-severity-levels)
2. [Dataclasses with Default Values](#2-dataclasses-with-default-values)
3. [Properties for Computed Values](#3-properties-for-computed-values)
4. [Regular Expressions](#4-regular-expressions)
5. [Set for Duplicate Detection](#5-set-for-duplicate-detection)
6. [Method Chaining Pattern](#6-method-chaining-pattern)
7. [Optional Types](#7-optional-types)
8. [Quick Reference Card](#8-quick-reference-card)

---

## 1. Enum for Severity Levels

### What is an Enum?

An **Enum** (enumeration) is a set of named constants. It ensures you can only use predefined values, preventing typos and invalid states.

### Why Use Enum for Severity?

```python
# ❌ BAD: Using strings directly
def add_issue(severity: str):
    if severity == "eror":  # Typo! Won't be caught
        ...

# ✅ GOOD: Using Enum
from enum import Enum

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

def add_issue(severity: Severity):
    if severity == Severity.EROR:  # NameError! Caught immediately
        ...
```

### Enum Basics

```python
from enum import Enum

class Severity(Enum):
    ERROR = "error"      # Name = ERROR, Value = "error"
    WARNING = "warning"  # Name = WARNING, Value = "warning"
    INFO = "info"        # Name = INFO, Value = "info"

# Accessing enum members
print(Severity.ERROR)        # Severity.ERROR
print(Severity.ERROR.name)   # "ERROR"
print(Severity.ERROR.value)  # "error"

# Comparing enums
issue_severity = Severity.ERROR
if issue_severity == Severity.ERROR:
    print("This is an error!")

# Iterating over enum
for level in Severity:
    print(level.name, level.value)
# ERROR error
# WARNING warning
# INFO info
```

### Common Pitfalls

```python
# ❌ DON'T compare with string
if severity == "error":  # Won't match Severity.ERROR

# ✅ DO compare with enum member
if severity == Severity.ERROR:  # Correct

# ❌ DON'T use .value unless needed
if severity.value == "error":  # Works but verbose

# ✅ DO use enum directly
if severity == Severity.ERROR:  # Clean
```

---

## 2. Dataclasses with Default Values

### Why Dataclasses for Validation Issues?

Dataclasses automatically generate `__init__`, `__repr__`, and `__eq__` methods, perfect for simple data containers.

### Basic Dataclass

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ValidationIssue:
    severity: Severity           # Required
    code: str                    # Required
    message: str                 # Required
    field: Optional[str] = None  # Optional with default
    suggestion: Optional[str] = None  # Optional with default

# Creating instances
issue1 = ValidationIssue(
    severity=Severity.ERROR,
    code="EMPTY_NAME",
    message="Name is required"
)

issue2 = ValidationIssue(
    severity=Severity.WARNING,
    code="NO_PERMS",
    message="No permissions",
    field="teams[0]",
    suggestion="Add some permissions"
)
```

### Default Factory for Mutable Defaults

```python
from dataclasses import dataclass, field
from typing import List

# ❌ BAD: Mutable default (all instances share same list!)
@dataclass
class BadResult:
    issues: List = []  # Don't do this!

# ✅ GOOD: Use field(default_factory=...)
@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

# Each instance gets its own empty list
r1 = ValidationResult()
r2 = ValidationResult()
r1.issues.append(issue1)
print(len(r2.issues))  # 0 - r2 is unaffected
```

### Adding Methods to Dataclasses

```python
@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_error(self, code: str, message: str, **kwargs):
        """Add an error - custom method."""
        self.issues.append(ValidationIssue(
            severity=Severity.ERROR,
            code=code,
            message=message,
            **kwargs
        ))

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues]
        }
```

---

## 3. Properties for Computed Values

### What is a Property?

A **property** is a method that acts like an attribute. It's computed on access, not stored.

### Why Use Properties?

```python
@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    # ❌ Without property - must call method
    def get_errors(self):
        return [i for i in self.issues if i.severity == Severity.ERROR]

    # Usage: result.get_errors()  # Method call

    # ✅ With property - access like attribute
    @property
    def errors(self):
        return [i for i in self.issues if i.severity == Severity.ERROR]

    # Usage: result.errors  # Looks like attribute

    @property
    def is_valid(self):
        """True if no errors."""
        return len(self.errors) == 0

    @property
    def error_count(self):
        """Number of errors."""
        return len(self.errors)
```

### Usage

```python
result = ValidationResult()
result.add_error("E1", "Error 1")
result.add_warning("W1", "Warning 1")

print(result.is_valid)      # False (has errors)
print(result.error_count)   # 1
print(result.warning_count) # 1
print(result.errors)        # [ValidationIssue(...)]
```

### Property vs Method

| Use Property When... | Use Method When... |
|---------------------|-------------------|
| No arguments needed | Arguments required |
| Feels like an attribute | Performs an action |
| Returns computed value | Has side effects |
| Example: `is_valid` | Example: `add_error(...)` |

---

## 4. Regular Expressions

### Why Regex for Key Validation?

LaunchDarkly keys must match specific patterns. Regex validates this efficiently.

### Basic Pattern Matching

```python
import re

# Define pattern
KEY_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')

# Pattern breakdown:
# ^           - Start of string
# [a-zA-Z0-9._-]  - Allowed characters: letters, numbers, dot, underscore, hyphen
# +           - One or more of the above
# $           - End of string

# Validate keys
def is_valid_key(key: str) -> bool:
    return bool(KEY_PATTERN.match(key))

# Examples
print(is_valid_key("mobile-app"))     # True
print(is_valid_key("my_project.v2"))  # True
print(is_valid_key("has space"))      # False - space not allowed
print(is_valid_key("special@char"))   # False - @ not allowed
print(is_valid_key(""))               # False - empty not allowed
```

### Common Regex Patterns

```python
# Alphanumeric with hyphens (kebab-case)
KEBAB_CASE = re.compile(r'^[a-z][a-z0-9-]*$')

# Email (simplified)
EMAIL = re.compile(r'^[\w.-]+@[\w.-]+\.\w+$')

# Key with dots (namespaced)
NAMESPACED = re.compile(r'^[a-z]+(\.[a-z]+)*$')
```

### Match vs Search

```python
text = "hello-world"

# match() - checks from START of string
re.match(r'hello', text)   # Match! Starts with 'hello'
re.match(r'world', text)   # None! 'world' not at start

# search() - finds pattern ANYWHERE
re.search(r'world', text)  # Match! Found 'world'
re.search(r'xyz', text)    # None! 'xyz' not found
```

---

## 5. Set for Duplicate Detection

### Why Use Set?

A **set** provides O(1) lookup time, perfect for checking if we've seen a value before.

### Duplicate Detection Pattern

```python
def find_duplicates(items: List[str]) -> List[str]:
    """Find duplicate items in a list."""
    seen = set()
    duplicates = []

    for item in items:
        if item in seen:  # O(1) lookup!
            duplicates.append(item)
        else:
            seen.add(item)  # O(1) add!

    return duplicates

# Example
keys = ["dev", "qa", "dev", "admin", "qa"]
print(find_duplicates(keys))  # ["dev", "qa"]
```

### Set vs List for Lookups

```python
# ❌ List - O(n) lookup
seen_list = []
for item in items:
    if item in seen_list:  # Slow for large lists
        ...
    seen_list.append(item)

# ✅ Set - O(1) lookup
seen_set = set()
for item in items:
    if item in seen_set:  # Fast!
        ...
    seen_set.add(item)
```

### Set Operations

```python
valid_teams = {"dev", "qa", "admin"}
matrix_teams = {"dev", "qa", "unknown"}

# Find teams in matrix but not in valid list
unknown = matrix_teams - valid_teams
print(unknown)  # {"unknown"}

# Find teams in both
common = matrix_teams & valid_teams
print(common)  # {"dev", "qa"}

# Find all unique teams
all_teams = matrix_teams | valid_teams
print(all_teams)  # {"dev", "qa", "admin", "unknown"}
```

---

## 6. Method Chaining Pattern

### The Validation Chain Pattern

Each validation method adds issues to the same result object. This is a form of method chaining.

```python
class ConfigValidator:
    def validate(self) -> ValidationResult:
        result = ValidationResult()

        # Each method modifies result in place
        self._validate_required_fields(result)
        self._validate_key_formats(result)
        self._validate_teams(result)
        self._validate_env_groups(result)
        self._validate_project_matrix(result)
        self._validate_env_matrix(result)
        self._validate_permission_coverage(result)

        return result

    def _validate_required_fields(self, result: ValidationResult):
        """Adds issues to result - doesn't return."""
        if not self.customer_name:
            result.add_error("EMPTY_CUSTOMER_NAME", ...)

    def _validate_teams(self, result: ValidationResult):
        """Adds issues to result - doesn't return."""
        for team in self.teams:
            if not team.key:
                result.add_error("EMPTY_TEAM_KEY", ...)
```

### Why This Pattern?

1. **Single result object** - All issues collected in one place
2. **Independent checks** - Each method can run independently
3. **Easy to extend** - Add new validation by adding new method
4. **Easy to test** - Test each validation method separately

---

## 7. Optional Types

### What is Optional?

`Optional[T]` means "either T or None". It makes nullable values explicit.

```python
from typing import Optional

@dataclass
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    field: Optional[str] = None      # Can be str or None
    suggestion: Optional[str] = None  # Can be str or None

# Both are valid:
issue1 = ValidationIssue(Severity.ERROR, "E1", "Error")
issue2 = ValidationIssue(
    Severity.ERROR, "E2", "Error",
    field="customer_name",
    suggestion="Enter a name"
)
```

### Handling Optional Values

```python
def format_issue(issue: ValidationIssue) -> str:
    """Format issue for display."""
    msg = f"[{issue.severity.name}] {issue.message}"

    # Check if optional field is present
    if issue.field:
        msg += f" (field: {issue.field})"

    if issue.suggestion:
        msg += f"\n  Suggestion: {issue.suggestion}"

    return msg
```

### Optional vs Default

```python
# Optional - value can be None
field: Optional[str] = None

# Default - value has a default but isn't Optional
enabled: bool = True

# Both - optional with non-None default
timeout: Optional[int] = 30  # Can be set to None explicitly
```

---

## 8. Quick Reference Card

### Validation Service Patterns

```python
# Enum for type-safe constants
class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"

# Dataclass with defaults
@dataclass
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    field: Optional[str] = None

# Mutable default with factory
@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

# Property for computed value
@property
def is_valid(self) -> bool:
    return len(self.errors) == 0

# Regex for format validation
KEY_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
is_valid = bool(KEY_PATTERN.match(key))

# Set for duplicate detection
seen = set()
if item in seen:  # O(1)
    # duplicate!
seen.add(item)
```

### Common Validation Checks

```python
# Empty string check
if not value or not value.strip():
    result.add_error("EMPTY_VALUE", ...)

# Format validation
if not KEY_PATTERN.match(value):
    result.add_error("INVALID_FORMAT", ...)

# Length validation
if len(value) > MAX_LENGTH:
    result.add_error("TOO_LONG", ...)

# Duplicate detection
if value in seen_values:
    result.add_error("DUPLICATE", ...)

# Reference validation
if value not in valid_values:
    result.add_warning("UNKNOWN_REF", ...)
```

---

## Next Steps

Now that you understand the validation patterns, proceed to:

1. [DESIGN.md](./DESIGN.md) - See how these concepts are applied
2. [README.md](./README.md) - Quick reference for Phase 4
3. Write tests in `tests/test_validation.py`

---

## Navigation

| Previous | Up | Next |
|----------|------|------|
| [Phase 3 Concepts](../phase3/PYTHON_CONCEPTS.md) | [Phase 4 Design](./DESIGN.md) | [Phase 5](../phase5/) |
