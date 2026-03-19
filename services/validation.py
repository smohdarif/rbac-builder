"""
Validation Service
==================

Validates RBAC configurations before deployment to catch errors early.

LESSON 34: Validation Pattern
=============================
Validation is crucial before deploying to external APIs. We validate:
1. Required fields are present
2. Data formats are correct
3. References are valid (e.g., team exists)
4. No duplicates or conflicts
5. LaunchDarkly-specific constraints

This prevents failed API calls and helps users fix issues before deployment.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import re


# =============================================================================
# LESSON 35: Validation Severity Levels
# =============================================================================
# Not all validation issues are equal:
#   - ERROR: Must fix before deployment (will cause API failure)
#   - WARNING: Should review, but won't block deployment
#   - INFO: Informational, might be intentional

class Severity(Enum):
    """Severity level for validation issues."""
    ERROR = "error"      # Blocks deployment
    WARNING = "warning"  # Should review
    INFO = "info"        # Informational


# =============================================================================
# LESSON 36: ValidationIssue - A Single Problem
# =============================================================================

@dataclass
class ValidationIssue:
    """
    Represents a single validation issue.

    Attributes:
        severity: ERROR, WARNING, or INFO
        code: Machine-readable error code (e.g., "EMPTY_TEAM_NAME")
        message: Human-readable description
        field: Which field has the issue (optional)
        suggestion: How to fix it (optional)

    Example:
        >>> issue = ValidationIssue(
        ...     severity=Severity.ERROR,
        ...     code="EMPTY_CUSTOMER_NAME",
        ...     message="Customer name is required",
        ...     field="customer_name",
        ...     suggestion="Enter a customer name in the sidebar"
        ... )
    """
    severity: Severity
    code: str
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "suggestion": self.suggestion
        }


# =============================================================================
# LESSON 37: ValidationResult - Collection of Issues
# =============================================================================

@dataclass
class ValidationResult:
    """
    Container for all validation issues.

    Attributes:
        issues: List of all validation issues found

    Properties:
        is_valid: True if no ERROR-level issues
        errors: List of ERROR issues only
        warnings: List of WARNING issues only
        error_count: Number of errors
        warning_count: Number of warnings

    Example:
        >>> result = ValidationResult()
        >>> result.add_error("EMPTY_NAME", "Name is required")
        >>> result.add_warning("NO_PERMISSIONS", "Team has no permissions")
        >>> print(result.is_valid)
        False
    """
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_error(
        self,
        code: str,
        message: str,
        field: Optional[str] = None,
        suggestion: Optional[str] = None
    ) -> None:
        """Add an ERROR-level issue."""
        self.issues.append(ValidationIssue(
            severity=Severity.ERROR,
            code=code,
            message=message,
            field=field,
            suggestion=suggestion
        ))

    def add_warning(
        self,
        code: str,
        message: str,
        field: Optional[str] = None,
        suggestion: Optional[str] = None
    ) -> None:
        """Add a WARNING-level issue."""
        self.issues.append(ValidationIssue(
            severity=Severity.WARNING,
            code=code,
            message=message,
            field=field,
            suggestion=suggestion
        ))

    def add_info(
        self,
        code: str,
        message: str,
        field: Optional[str] = None,
        suggestion: Optional[str] = None
    ) -> None:
        """Add an INFO-level issue."""
        self.issues.append(ValidationIssue(
            severity=Severity.INFO,
            code=code,
            message=message,
            field=field,
            suggestion=suggestion
        ))

    @property
    def is_valid(self) -> bool:
        """True if no ERROR-level issues exist."""
        return len(self.errors) == 0

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get all ERROR-level issues."""
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get all WARNING-level issues."""
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def infos(self) -> List[ValidationIssue]:
        """Get all INFO-level issues."""
        return [i for i in self.issues if i.severity == Severity.INFO]

    @property
    def error_count(self) -> int:
        """Number of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Number of warnings."""
        return len(self.warnings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [issue.to_dict() for issue in self.issues]
        }


# =============================================================================
# LESSON 38: ConfigValidator - The Main Validator
# =============================================================================

class ConfigValidator:
    """
    Validates RBAC configuration data.

    This validator checks:
    1. Required fields (customer_name, project_key, etc.)
    2. Key formats (LaunchDarkly constraints)
    3. Duplicate detection (team keys, role keys)
    4. Reference validity (teams in matrix exist)
    5. Permission coverage (teams with no permissions)
    6. Environment consistency

    Usage:
        >>> validator = ConfigValidator(
        ...     customer_name="Acme",
        ...     project_key="mobile-app",
        ...     teams_df=teams_df,
        ...     env_groups_df=env_groups_df,
        ...     project_matrix_df=project_matrix_df,
        ...     env_matrix_df=env_matrix_df
        ... )
        >>> result = validator.validate()
        >>> if not result.is_valid:
        ...     for error in result.errors:
        ...         print(f"ERROR: {error.message}")
    """

    # LaunchDarkly key constraints
    KEY_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    KEY_MAX_LENGTH = 256
    NAME_MAX_LENGTH = 256

    def __init__(
        self,
        customer_name: str,
        project_key: str,
        teams_df,           # pandas DataFrame
        env_groups_df,      # pandas DataFrame
        project_matrix_df,  # pandas DataFrame
        env_matrix_df,      # pandas DataFrame
    ):
        """
        Initialize the validator.

        Args:
            customer_name: Customer identifier
            project_key: LaunchDarkly project key
            teams_df: DataFrame with team definitions
            env_groups_df: DataFrame with environment groups
            project_matrix_df: DataFrame with project-level permissions
            env_matrix_df: DataFrame with environment-level permissions
        """
        self.customer_name = customer_name
        self.project_key = project_key
        self.teams_df = teams_df
        self.env_groups_df = env_groups_df
        self.project_matrix_df = project_matrix_df
        self.env_matrix_df = env_matrix_df

    def validate(self) -> ValidationResult:
        """
        Run all validation checks.

        Returns:
            ValidationResult containing all issues found
        """
        result = ValidationResult()

        # =================================================================
        # LESSON 39: Chaining Validation Methods
        # =================================================================
        # We break validation into small, focused methods.
        # Each method adds issues to the result object.
        # This makes the code easier to read, test, and maintain.

        self._validate_required_fields(result)
        self._validate_key_formats(result)
        self._validate_teams(result)
        self._validate_env_groups(result)
        self._validate_project_matrix(result)
        self._validate_env_matrix(result)
        self._validate_permission_coverage(result)

        return result

    # =========================================================================
    # REQUIRED FIELDS
    # =========================================================================

    def _validate_required_fields(self, result: ValidationResult) -> None:
        """Check that required fields are present and non-empty."""

        # Customer name
        if not self.customer_name or not self.customer_name.strip():
            result.add_error(
                code="EMPTY_CUSTOMER_NAME",
                message="Customer name is required",
                field="customer_name",
                suggestion="Enter a customer name in the sidebar"
            )

        # Project key
        if not self.project_key or not self.project_key.strip():
            result.add_error(
                code="EMPTY_PROJECT_KEY",
                message="Project key is required",
                field="project_key",
                suggestion="Enter a project key in the Setup tab"
            )

        # Teams
        if self.teams_df is None or self.teams_df.empty:
            result.add_error(
                code="NO_TEAMS",
                message="At least one team is required",
                field="teams",
                suggestion="Add teams in the Setup tab"
            )

        # Environment groups
        if self.env_groups_df is None or self.env_groups_df.empty:
            result.add_error(
                code="NO_ENV_GROUPS",
                message="At least one environment group is required",
                field="env_groups",
                suggestion="Add environment groups in the Setup tab"
            )

    # =========================================================================
    # KEY FORMAT VALIDATION
    # =========================================================================

    def _validate_key_formats(self, result: ValidationResult) -> None:
        """Validate that keys match LaunchDarkly's format requirements."""

        # Project key format
        if self.project_key:
            if not self.KEY_PATTERN.match(self.project_key):
                result.add_error(
                    code="INVALID_PROJECT_KEY_FORMAT",
                    message=f"Project key '{self.project_key}' contains invalid characters",
                    field="project_key",
                    suggestion="Use only letters, numbers, dots, underscores, and hyphens"
                )
            if len(self.project_key) > self.KEY_MAX_LENGTH:
                result.add_error(
                    code="PROJECT_KEY_TOO_LONG",
                    message=f"Project key exceeds {self.KEY_MAX_LENGTH} characters",
                    field="project_key",
                    suggestion=f"Shorten to {self.KEY_MAX_LENGTH} characters or less"
                )

    # =========================================================================
    # TEAMS VALIDATION
    # =========================================================================

    def _validate_teams(self, result: ValidationResult) -> None:
        """Validate team definitions."""
        if self.teams_df is None or self.teams_df.empty:
            return

        key_col = "Key" if "Key" in self.teams_df.columns else "key"
        name_col = "Name" if "Name" in self.teams_df.columns else "name"

        seen_keys: Set[str] = set()
        seen_names: Set[str] = set()

        for idx, row in self.teams_df.iterrows():
            team_key = row.get(key_col)
            team_name = row.get(name_col)

            # Check for empty key
            if not team_key or (isinstance(team_key, str) and not team_key.strip()):
                result.add_error(
                    code="EMPTY_TEAM_KEY",
                    message=f"Team at row {idx + 1} has no key",
                    field=f"teams[{idx}].key",
                    suggestion="Enter a unique key for each team"
                )
                continue

            # Check key format
            if not self.KEY_PATTERN.match(str(team_key)):
                result.add_error(
                    code="INVALID_TEAM_KEY_FORMAT",
                    message=f"Team key '{team_key}' contains invalid characters",
                    field=f"teams[{idx}].key",
                    suggestion="Use only letters, numbers, dots, underscores, and hyphens"
                )

            # Check for duplicate keys
            if team_key in seen_keys:
                result.add_error(
                    code="DUPLICATE_TEAM_KEY",
                    message=f"Duplicate team key: '{team_key}'",
                    field=f"teams[{idx}].key",
                    suggestion="Each team must have a unique key"
                )
            seen_keys.add(team_key)

            # Check for duplicate names
            if team_name and team_name in seen_names:
                result.add_warning(
                    code="DUPLICATE_TEAM_NAME",
                    message=f"Duplicate team name: '{team_name}'",
                    field=f"teams[{idx}].name",
                    suggestion="Consider using unique names for clarity"
                )
            if team_name:
                seen_names.add(team_name)

    # =========================================================================
    # ENVIRONMENT GROUPS VALIDATION
    # =========================================================================

    def _validate_env_groups(self, result: ValidationResult) -> None:
        """Validate environment group definitions."""
        if self.env_groups_df is None or self.env_groups_df.empty:
            return

        key_col = "Key" if "Key" in self.env_groups_df.columns else "key"

        seen_keys: Set[str] = set()

        for idx, row in self.env_groups_df.iterrows():
            env_key = row.get(key_col)

            # Check for empty key
            if not env_key or (isinstance(env_key, str) and not env_key.strip()):
                result.add_error(
                    code="EMPTY_ENV_KEY",
                    message=f"Environment group at row {idx + 1} has no key",
                    field=f"env_groups[{idx}].key",
                    suggestion="Enter a unique key for each environment group"
                )
                continue

            # Check for duplicate keys
            if env_key in seen_keys:
                result.add_error(
                    code="DUPLICATE_ENV_KEY",
                    message=f"Duplicate environment key: '{env_key}'",
                    field=f"env_groups[{idx}].key",
                    suggestion="Each environment group must have a unique key"
                )
            seen_keys.add(env_key)

    # =========================================================================
    # PROJECT MATRIX VALIDATION
    # =========================================================================

    def _validate_project_matrix(self, result: ValidationResult) -> None:
        """Validate project-level permission matrix."""
        if self.project_matrix_df is None or self.project_matrix_df.empty:
            result.add_warning(
                code="EMPTY_PROJECT_MATRIX",
                message="No project-level permissions defined",
                field="project_matrix",
                suggestion="Set project permissions in the Design Matrix tab"
            )
            return

        # Get valid team names
        name_col = "Name" if "Name" in self.teams_df.columns else "name"
        valid_team_names = set(self.teams_df[name_col].dropna().tolist())

        # Check each row
        for idx, row in self.project_matrix_df.iterrows():
            team_name = row.get("Team")

            # Check team exists
            if team_name and team_name not in valid_team_names:
                result.add_warning(
                    code="UNKNOWN_TEAM_IN_MATRIX",
                    message=f"Team '{team_name}' in matrix not found in Teams list",
                    field=f"project_matrix[{idx}].Team",
                    suggestion="Click 'Regenerate Matrix from Setup' to sync"
                )

    # =========================================================================
    # ENVIRONMENT MATRIX VALIDATION
    # =========================================================================

    def _validate_env_matrix(self, result: ValidationResult) -> None:
        """Validate environment-level permission matrix."""
        if self.env_matrix_df is None or self.env_matrix_df.empty:
            result.add_warning(
                code="EMPTY_ENV_MATRIX",
                message="No environment-level permissions defined",
                field="env_matrix",
                suggestion="Set environment permissions in the Design Matrix tab"
            )
            return

        # Get valid team names and env keys
        name_col = "Name" if "Name" in self.teams_df.columns else "name"
        valid_team_names = set(self.teams_df[name_col].dropna().tolist())

        key_col = "Key" if "Key" in self.env_groups_df.columns else "key"
        valid_env_keys = set(self.env_groups_df[key_col].dropna().tolist())

        # Check each row
        for idx, row in self.env_matrix_df.iterrows():
            team_name = row.get("Team")
            env_key = row.get("Environment")

            # Check team exists
            if team_name and team_name not in valid_team_names:
                result.add_warning(
                    code="UNKNOWN_TEAM_IN_ENV_MATRIX",
                    message=f"Team '{team_name}' in env matrix not found in Teams list",
                    field=f"env_matrix[{idx}].Team",
                    suggestion="Click 'Regenerate Matrix from Setup' to sync"
                )

            # Check environment exists
            if env_key and env_key not in valid_env_keys:
                result.add_warning(
                    code="UNKNOWN_ENV_IN_MATRIX",
                    message=f"Environment '{env_key}' not found in Environment Groups",
                    field=f"env_matrix[{idx}].Environment",
                    suggestion="Click 'Regenerate Matrix from Setup' to sync"
                )

    # =========================================================================
    # PERMISSION COVERAGE
    # =========================================================================

    def _validate_permission_coverage(self, result: ValidationResult) -> None:
        """Check that teams have meaningful permissions."""
        if self.teams_df is None or self.teams_df.empty:
            return

        name_col = "Name" if "Name" in self.teams_df.columns else "name"

        for _, row in self.teams_df.iterrows():
            team_name = row.get(name_col)
            if not team_name:
                continue

            has_project_perms = self._team_has_project_permissions(team_name)
            has_env_perms = self._team_has_env_permissions(team_name)

            if not has_project_perms and not has_env_perms:
                result.add_warning(
                    code="TEAM_NO_PERMISSIONS",
                    message=f"Team '{team_name}' has no permissions assigned",
                    field=f"teams.{team_name}",
                    suggestion="Assign permissions in the Design Matrix tab or remove the team"
                )

    def _team_has_project_permissions(self, team_name: str) -> bool:
        """Check if team has any project-level permissions."""
        if self.project_matrix_df is None or self.project_matrix_df.empty:
            return False

        team_rows = self.project_matrix_df[
            self.project_matrix_df["Team"] == team_name
        ]

        if team_rows.empty:
            return False

        # Check if any permission column is True
        for col in team_rows.columns:
            if col != "Team" and team_rows[col].any():
                return True

        return False

    def _team_has_env_permissions(self, team_name: str) -> bool:
        """Check if team has any environment-level permissions."""
        if self.env_matrix_df is None or self.env_matrix_df.empty:
            return False

        team_rows = self.env_matrix_df[
            self.env_matrix_df["Team"] == team_name
        ]

        if team_rows.empty:
            return False

        # Check if any permission column is True
        for col in team_rows.columns:
            if col not in ["Team", "Environment"] and team_rows[col].any():
                return True

        return False


