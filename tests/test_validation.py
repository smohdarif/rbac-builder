"""
Tests for Phase 4: Validation Service
=====================================

Tests for ConfigValidator, ValidationResult, and validation rules.

Run with: pytest tests/test_validation.py -v
"""

import pytest
import pandas as pd

from services import (
    ConfigValidator,
    ValidationResult,
    ValidationIssue,
    Severity,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def valid_teams_df():
    """Create valid teams DataFrame."""
    return pd.DataFrame({
        "Key": ["dev", "qa", "admin"],
        "Name": ["Developer", "QA Engineer", "Administrator"],
        "Description": ["Dev team", "QA team", "Admin team"]
    })


@pytest.fixture
def valid_env_groups_df():
    """Create valid environment groups DataFrame."""
    return pd.DataFrame({
        "Key": ["Test", "Production"],
        "Critical": [False, True]
    })


@pytest.fixture
def valid_project_matrix_df():
    """Create valid project matrix DataFrame."""
    return pd.DataFrame({
        "Team": ["Developer", "QA Engineer", "Administrator"],
        "Create Flags": [True, False, True],
        "Update Flags": [True, True, True],
        "View Project": [True, True, True]
    })


@pytest.fixture
def valid_env_matrix_df():
    """Create valid environment matrix DataFrame."""
    return pd.DataFrame({
        "Team": ["Developer", "Developer", "QA Engineer", "QA Engineer"],
        "Environment": ["Test", "Production", "Test", "Production"],
        "Update Targeting": [True, False, True, False],
        "Review Changes": [False, False, True, True]
    })


@pytest.fixture
def valid_validator(
    valid_teams_df,
    valid_env_groups_df,
    valid_project_matrix_df,
    valid_env_matrix_df
):
    """Create a validator with valid data."""
    return ConfigValidator(
        customer_name="Test Corp",
        project_key="test-project",
        teams_df=valid_teams_df,
        env_groups_df=valid_env_groups_df,
        project_matrix_df=valid_project_matrix_df,
        env_matrix_df=valid_env_matrix_df
    )


# =============================================================================
# ValidationResult Tests
# =============================================================================

class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_empty_result_is_valid(self):
        """Test that empty result is valid."""
        result = ValidationResult()

        assert result.is_valid is True
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_add_error(self):
        """Test adding an error."""
        result = ValidationResult()
        result.add_error("TEST_ERROR", "This is an error")

        assert result.is_valid is False
        assert result.error_count == 1
        assert result.errors[0].code == "TEST_ERROR"

    def test_add_warning(self):
        """Test adding a warning."""
        result = ValidationResult()
        result.add_warning("TEST_WARNING", "This is a warning")

        assert result.is_valid is True  # Warnings don't affect validity
        assert result.warning_count == 1
        assert result.warnings[0].code == "TEST_WARNING"

    def test_add_error_with_details(self):
        """Test adding error with field and suggestion."""
        result = ValidationResult()
        result.add_error(
            code="FIELD_ERROR",
            message="Field is invalid",
            field="customer_name",
            suggestion="Enter a valid name"
        )

        issue = result.errors[0]
        assert issue.field == "customer_name"
        assert issue.suggestion == "Enter a valid name"

    def test_to_dict(self):
        """Test serialization to dict."""
        result = ValidationResult()
        result.add_error("E1", "Error 1")
        result.add_warning("W1", "Warning 1")

        data = result.to_dict()

        assert data["is_valid"] is False
        assert data["error_count"] == 1
        assert data["warning_count"] == 1
        assert len(data["issues"]) == 2


# =============================================================================
# ValidationIssue Tests
# =============================================================================

class TestValidationIssue:
    """Tests for ValidationIssue class."""

    def test_create_issue(self):
        """Test creating a validation issue."""
        issue = ValidationIssue(
            severity=Severity.ERROR,
            code="TEST_CODE",
            message="Test message"
        )

        assert issue.severity == Severity.ERROR
        assert issue.code == "TEST_CODE"
        assert issue.message == "Test message"
        assert issue.field is None
        assert issue.suggestion is None

    def test_to_dict(self):
        """Test issue serialization."""
        issue = ValidationIssue(
            severity=Severity.WARNING,
            code="WARN",
            message="Warning",
            field="test_field",
            suggestion="Fix it"
        )

        data = issue.to_dict()

        assert data["severity"] == "warning"
        assert data["code"] == "WARN"
        assert data["field"] == "test_field"


# =============================================================================
# Required Fields Validation Tests
# =============================================================================

class TestRequiredFieldsValidation:
    """Tests for required field validation."""

    def test_empty_customer_name(self, valid_teams_df, valid_env_groups_df):
        """Test that empty customer name causes error."""
        validator = ConfigValidator(
            customer_name="",
            project_key="test",
            teams_df=valid_teams_df,
            env_groups_df=valid_env_groups_df,
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        assert result.is_valid is False
        error_codes = [e.code for e in result.errors]
        assert "EMPTY_CUSTOMER_NAME" in error_codes

    def test_whitespace_customer_name(self, valid_teams_df, valid_env_groups_df):
        """Test that whitespace-only customer name causes error."""
        validator = ConfigValidator(
            customer_name="   ",
            project_key="test",
            teams_df=valid_teams_df,
            env_groups_df=valid_env_groups_df,
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        assert result.is_valid is False
        error_codes = [e.code for e in result.errors]
        assert "EMPTY_CUSTOMER_NAME" in error_codes

    def test_empty_project_key(self, valid_teams_df, valid_env_groups_df):
        """Test that empty project key causes error."""
        validator = ConfigValidator(
            customer_name="Test",
            project_key="",
            teams_df=valid_teams_df,
            env_groups_df=valid_env_groups_df,
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        assert result.is_valid is False
        error_codes = [e.code for e in result.errors]
        assert "EMPTY_PROJECT_KEY" in error_codes

    def test_no_teams(self, valid_env_groups_df):
        """Test that empty teams causes error."""
        validator = ConfigValidator(
            customer_name="Test",
            project_key="test",
            teams_df=pd.DataFrame(),
            env_groups_df=valid_env_groups_df,
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        assert result.is_valid is False
        error_codes = [e.code for e in result.errors]
        assert "NO_TEAMS" in error_codes


# =============================================================================
# Key Format Validation Tests
# =============================================================================

class TestKeyFormatValidation:
    """Tests for key format validation."""

    def test_project_key_with_space(self, valid_teams_df, valid_env_groups_df):
        """Test that project key with space causes error."""
        validator = ConfigValidator(
            customer_name="Test",
            project_key="test project",  # Has space
            teams_df=valid_teams_df,
            env_groups_df=valid_env_groups_df,
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        assert result.is_valid is False
        error_codes = [e.code for e in result.errors]
        assert "INVALID_PROJECT_KEY_FORMAT" in error_codes

    def test_project_key_with_special_chars(self, valid_teams_df, valid_env_groups_df):
        """Test that project key with special chars causes error."""
        validator = ConfigValidator(
            customer_name="Test",
            project_key="test@project!",  # Has @ and !
            teams_df=valid_teams_df,
            env_groups_df=valid_env_groups_df,
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        assert result.is_valid is False
        error_codes = [e.code for e in result.errors]
        assert "INVALID_PROJECT_KEY_FORMAT" in error_codes

    def test_valid_project_key_formats(self, valid_teams_df, valid_env_groups_df):
        """Test valid project key formats."""
        valid_keys = ["mobile-app", "web_platform", "project.v2", "MyProject123"]

        for key in valid_keys:
            validator = ConfigValidator(
                customer_name="Test",
                project_key=key,
                teams_df=valid_teams_df,
                env_groups_df=valid_env_groups_df,
                project_matrix_df=pd.DataFrame(),
                env_matrix_df=pd.DataFrame()
            )
            result = validator.validate()

            # Should not have format errors (may have other warnings)
            error_codes = [e.code for e in result.errors]
            assert "INVALID_PROJECT_KEY_FORMAT" not in error_codes, f"Key '{key}' should be valid"


# =============================================================================
# Duplicate Detection Tests
# =============================================================================

class TestDuplicateDetection:
    """Tests for duplicate key detection."""

    def test_duplicate_team_key(self, valid_env_groups_df):
        """Test that duplicate team keys cause error."""
        teams_df = pd.DataFrame({
            "Key": ["dev", "qa", "dev"],  # "dev" appears twice
            "Name": ["Developer", "QA", "Developer 2"],
            "Description": ["", "", ""]
        })

        validator = ConfigValidator(
            customer_name="Test",
            project_key="test",
            teams_df=teams_df,
            env_groups_df=valid_env_groups_df,
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        assert result.is_valid is False
        error_codes = [e.code for e in result.errors]
        assert "DUPLICATE_TEAM_KEY" in error_codes

    def test_duplicate_env_key(self, valid_teams_df):
        """Test that duplicate env keys cause error."""
        env_groups_df = pd.DataFrame({
            "Key": ["test", "test"],  # Duplicate
            "Critical": [False, True]
        })

        validator = ConfigValidator(
            customer_name="Test",
            project_key="test",
            teams_df=valid_teams_df,
            env_groups_df=env_groups_df,
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        assert result.is_valid is False
        error_codes = [e.code for e in result.errors]
        assert "DUPLICATE_ENV_KEY" in error_codes


# =============================================================================
# Reference Validation Tests
# =============================================================================

class TestReferenceValidation:
    """Tests for reference validation."""

    def test_unknown_team_in_matrix(
        self,
        valid_teams_df,
        valid_env_groups_df
    ):
        """Test that unknown team in matrix causes warning."""
        project_matrix_df = pd.DataFrame({
            "Team": ["Developer", "Unknown Team"],  # Unknown Team not in teams_df
            "Create Flags": [True, True],
            "View Project": [True, True]
        })

        validator = ConfigValidator(
            customer_name="Test",
            project_key="test",
            teams_df=valid_teams_df,
            env_groups_df=valid_env_groups_df,
            project_matrix_df=project_matrix_df,
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        warning_codes = [w.code for w in result.warnings]
        assert "UNKNOWN_TEAM_IN_MATRIX" in warning_codes


# =============================================================================
# Permission Coverage Tests
# =============================================================================

class TestPermissionCoverage:
    """Tests for permission coverage validation."""

    def test_team_with_no_permissions_warning(
        self,
        valid_env_groups_df
    ):
        """Test that team with no permissions causes warning."""
        # Teams where "Admin" has no permissions anywhere
        teams_df = pd.DataFrame({
            "Key": ["dev", "admin"],
            "Name": ["Developer", "Admin"],
            "Description": ["", ""]
        })

        project_matrix_df = pd.DataFrame({
            "Team": ["Developer", "Admin"],
            "Create Flags": [True, False],
            "View Project": [True, False]  # Admin has all False
        })

        env_matrix_df = pd.DataFrame({
            "Team": ["Developer", "Developer"],
            "Environment": ["Test", "Production"],
            "Update Targeting": [True, False]
            # Admin not in env_matrix at all
        })

        validator = ConfigValidator(
            customer_name="Test",
            project_key="test",
            teams_df=teams_df,
            env_groups_df=valid_env_groups_df,
            project_matrix_df=project_matrix_df,
            env_matrix_df=env_matrix_df
        )
        result = validator.validate()

        warning_codes = [w.code for w in result.warnings]
        assert "TEAM_NO_PERMISSIONS" in warning_codes


# =============================================================================
# Full Validation Tests
# =============================================================================

class TestFullValidation:
    """Tests for complete validation flow."""

    def test_valid_config_passes(self, valid_validator):
        """Test that valid config passes validation."""
        result = valid_validator.validate()

        assert result.is_valid is True
        assert result.error_count == 0

    def test_multiple_errors(self):
        """Test that multiple errors are collected."""
        validator = ConfigValidator(
            customer_name="",  # Error 1
            project_key="has space",  # Error 2
            teams_df=pd.DataFrame(),  # Error 3
            env_groups_df=pd.DataFrame(),  # Error 4
            project_matrix_df=pd.DataFrame(),
            env_matrix_df=pd.DataFrame()
        )
        result = validator.validate()

        assert result.is_valid is False
        assert result.error_count >= 3  # Multiple errors


# =============================================================================
# Severity Tests
# =============================================================================

class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"

    def test_severity_comparison(self):
        """Test severity comparison."""
        assert Severity.ERROR == Severity.ERROR
        assert Severity.ERROR != Severity.WARNING


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
