"""
Tests for Phase 1: Data Models
==============================

Tests for Team, EnvironmentGroup, and RBACConfig dataclasses.

Run with: pytest tests/test_models.py -v
"""

import pytest
from datetime import datetime

from models import Team, EnvironmentGroup, RBACConfig


# =============================================================================
# Team Tests
# =============================================================================

class TestTeam:
    """Tests for the Team dataclass."""

    def test_create_team_basic(self):
        """Test creating a team with required fields."""
        team = Team(key="dev", name="Developer")

        assert team.key == "dev"
        assert team.name == "Developer"
        assert team.description == ""  # Default

    def test_create_team_full(self):
        """Test creating a team with all fields."""
        team = Team(
            key="qa",
            name="QA Engineer",
            description="Quality assurance team"
        )

        assert team.key == "qa"
        assert team.name == "QA Engineer"
        assert team.description == "Quality assurance team"

    def test_team_to_dict(self):
        """Test Team serialization to dict."""
        team = Team(key="dev", name="Developer", description="Dev team")
        data = team.to_dict()

        assert data == {
            "key": "dev",
            "name": "Developer",
            "description": "Dev team"
        }

    def test_team_from_dict(self):
        """Test Team deserialization from dict."""
        data = {
            "key": "admin",
            "name": "Administrator",
            "description": "Admin team"
        }
        team = Team.from_dict(data)

        assert team.key == "admin"
        assert team.name == "Administrator"
        assert team.description == "Admin team"

    def test_team_empty_key_raises(self):
        """Test that empty key raises ValueError."""
        with pytest.raises(ValueError, match="key cannot be empty"):
            Team(key="", name="No Key Team")

    def test_team_empty_name_raises(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Team(key="noname", name="")


# =============================================================================
# EnvironmentGroup Tests
# =============================================================================

class TestEnvironmentGroup:
    """Tests for the EnvironmentGroup dataclass."""

    def test_create_env_group_basic(self):
        """Test creating an environment group with defaults."""
        env = EnvironmentGroup(key="production")

        assert env.key == "production"
        assert env.requires_approval is False
        assert env.is_critical is False
        assert env.notes == ""

    def test_create_env_group_critical(self):
        """Test creating a critical environment group."""
        env = EnvironmentGroup(
            key="production",
            requires_approval=True,
            is_critical=True,
            notes="Production environment"
        )

        assert env.key == "production"
        assert env.requires_approval is True
        assert env.is_critical is True
        assert env.notes == "Production environment"

    def test_env_group_auto_approval_for_critical(self):
        """Test that critical environments auto-set requires_approval."""
        env = EnvironmentGroup(
            key="prod",
            is_critical=True,
            requires_approval=False  # Should be overridden
        )

        # __post_init__ should set requires_approval=True
        assert env.requires_approval is True

    def test_env_group_to_dict(self):
        """Test EnvironmentGroup serialization."""
        env = EnvironmentGroup(
            key="staging",
            requires_approval=False,
            is_critical=False,
            notes="Staging env"
        )
        data = env.to_dict()

        assert data["key"] == "staging"
        assert data["requires_approval"] is False
        assert data["is_critical"] is False
        assert data["notes"] == "Staging env"

    def test_env_group_from_dict(self):
        """Test EnvironmentGroup deserialization."""
        data = {
            "key": "test",
            "requires_approval": False,
            "is_critical": False,
            "notes": "Test environment"
        }
        env = EnvironmentGroup.from_dict(data)

        assert env.key == "test"
        assert env.is_critical is False


# =============================================================================
# RBACConfig Tests
# =============================================================================

class TestRBACConfig:
    """Tests for the RBACConfig dataclass."""

    def test_create_config_basic(self):
        """Test creating a basic RBAC config."""
        config = RBACConfig(
            customer_name="Acme Corp",
            project_key="mobile-app"
        )

        assert config.customer_name == "Acme Corp"
        assert config.project_key == "mobile-app"
        assert config.mode == "Manual"  # Default
        assert config.teams == []
        assert config.env_groups == []

    def test_create_config_full(self):
        """Test creating a full RBAC config."""
        teams = [
            Team(key="dev", name="Developer"),
            Team(key="qa", name="QA")
        ]
        env_groups = [
            EnvironmentGroup(key="test"),
            EnvironmentGroup(key="production", is_critical=True)
        ]

        config = RBACConfig(
            customer_name="Acme",
            project_key="app",
            mode="Connected",
            teams=teams,
            env_groups=env_groups
        )

        assert len(config.teams) == 2
        assert len(config.env_groups) == 2
        assert config.mode == "Connected"

    def test_config_empty_customer_raises(self):
        """Test that empty customer_name raises ValueError."""
        with pytest.raises(ValueError, match="customer_name cannot be empty"):
            RBACConfig(customer_name="", project_key="app")

    def test_config_empty_project_raises(self):
        """Test that empty project_key raises ValueError."""
        with pytest.raises(ValueError, match="project_key cannot be empty"):
            RBACConfig(customer_name="Acme", project_key="")

    def test_config_to_dict(self):
        """Test RBACConfig serialization."""
        config = RBACConfig(
            customer_name="Test",
            project_key="test-project",
            teams=[Team(key="dev", name="Developer")],
            env_groups=[EnvironmentGroup(key="prod", is_critical=True)]
        )
        data = config.to_dict()

        assert data["customer_name"] == "Test"
        assert data["project_key"] == "test-project"
        assert len(data["teams"]) == 1
        assert len(data["env_groups"]) == 1
        assert data["teams"][0]["key"] == "dev"

    def test_config_to_json(self):
        """Test RBACConfig JSON serialization."""
        config = RBACConfig(
            customer_name="Test",
            project_key="test"
        )
        json_str = config.to_json()

        assert '"customer_name": "Test"' in json_str
        assert '"project_key": "test"' in json_str

    def test_config_from_dict(self):
        """Test RBACConfig deserialization."""
        data = {
            "customer_name": "Loaded",
            "project_key": "loaded-project",
            "mode": "Manual",
            "teams": [{"key": "dev", "name": "Dev", "description": ""}],
            "env_groups": [{"key": "prod", "is_critical": True}]
        }
        config = RBACConfig.from_dict(data)

        assert config.customer_name == "Loaded"
        assert len(config.teams) == 1
        assert config.teams[0].key == "dev"
        assert len(config.env_groups) == 1
        assert config.env_groups[0].is_critical is True

    def test_config_created_at_auto_set(self):
        """Test that created_at is auto-set."""
        config = RBACConfig(
            customer_name="Test",
            project_key="test"
        )

        assert config.created_at is not None
        assert isinstance(config.created_at, datetime)

    def test_config_roundtrip(self):
        """Test that config survives dict roundtrip."""
        config = RBACConfig(
            customer_name="Test",
            project_key="test",
            teams=[Team(key="dev", name="Developer")]
        )
        data = config.to_dict()
        loaded = RBACConfig.from_dict(data)

        assert loaded.customer_name == config.customer_name
        assert loaded.project_key == config.project_key
        assert len(loaded.teams) == len(config.teams)


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
