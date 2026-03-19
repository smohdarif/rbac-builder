"""
Tests for Phase 5: UI Modules
=============================

Tests for setup_tab, matrix_tab, deploy_tab, reference_tab.

Note: Streamlit UI testing is challenging. We focus on:
1. Testing pure functions extracted from UI code
2. Testing session state initialization
3. Testing data transformations

Run with: pytest tests/test_ui_modules.py -v
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def default_teams_df():
    """Create default teams DataFrame."""
    return pd.DataFrame({
        "Key": ["dev", "qa", "admin"],
        "Name": ["Developer", "QA Engineer", "Administrator"],
        "Description": ["Development team", "QA team", "Admin team"]
    })


@pytest.fixture
def default_env_groups_df():
    """Create default environment groups DataFrame."""
    return pd.DataFrame({
        "Key": ["Test", "Production"],
        "Critical": [False, True]
    })


@pytest.fixture
def mock_session_state(default_teams_df, default_env_groups_df):
    """Create mock session state with default values."""
    # Use a dict-like mock that handles .get() properly
    mock_data = {
        "customer_name": "Test Corp",
        "project_key": "test-project",
        "_customer_name": "Test Corp",
        "_mode": "Manual",
        "project": "test-project",
        "teams": default_teams_df,
        "env_groups": default_env_groups_df,
        "project_matrix_df": None,
        "env_matrix_df": None,
        "validation_result": None,
        "deploy_payload": None,
    }

    mock = MagicMock()
    # Make .get() work like a dict
    mock.get = lambda key, default=None: mock_data.get(key, default)
    # Make attribute access work
    mock.customer_name = "Test Corp"
    mock.project_key = "test-project"
    mock.teams_df = default_teams_df
    mock.env_groups_df = default_env_groups_df
    mock.teams = default_teams_df
    mock.env_groups = default_env_groups_df
    mock.project_matrix_df = None
    mock.env_matrix_df = None
    mock.validation_result = None
    mock.deploy_payload = None
    # Make "in" checks work
    mock.__contains__ = lambda self, key: key in mock_data

    return mock


# =============================================================================
# Setup Tab Tests
# =============================================================================

class TestSetupTabHelpers:
    """Tests for setup_tab helper functions."""

    def test_default_teams_has_required_columns(self, default_teams_df):
        """Test that default teams has Key, Name, Description columns."""
        required_columns = ["Key", "Name", "Description"]
        for col in required_columns:
            assert col in default_teams_df.columns

    def test_default_teams_has_data(self, default_teams_df):
        """Test that default teams is not empty."""
        assert len(default_teams_df) > 0

    def test_default_env_groups_has_required_columns(self, default_env_groups_df):
        """Test that default env groups has Key, Critical columns."""
        required_columns = ["Key", "Critical"]
        for col in required_columns:
            assert col in default_env_groups_df.columns

    def test_default_env_groups_has_data(self, default_env_groups_df):
        """Test that default env groups is not empty."""
        assert len(default_env_groups_df) > 0

    def test_env_groups_has_critical_environment(self, default_env_groups_df):
        """Test that at least one environment is marked critical."""
        assert default_env_groups_df["Critical"].any()


# =============================================================================
# Matrix Tab Tests
# =============================================================================

class TestMatrixTabHelpers:
    """Tests for matrix_tab helper functions."""

    def test_create_project_matrix_from_teams(self, default_teams_df):
        """Test creating project matrix from teams."""
        from ui.matrix_tab import create_default_project_matrix

        team_names = default_teams_df["Name"].tolist()
        matrix = create_default_project_matrix(team_names)

        # Should have one row per team
        assert len(matrix) == len(team_names)
        # Should have Team column
        assert "Team" in matrix.columns
        # Teams should match
        assert list(matrix["Team"]) == team_names

    def test_create_project_matrix_has_permission_columns(self, default_teams_df):
        """Test that project matrix has permission columns."""
        from ui.matrix_tab import create_default_project_matrix, PROJECT_PERMISSIONS

        team_names = default_teams_df["Name"].tolist()
        matrix = create_default_project_matrix(team_names)

        # Should have all permission columns
        for perm in PROJECT_PERMISSIONS:
            assert perm in matrix.columns

    def test_create_project_matrix_defaults_to_false(self, default_teams_df):
        """Test that permissions default to False (except View Project)."""
        from ui.matrix_tab import create_default_project_matrix, PROJECT_PERMISSIONS

        team_names = default_teams_df["Name"].tolist()
        matrix = create_default_project_matrix(team_names)

        # All permission values should be False, except "View Project" which is True
        for perm in PROJECT_PERMISSIONS:
            if perm == "View Project":
                assert (matrix[perm] == True).all()  # View Project defaults to True
            else:
                assert (matrix[perm] == False).all()

    def test_create_env_matrix_from_teams_and_envs(
        self, default_teams_df, default_env_groups_df
    ):
        """Test creating env matrix from teams and environments."""
        from ui.matrix_tab import create_default_env_matrix

        team_names = default_teams_df["Name"].tolist()
        env_keys = default_env_groups_df["Key"].tolist()
        matrix = create_default_env_matrix(team_names, env_keys)

        # Should have teams × envs rows
        expected_rows = len(team_names) * len(env_keys)
        assert len(matrix) == expected_rows

    def test_create_env_matrix_has_team_and_env_columns(
        self, default_teams_df, default_env_groups_df
    ):
        """Test that env matrix has Team and Environment columns."""
        from ui.matrix_tab import create_default_env_matrix

        team_names = default_teams_df["Name"].tolist()
        env_keys = default_env_groups_df["Key"].tolist()
        matrix = create_default_env_matrix(team_names, env_keys)

        assert "Team" in matrix.columns
        assert "Environment" in matrix.columns

    def test_create_env_matrix_has_permission_columns(
        self, default_teams_df, default_env_groups_df
    ):
        """Test that env matrix has permission columns."""
        from ui.matrix_tab import create_default_env_matrix, ENV_PERMISSIONS

        team_names = default_teams_df["Name"].tolist()
        env_keys = default_env_groups_df["Key"].tolist()
        matrix = create_default_env_matrix(team_names, env_keys)

        for perm in ENV_PERMISSIONS:
            assert perm in matrix.columns

    def test_sync_project_matrix_adds_new_team(self, default_teams_df):
        """Test that syncing adds rows for new teams."""
        from ui.matrix_tab import create_default_project_matrix, sync_project_matrix

        # Create initial matrix with 2 teams
        initial_teams = ["Developer", "QA"]
        matrix = create_default_project_matrix(initial_teams)
        assert len(matrix) == 2

        # Sync with 3 teams
        new_teams = ["Developer", "QA", "Admin"]
        synced = sync_project_matrix(matrix, new_teams)

        assert len(synced) == 3
        assert "Admin" in synced["Team"].tolist()

    def test_sync_project_matrix_removes_deleted_team(self, default_teams_df):
        """Test that syncing removes rows for deleted teams."""
        from ui.matrix_tab import create_default_project_matrix, sync_project_matrix

        # Create initial matrix with 3 teams
        initial_teams = ["Developer", "QA", "Admin"]
        matrix = create_default_project_matrix(initial_teams)
        assert len(matrix) == 3

        # Sync with 2 teams (Admin removed)
        new_teams = ["Developer", "QA"]
        synced = sync_project_matrix(matrix, new_teams)

        assert len(synced) == 2
        assert "Admin" not in synced["Team"].tolist()

    def test_sync_project_matrix_preserves_permissions(self, default_teams_df):
        """Test that syncing preserves existing permission values."""
        from ui.matrix_tab import create_default_project_matrix, sync_project_matrix

        # Create initial matrix
        initial_teams = ["Developer", "QA"]
        matrix = create_default_project_matrix(initial_teams)

        # Set a permission to True
        matrix.loc[matrix["Team"] == "Developer", "Create Flags"] = True

        # Sync (no changes to teams)
        synced = sync_project_matrix(matrix, initial_teams)

        # Permission should be preserved
        dev_row = synced[synced["Team"] == "Developer"]
        assert dev_row["Create Flags"].iloc[0] == True


# =============================================================================
# Deploy Tab Tests
# =============================================================================

class TestDeployTabHelpers:
    """Tests for deploy_tab helper functions."""

    def test_build_config_from_session(self, mock_session_state):
        """Test building RBACConfig from session state."""
        from ui.deploy_tab import build_config_from_session

        with patch("streamlit.session_state", mock_session_state):
            config = build_config_from_session()

            assert config.customer_name == "Test Corp"
            assert config.project_key == "test-project"

    def test_validation_runs_with_session_data(self, mock_session_state):
        """Test that validation can run with session state data."""
        from services import ConfigValidator

        validator = ConfigValidator(
            customer_name=mock_session_state.customer_name,
            project_key=mock_session_state.project_key,
            teams_df=mock_session_state.teams_df,
            env_groups_df=mock_session_state.env_groups_df,
            project_matrix_df=pd.DataFrame({"Team": []}),
            env_matrix_df=pd.DataFrame({"Team": [], "Environment": []})
        )
        result = validator.validate()

        # Should run without error
        assert result is not None


# =============================================================================
# Reference Tab Tests
# =============================================================================

class TestReferenceTabHelpers:
    """Tests for reference_tab helper functions."""

    def test_reference_content_exists(self):
        """Test that reference content constants exist."""
        from ui.reference_tab import (
            HIERARCHY_DIAGRAM,
            KEY_TERMS,
            BUILTIN_ROLES,
        )

        assert HIERARCHY_DIAGRAM is not None
        assert len(HIERARCHY_DIAGRAM) > 0

        assert KEY_TERMS is not None
        assert len(KEY_TERMS) > 0

        assert BUILTIN_ROLES is not None
        assert len(BUILTIN_ROLES) > 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestUIIntegration:
    """Integration tests for UI modules."""

    def test_matrix_uses_teams_from_setup(
        self, default_teams_df, default_env_groups_df
    ):
        """Test that matrix tab can use teams from setup tab."""
        from ui.matrix_tab import create_default_project_matrix

        # Simulate setup tab saving teams
        team_names = default_teams_df["Name"].tolist()

        # Matrix tab creates matrix from those teams
        matrix = create_default_project_matrix(team_names)

        # Should have correct number of rows
        assert len(matrix) == len(team_names)

    def test_deploy_can_use_matrix_data(
        self, default_teams_df, default_env_groups_df
    ):
        """Test that deploy tab can use matrix data."""
        from ui.matrix_tab import create_default_project_matrix, create_default_env_matrix
        from services import PayloadBuilder

        team_names = default_teams_df["Name"].tolist()
        env_keys = default_env_groups_df["Key"].tolist()

        project_matrix = create_default_project_matrix(team_names)
        env_matrix = create_default_env_matrix(team_names, env_keys)

        # Deploy tab uses PayloadBuilder with matrix data
        builder = PayloadBuilder(
            customer_name="Test",
            project_key="test",
            teams_df=default_teams_df,
            env_groups_df=default_env_groups_df,
            project_matrix_df=project_matrix,
            env_matrix_df=env_matrix
        )
        payload = builder.build()

        # Should generate payload
        assert payload is not None
        assert payload.get_team_count() == len(team_names)


# =============================================================================
# Session State Tests
# =============================================================================

class TestSessionStatePatterns:
    """Tests for session state patterns used in UI modules."""

    def test_safe_initialization_pattern(self):
        """Test the safe session state initialization pattern."""
        # Simulating: if "key" not in st.session_state: st.session_state.key = default
        session_state = {}

        # First access - initialize
        if "customer_name" not in session_state:
            session_state["customer_name"] = ""

        assert session_state["customer_name"] == ""

        # Second access - should not reset
        session_state["customer_name"] = "Test Corp"
        if "customer_name" not in session_state:
            session_state["customer_name"] = ""

        assert session_state["customer_name"] == "Test Corp"

    def test_get_with_default_pattern(self):
        """Test the get with default pattern."""
        session_state = {}

        # Get with default
        value = session_state.get("missing_key", "default_value")
        assert value == "default_value"

        # Key still doesn't exist (get doesn't create it)
        assert "missing_key" not in session_state


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
