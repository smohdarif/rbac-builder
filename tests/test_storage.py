"""
Tests for Phase 2: Storage Service
==================================

Tests for StorageService save, load, delete, and template operations.

Run with: pytest tests/test_storage.py -v
"""

import pytest
import json
import tempfile
from pathlib import Path

from services import (
    StorageService,
    StorageError,
    ConfigNotFoundError,
    ConfigParseError,
)
from models import RBACConfig, Team, EnvironmentGroup


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_storage():
    """Create a StorageService with temporary directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        storage = StorageService(base_path=base_path)
        yield storage


@pytest.fixture
def sample_config():
    """Create a sample RBACConfig for testing."""
    return RBACConfig(
        customer_name="Test Customer",
        project_key="test-project",
        mode="Manual",
        teams=[
            Team(key="dev", name="Developer", description="Dev team"),
            Team(key="qa", name="QA", description="QA team")
        ],
        env_groups=[
            EnvironmentGroup(key="test", is_critical=False),
            EnvironmentGroup(key="production", is_critical=True)
        ]
    )


# =============================================================================
# Save Tests
# =============================================================================

class TestStorageSave:
    """Tests for saving configurations."""

    def test_save_config(self, temp_storage, sample_config):
        """Test saving a configuration."""
        path = temp_storage.save(sample_config)

        assert path.exists()
        assert path.suffix == ".json"

    def test_save_creates_customer_folder(self, temp_storage, sample_config):
        """Test that save creates a customer folder."""
        path = temp_storage.save(sample_config)

        # Folder should be named after customer (sanitized)
        assert "test_customer" in str(path.parent).lower() or "test-customer" in str(path.parent).lower()

    def test_save_overwrites_existing(self, temp_storage, sample_config):
        """Test that save overwrites existing config."""
        # Save twice
        path1 = temp_storage.save(sample_config)
        sample_config.mode = "Connected"  # Modify
        path2 = temp_storage.save(sample_config)

        # Should be same path
        assert path1 == path2

        # Load and verify updated
        loaded = temp_storage.load("Test Customer")
        assert loaded.mode == "Connected"


# =============================================================================
# Load Tests
# =============================================================================

class TestStorageLoad:
    """Tests for loading configurations."""

    def test_load_config(self, temp_storage, sample_config):
        """Test loading a saved configuration."""
        temp_storage.save(sample_config)

        loaded = temp_storage.load("Test Customer")

        assert loaded.customer_name == "Test Customer"
        assert loaded.project_key == "test-project"
        assert len(loaded.teams) == 2
        assert len(loaded.env_groups) == 2

    def test_load_not_found_raises(self, temp_storage):
        """Test that loading non-existent config raises error."""
        with pytest.raises(ConfigNotFoundError):
            temp_storage.load("NonExistent")

    def test_load_preserves_teams(self, temp_storage, sample_config):
        """Test that teams are preserved after load."""
        temp_storage.save(sample_config)
        loaded = temp_storage.load("Test Customer")

        assert loaded.teams[0].key == "dev"
        assert loaded.teams[0].name == "Developer"
        assert loaded.teams[1].key == "qa"

    def test_load_preserves_env_groups(self, temp_storage, sample_config):
        """Test that environment groups are preserved after load."""
        temp_storage.save(sample_config)
        loaded = temp_storage.load("Test Customer")

        assert loaded.env_groups[0].key == "test"
        assert loaded.env_groups[0].is_critical is False
        assert loaded.env_groups[1].key == "production"
        assert loaded.env_groups[1].is_critical is True


# =============================================================================
# Exists Tests
# =============================================================================

class TestStorageExists:
    """Tests for checking if config exists."""

    def test_exists_true(self, temp_storage, sample_config):
        """Test exists returns True for saved config."""
        temp_storage.save(sample_config)

        assert temp_storage.exists("Test Customer") is True

    def test_exists_false(self, temp_storage):
        """Test exists returns False for non-existent config."""
        assert temp_storage.exists("NonExistent") is False


# =============================================================================
# Delete Tests
# =============================================================================

class TestStorageDelete:
    """Tests for deleting configurations."""

    def test_delete_config(self, temp_storage, sample_config):
        """Test deleting a configuration."""
        temp_storage.save(sample_config)
        assert temp_storage.exists("Test Customer")

        result = temp_storage.delete("Test Customer")

        assert result is True
        assert temp_storage.exists("Test Customer") is False

    def test_delete_nonexistent_returns_false(self, temp_storage):
        """Test deleting non-existent config returns False."""
        result = temp_storage.delete("NonExistent")

        assert result is False


# =============================================================================
# List Tests
# =============================================================================

class TestStorageList:
    """Tests for listing configurations."""

    def test_list_customers_empty(self, temp_storage):
        """Test listing when no customers saved."""
        customers = temp_storage.list_customers()

        assert customers == []

    def test_list_customers(self, temp_storage, sample_config):
        """Test listing saved customers."""
        temp_storage.save(sample_config)

        # Save another
        config2 = RBACConfig(
            customer_name="Another Customer",
            project_key="another-project"
        )
        temp_storage.save(config2)

        customers = temp_storage.list_customers()

        assert len(customers) == 2
        assert "Test Customer" in customers or "test_customer" in [c.lower() for c in customers]


# =============================================================================
# Export/Import Tests
# =============================================================================

class TestStorageExportImport:
    """Tests for JSON export/import."""

    def test_export_json(self, temp_storage, sample_config):
        """Test exporting config to JSON string."""
        json_str = temp_storage.export_json(sample_config)

        # Should be valid JSON
        data = json.loads(json_str)

        assert data["customer_name"] == "Test Customer"
        assert data["project_key"] == "test-project"

    def test_import_json(self, temp_storage, sample_config):
        """Test importing config from JSON string."""
        json_str = temp_storage.export_json(sample_config)

        imported = temp_storage.import_json(json_str)

        assert imported.customer_name == "Test Customer"
        assert imported.project_key == "test-project"
        assert len(imported.teams) == 2

    def test_import_invalid_json_raises(self, temp_storage):
        """Test that invalid JSON raises error."""
        with pytest.raises(ConfigParseError):
            temp_storage.import_json("not valid json")


# =============================================================================
# Template Tests
# =============================================================================

class TestStorageTemplates:
    """Tests for template operations."""

    def test_list_templates(self, temp_storage):
        """Test listing available templates."""
        # Note: This uses the actual templates folder
        # In a real test, we'd mock or create temp templates
        templates = temp_storage.list_templates()

        # Should return a list (may be empty in temp dir)
        assert isinstance(templates, list)

    def test_save_as_template(self, temp_storage, sample_config):
        """Test saving config as template."""
        path = temp_storage.save_as_template(sample_config, "my-template")

        assert path.exists()
        assert "my-template" in path.name


# =============================================================================
# Edge Cases
# =============================================================================

class TestStorageEdgeCases:
    """Tests for edge cases and error handling."""

    def test_customer_name_sanitization(self, temp_storage):
        """Test that customer names are properly sanitized."""
        config = RBACConfig(
            customer_name="Customer With Spaces & Special!",
            project_key="test"
        )
        path = temp_storage.save(config)

        # Should create valid path
        assert path.exists()

    def test_load_after_save_roundtrip(self, temp_storage, sample_config):
        """Test complete save/load roundtrip."""
        original = sample_config

        temp_storage.save(original)
        loaded = temp_storage.load("Test Customer")

        # Compare key fields
        assert loaded.customer_name == original.customer_name
        assert loaded.project_key == original.project_key
        assert loaded.mode == original.mode
        assert len(loaded.teams) == len(original.teams)
        assert len(loaded.env_groups) == len(original.env_groups)


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