# =============================================================================
# LESSON 40: Convenience Function
# =============================================================================

def validate_from_session(
    customer_name: str,
    project_key: str,
    session_state
) -> ValidationResult:
    """
    Validate configuration directly from Streamlit session state.

    This is a convenience function for use in the Streamlit app.

    Args:
        customer_name: Customer identifier
        project_key: Project key
        session_state: Streamlit session state object

    Returns:
        ValidationResult with all issues found
    """
    validator = ConfigValidator(
        customer_name=customer_name,
        project_key=project_key,
        teams_df=session_state.get("teams"),
        env_groups_df=session_state.get("env_groups"),
        project_matrix_df=session_state.get("project_matrix"),
        env_matrix_df=session_state.get("env_matrix")
    )
    return validator.validate()


# =============================================================================
# Module test
# =============================================================================
if __name__ == "__main__":
    import pandas as pd

    print("=== ConfigValidator Test ===\n")

    # Test with valid data
    teams_df = pd.DataFrame({
        "Key": ["dev", "qa"],
        "Name": ["Developer", "QA Engineer"],
        "Description": ["Dev team", "QA team"]
    })

    env_groups_df = pd.DataFrame({
        "Key": ["Test", "Production"],
        "Critical": [False, True]
    })

    project_matrix_df = pd.DataFrame({
        "Team": ["Developer", "QA Engineer"],
        "Create Flags": [True, False],
        "View Project": [True, True]
    })

    env_matrix_df = pd.DataFrame({
        "Team": ["Developer", "Developer"],
        "Environment": ["Test", "Production"],
        "Update Targeting": [True, False]
    })

    validator = ConfigValidator(
        customer_name="Test Corp",
        project_key="test-project",
        teams_df=teams_df,
        env_groups_df=env_groups_df,
        project_matrix_df=project_matrix_df,
        env_matrix_df=env_matrix_df
    )

    result = validator.validate()

    print(f"Is Valid: {result.is_valid}")
    print(f"Errors: {result.error_count}")
    print(f"Warnings: {result.warning_count}")

    if result.issues:
        print("\nIssues found:")
        for issue in result.issues:
            print(f"  [{issue.severity.value.upper()}] {issue.message}")

    # Test with invalid data
    print("\n--- Testing with invalid data ---\n")

    invalid_validator = ConfigValidator(
        customer_name="",  # Empty!
        project_key="test project",  # Has space!
        teams_df=pd.DataFrame({"Key": ["dev", "dev"], "Name": ["Dev", "Dev"]}),  # Duplicates!
        env_groups_df=env_groups_df,
        project_matrix_df=project_matrix_df,
        env_matrix_df=env_matrix_df
    )

    invalid_result = invalid_validator.validate()

    print(f"Is Valid: {invalid_result.is_valid}")
    print(f"Errors: {invalid_result.error_count}")
    print(f"Warnings: {invalid_result.warning_count}")

    if invalid_result.issues:
        print("\nIssues found:")
        for issue in invalid_result.issues:
            print(f"  [{issue.severity.value.upper()}] {issue.code}: {issue.message}")
            if issue.suggestion:
                print(f"      Suggestion: {issue.suggestion}")
