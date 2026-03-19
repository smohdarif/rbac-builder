"""
Storage Service for RBAC Builder
================================

This module handles saving and loading RBAC configurations to/from JSON files.

Features:
    - Save configurations with automatic backup
    - Load configurations from file
    - List all saved customers
    - Template support for quick starts
    - Version history management

Learn more: docs/phases/phase2/DESIGN.md
"""

# =============================================================================
# LESSON 42: Imports Organization
# =============================================================================
# Python imports are organized in three groups (PEP 8):
#   1. Standard library imports (built into Python)
#   2. Third-party imports (installed via pip)
#   3. Local imports (our own modules)
#
# Each group is separated by a blank line.

# Standard library imports
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

# Third-party imports
# (none needed for this module)

# Local imports
# =============================================================================
# LESSON 42b: Import Strategies for Packages
# =============================================================================
# There are two ways to import from sibling packages:
#
# 1. Relative import: from ..models import RBACConfig
#    - Only works when running as a package
#    - Doesn't work when running file directly (python storage.py)
#
# 2. Absolute import: from models import RBACConfig
#    - Works when app.py is in the project root
#    - Streamlit Cloud compatible (runs from project root)
#
# We use absolute imports for Streamlit Cloud compatibility.
from models import RBACConfig


# =============================================================================
# LESSON 43: Custom Exceptions
# =============================================================================
# Custom exceptions make error handling more specific and meaningful.
#
# Instead of:
#   raise Exception("Config not found")  # Generic, hard to catch specifically
#
# We use:
#   raise ConfigNotFoundError("acme")  # Specific, can catch this type only
#
# Benefits:
#   - UI can show different messages for different errors
#   - Easier debugging (know exactly what went wrong)
#   - Can add extra context (like customer name)


class StorageError(Exception):
    """
    Base exception for all storage operations.

    All other storage exceptions inherit from this.
    This allows catching ALL storage errors with one except block:

        try:
            storage.load("customer")
        except StorageError as e:
            # Catches ConfigNotFoundError, ConfigParseError, etc.
            print(f"Storage error: {e}")
    """
    pass


class ConfigNotFoundError(StorageError):
    """
    Raised when a configuration file doesn't exist.

    Example:
        raise ConfigNotFoundError("acme-corp")
        # Message: "Configuration not found for 'acme-corp'"
    """

    def __init__(self, customer_name: str):
        self.customer_name = customer_name
        super().__init__(f"Configuration not found for '{customer_name}'")


class ConfigParseError(StorageError):
    """
    Raised when JSON parsing fails.

    Stores the original error for debugging.

    Example:
        except json.JSONDecodeError as e:
            raise ConfigParseError("config.json", e) from e
    """

    def __init__(self, file_path: str, original_error: Exception):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(f"Failed to parse '{file_path}': {original_error}")


class ConfigWriteError(StorageError):
    """
    Raised when writing to file fails.

    Could be due to:
        - Permission denied
        - Disk full
        - Invalid path
    """

    def __init__(self, file_path: str, original_error: Exception):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(f"Failed to write '{file_path}': {original_error}")


# =============================================================================
# LESSON 44: Helper Functions
# =============================================================================
# Small utility functions that do one thing well.
# These are module-level functions (not in a class) because:
#   - They don't need object state
#   - They can be reused elsewhere
#   - They're easier to test in isolation


def slugify(text: str) -> str:
    """
    Convert a human-readable string to a filename-safe slug.

    This ensures customer names become valid folder names on any OS.

    Examples:
        >>> slugify("Acme Corporation")
        'acme-corporation'
        >>> slugify("John's Company")
        'johns-company'
        >>> slugify("Test 123!")
        'test-123'
        >>> slugify("  Extra   Spaces  ")
        'extra-spaces'

    Why slugify?
        File systems have restrictions:
        - Windows: Can't use \\ / : * ? " < > |
        - macOS: Can't use : /
        - Linux: Can't use /

        Slugify converts to safe characters: a-z, 0-9, hyphen
    """
    # Step 1: Convert to lowercase
    slug = text.lower()

    # Step 2: Replace spaces with hyphens
    slug = slug.replace(" ", "-")

    # Step 3: Remove special characters (keep only letters, numbers, hyphens)
    # re.sub replaces anything NOT matching the pattern with empty string
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Step 4: Remove multiple consecutive hyphens
    # "acme---corp" becomes "acme-corp"
    slug = re.sub(r"-+", "-", slug)

    # Step 5: Remove leading/trailing hyphens
    slug = slug.strip("-")

    return slug


def get_timestamp() -> str:
    """
    Generate a timestamp string for backup filenames.

    Format: YYYY-MM-DD_HH-MM-SS

    Example:
        >>> get_timestamp()
        '2024-03-11_14-30-00'

    Why this format?
        - Sortable: alphabetical order = chronological order
        - Filename safe: no colons (Windows doesn't allow them)
        - Human readable: easy to see when backup was made
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


# =============================================================================
# LESSON 45: The StorageService Class
# =============================================================================
# This is the main class that handles all file operations.
#
# Design decisions:
#   - Uses pathlib.Path for cross-platform compatibility
#   - Stores configs in organized folder structure
#   - Automatically creates backups before overwriting
#   - Provides template support for quick starts


class StorageService:
    """
    Service for saving and loading RBAC configurations.

    Directory Structure:
        configs/
        ├── customers/
        │   └── {customer-slug}/
        │       ├── config.json      # Current config
        │       └── history/         # Backups
        │           └── 2024-03-11_14-30-00.json
        └── templates/
            └── standard-4-env.json

    Usage:
        storage = StorageService()

        # Save configuration (auto-creates backup if exists)
        storage.save(config)

        # Load configuration
        config = storage.load("Acme Corporation")

        # List all customers
        customers = storage.list_customers()
    """

    # ==========================================================================
    # LESSON 46: Class Constants and __init__
    # ==========================================================================
    # Constants are defined at class level (shared by all instances).
    # __init__ sets up instance-specific state.

    # Default number of backups to keep per customer
    DEFAULT_MAX_HISTORY = 10

    def __init__(
        self,
        base_path: Optional[Path | str] = None,
        max_history: int = DEFAULT_MAX_HISTORY,
    ):
        """
        Initialize the storage service.

        Args:
            base_path: Root path for configs. Defaults to ./configs
            max_history: Maximum backup files to keep per customer

        Example:
            # Use default location (./configs)
            storage = StorageService()

            # Use custom location
            storage = StorageService(base_path="/data/rbac-configs")
        """
        # =======================================================================
        # LESSON 47: pathlib.Path
        # =======================================================================
        # Path objects are better than strings for file paths:
        #   - Cross-platform (Windows uses \, Unix uses /)
        #   - Convenient methods (exists(), mkdir(), etc.)
        #   - Can use / operator to join paths
        #
        # Path("configs") / "customers" / "acme"
        # Becomes: "configs/customers/acme" (Unix) or "configs\\customers\\acme" (Windows)

        if base_path is None:
            # Default to ./configs relative to the project root
            # __file__ is the path to THIS file (storage.py)
            # .parent.parent goes up two levels: services/ -> rbac-builder/
            project_root = Path(__file__).parent.parent
            self.base_path = project_root / "configs"
        else:
            # Convert string to Path if needed
            self.base_path = Path(base_path)

        # =======================================================================
        # LESSON 48: Computed Properties
        # =======================================================================
        # Store commonly used paths as instance attributes.
        # This avoids recalculating them every time.

        self.customers_path = self.base_path / "customers"
        self.templates_path = self.base_path / "templates"
        self.max_history = max_history

        # =======================================================================
        # LESSON 49: Directory Initialization
        # =======================================================================
        # Ensure directories exist when service is created.
        # This prevents errors later when trying to save.
        #
        # mkdir() parameters:
        #   parents=True: Create parent directories if needed
        #   exist_ok=True: Don't error if directory already exists

        self.customers_path.mkdir(parents=True, exist_ok=True)
        self.templates_path.mkdir(parents=True, exist_ok=True)

    # ==========================================================================
    # LESSON 50: Path Helper Methods
    # ==========================================================================
    # Private methods (prefixed with _) that build file paths.
    # These are internal helpers, not part of the public API.

    def _get_customer_path(self, customer_name: str) -> Path:
        """Get the directory path for a customer."""
        customer_slug = slugify(customer_name)
        return self.customers_path / customer_slug

    def _get_config_path(self, customer_name: str) -> Path:
        """Get the config.json path for a customer."""
        return self._get_customer_path(customer_name) / "config.json"

    def _get_history_path(self, customer_name: str) -> Path:
        """Get the history directory path for a customer."""
        return self._get_customer_path(customer_name) / "history"

    # ==========================================================================
    # LESSON 51: Core Operations - exists()
    # ==========================================================================

    def exists(self, customer_name: str) -> bool:
        """
        Check if a configuration exists for a customer.

        Args:
            customer_name: The customer name (will be slugified)

        Returns:
            True if config exists, False otherwise

        Example:
            if storage.exists("Acme Corporation"):
                config = storage.load("Acme Corporation")
        """
        config_path = self._get_config_path(customer_name)
        return config_path.exists()

    # ==========================================================================
    # LESSON 52: Core Operations - save()
    # ==========================================================================

    def save(self, config: RBACConfig) -> Path:
        """
        Save a configuration to the file system.

        This method:
            1. Validates the config has a customer name
            2. Creates the customer directory if needed
            3. Creates a backup if config already exists
            4. Updates the timestamp
            5. Writes the JSON file
            6. Cleans up old backups

        Args:
            config: The RBACConfig to save

        Returns:
            Path to the saved config file

        Raises:
            ValueError: If customer_name is empty
            ConfigWriteError: If writing fails

        Example:
            config = RBACConfig(customer_name="Acme", project_key="web-app")
            path = storage.save(config)
            print(f"Saved to {path}")
        """
        # Step 1: Validate
        if not config.customer_name or not config.customer_name.strip():
            raise ValueError("Customer name is required to save configuration")

        # Step 2: Get paths
        customer_path = self._get_customer_path(config.customer_name)
        config_path = self._get_config_path(config.customer_name)
        history_path = self._get_history_path(config.customer_name)

        # Step 3: Create directories
        # =======================================================================
        # LESSON 53: Creating Nested Directories
        # =======================================================================
        # mkdir(parents=True) creates all parent directories if they don't exist.
        # Like: mkdir -p in bash
        customer_path.mkdir(parents=True, exist_ok=True)
        history_path.mkdir(parents=True, exist_ok=True)

        # Step 4: Create backup if config already exists
        if config_path.exists():
            self._create_backup(config.customer_name)

        # Step 5: Update timestamp
        config.mark_updated()

        # Step 6: Write JSON to file
        # =======================================================================
        # LESSON 54: Writing Files with Path.write_text()
        # =======================================================================
        # Path.write_text() is a convenient method that:
        #   - Opens the file
        #   - Writes the content
        #   - Closes the file
        # All in one line! Equivalent to:
        #   with open(path, 'w') as f:
        #       f.write(content)

        try:
            json_string = config.to_json()
            config_path.write_text(json_string, encoding="utf-8")
        except (IOError, OSError) as e:
            raise ConfigWriteError(str(config_path), e) from e

        # Step 7: Cleanup old backups
        self._cleanup_old_backups(config.customer_name)

        return config_path

    # ==========================================================================
    # LESSON 55: Core Operations - load()
    # ==========================================================================

    def load(self, customer_name: str) -> RBACConfig:
        """
        Load a configuration from the file system.

        Args:
            customer_name: The customer name to load (will be slugified)

        Returns:
            The loaded RBACConfig

        Raises:
            ConfigNotFoundError: If config doesn't exist
            ConfigParseError: If JSON is invalid

        Example:
            config = storage.load("Acme Corporation")
            print(f"Loaded config for {config.customer_name}")
        """
        config_path = self._get_config_path(customer_name)

        # Check if file exists
        if not config_path.exists():
            raise ConfigNotFoundError(customer_name)

        # =======================================================================
        # LESSON 56: Reading Files with Path.read_text()
        # =======================================================================
        # Path.read_text() reads the entire file content as a string.
        # It handles opening, reading, and closing automatically.

        try:
            json_string = config_path.read_text(encoding="utf-8")
        except (IOError, OSError) as e:
            raise StorageError(f"Failed to read config: {e}") from e

        # =======================================================================
        # LESSON 57: Exception Chaining with 'from e'
        # =======================================================================
        # When we catch one exception and raise another, we use 'from e'
        # to preserve the original error information.
        #
        # This creates an "exception chain" that shows:
        #   ConfigParseError -> JSONDecodeError
        #
        # Helpful for debugging: you see both what happened AND why

        try:
            config = RBACConfig.from_json(json_string)
        except json.JSONDecodeError as e:
            raise ConfigParseError(str(config_path), e) from e

        return config

    # ==========================================================================
    # LESSON 58: Core Operations - delete()
    # ==========================================================================

    def delete(self, customer_name: str) -> bool:
        """
        Delete a customer's configuration and all history.

        WARNING: This permanently deletes all data for this customer!

        Args:
            customer_name: The customer to delete

        Returns:
            True if deleted, False if didn't exist

        Example:
            if storage.delete("Old Customer"):
                print("Deleted successfully")
        """
        customer_path = self._get_customer_path(customer_name)

        if not customer_path.exists():
            return False

        # =======================================================================
        # LESSON 59: Deleting Directories with shutil.rmtree()
        # =======================================================================
        # Path.rmdir() only works on EMPTY directories.
        # shutil.rmtree() deletes a directory AND all its contents.
        #
        # BE CAREFUL: This is permanent! There's no undo.

        shutil.rmtree(customer_path)
        return True

    # ==========================================================================
    # LESSON 60: Listing Operations
    # ==========================================================================

    def list_customers(self) -> list[str]:
        """
        Get a list of all saved customer names.

        Returns:
            List of customer names (not slugs, but original names)

        Example:
            customers = storage.list_customers()
            # ['Acme Corporation', 'Beta Inc', 'Gamma LLC']
        """
        # =======================================================================
        # LESSON 61: Iterating Directories with iterdir()
        # =======================================================================
        # Path.iterdir() yields each item (file or folder) in a directory.
        # We filter to only directories that have a config.json file.

        if not self.customers_path.exists():
            return []

        customers = []
        for folder in self.customers_path.iterdir():
            # Skip files, only process directories
            if not folder.is_dir():
                continue

            # Check if this folder has a config.json
            config_file = folder / "config.json"
            if not config_file.exists():
                continue

            # Load the config to get the actual customer name
            # (not the slugified folder name)
            try:
                config = self.load(folder.name)
                customers.append(config.customer_name)
            except (ConfigNotFoundError, ConfigParseError):
                # Skip invalid configs
                continue

        return sorted(customers)

    def list_templates(self) -> list[str]:
        """
        Get a list of available template names.

        Returns:
            List of template names (without .json extension)

        Example:
            templates = storage.list_templates()
            # ['standard-4-env', 'minimal-2-env']
        """
        # =======================================================================
        # LESSON 62: Finding Files with glob()
        # =======================================================================
        # Path.glob(pattern) finds files matching a pattern.
        # "*.json" matches any file ending in .json
        #
        # Path.stem gives the filename without extension:
        #   Path("standard-4-env.json").stem  ->  "standard-4-env"

        if not self.templates_path.exists():
            return []

        templates = []
        for template_file in self.templates_path.glob("*.json"):
            templates.append(template_file.stem)

        return sorted(templates)

    def list_history(self, customer_name: str) -> list[str]:
        """
        Get a list of backup timestamps for a customer.

        Args:
            customer_name: The customer to get history for

        Returns:
            List of timestamps (newest first)

        Example:
            history = storage.list_history("Acme Corporation")
            # ['2024-03-11_14-30-00', '2024-03-10_09-15-00']
        """
        history_path = self._get_history_path(customer_name)

        if not history_path.exists():
            return []

        # Get all backup files, sorted newest first
        backups = sorted(history_path.glob("*.json"), reverse=True)

        return [backup.stem for backup in backups]

    # ==========================================================================
    # LESSON 63: Template Operations
    # ==========================================================================

    def load_template(self, template_name: str) -> RBACConfig:
        """
        Load a starter template configuration.

        Templates are pre-built configurations that can be used as
        starting points. The loaded config will have:
            - Empty customer_name (user must fill in)
            - Fresh timestamps

        Args:
            template_name: Name of template (without .json extension)

        Returns:
            RBACConfig loaded from template

        Raises:
            ConfigNotFoundError: If template doesn't exist

        Example:
            config = storage.load_template("standard-4-env")
            config.customer_name = "New Customer"
            storage.save(config)
        """
        template_path = self.templates_path / f"{template_name}.json"

        if not template_path.exists():
            raise ConfigNotFoundError(f"Template '{template_name}'")

        try:
            json_string = template_path.read_text(encoding="utf-8")
            config = RBACConfig.from_json(json_string)
        except json.JSONDecodeError as e:
            raise ConfigParseError(str(template_path), e) from e

        # Reset timestamps for the new config
        # This makes it a "fresh" config
        now = datetime.now()
        config.created_at = now
        config.updated_at = now

        return config

    def save_as_template(self, config: RBACConfig, template_name: str) -> Path:
        """
        Save a configuration as a reusable template.

        The template will have:
            - customer_name cleared (template is generic)
            - All other settings preserved

        Args:
            config: The configuration to save as template
            template_name: Name for the template (will be slugified)

        Returns:
            Path to the saved template file

        Example:
            storage.save_as_template(config, "enterprise-setup")
        """
        template_slug = slugify(template_name)
        template_path = self.templates_path / f"{template_slug}.json"

        # Create a copy of the config without customer-specific info
        # We'll modify the JSON directly to avoid changing the original
        json_string = config.to_json()
        template_data = json.loads(json_string)

        # Clear customer-specific fields
        template_data["customer_name"] = ""
        template_data["created_at"] = None
        template_data["updated_at"] = None

        # Write the template
        try:
            template_path.write_text(
                json.dumps(template_data, indent=2),
                encoding="utf-8"
            )
        except (IOError, OSError) as e:
            raise ConfigWriteError(str(template_path), e) from e

        return template_path

    # ==========================================================================
    # LESSON 64: Export/Import Operations
    # ==========================================================================

    def export_json(self, config: RBACConfig) -> str:
        """
        Export a configuration as a JSON string.

        Useful for:
            - Download button in UI
            - Sharing via email/Slack
            - Version control

        Args:
            config: The configuration to export

        Returns:
            Pretty-printed JSON string

        Example:
            json_str = storage.export_json(config)
            st.download_button("Download", json_str, "rbac-config.json")
        """
        return config.to_json()

    def import_json(self, json_string: str) -> RBACConfig:
        """
        Import a configuration from a JSON string.

        Useful for:
            - Upload button in UI
            - Pasting shared configs

        Args:
            json_string: JSON string to parse

        Returns:
            Parsed RBACConfig

        Raises:
            ConfigParseError: If JSON is invalid

        Example:
            uploaded = st.file_uploader("Upload config")
            if uploaded:
                config = storage.import_json(uploaded.read())
        """
        try:
            return RBACConfig.from_json(json_string)
        except json.JSONDecodeError as e:
            raise ConfigParseError("uploaded content", e) from e

    # ==========================================================================
    # LESSON 65: History Operations (Private Methods)
    # ==========================================================================
    # Private methods are prefixed with _ to indicate they're internal.
    # They're not part of the public API and may change without notice.

    def _create_backup(self, customer_name: str) -> Path:
        """
        Create a timestamped backup of the current config.

        Called automatically by save() before overwriting.

        Args:
            customer_name: Customer to backup

        Returns:
            Path to the backup file
        """
        config_path = self._get_config_path(customer_name)
        history_path = self._get_history_path(customer_name)

        # Ensure history directory exists
        history_path.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = get_timestamp()
        backup_path = history_path / f"{timestamp}.json"

        # =======================================================================
        # LESSON 66: Copying Files with shutil.copy2()
        # =======================================================================
        # shutil.copy2() copies a file AND its metadata (timestamps, etc.)
        # shutil.copy() only copies the content
        #
        # We use copy2() to preserve the original modification time,
        # which is useful for knowing when the backup was actually made.

        shutil.copy2(config_path, backup_path)

        return backup_path

    def _cleanup_old_backups(self, customer_name: str) -> None:
        """
        Remove old backups exceeding the max_history limit.

        Keeps the most recent backups and deletes the oldest ones.

        Args:
            customer_name: Customer to clean up
        """
        history_path = self._get_history_path(customer_name)

        if not history_path.exists():
            return

        # Get all backups sorted by name (oldest first)
        # Since our timestamp format is sortable, alphabetical = chronological
        backups = sorted(history_path.glob("*.json"))

        # =======================================================================
        # LESSON 67: Cleanup Loop Pattern
        # =======================================================================
        # We remove the OLDEST backups first (beginning of sorted list)
        # until we're at or below the limit.
        #
        # Using while loop because we're modifying the list as we go.

        while len(backups) > self.max_history:
            oldest = backups.pop(0)  # Remove from list
            oldest.unlink()  # Delete the file

    def load_from_history(
        self,
        customer_name: str,
        timestamp: str
    ) -> RBACConfig:
        """
        Load a specific version from history.

        Useful for reverting to a previous version.

        Args:
            customer_name: Customer to load history for
            timestamp: Timestamp of the backup (from list_history())

        Returns:
            RBACConfig from that point in history

        Raises:
            ConfigNotFoundError: If backup doesn't exist

        Example:
            history = storage.list_history("Acme")
            old_config = storage.load_from_history("Acme", history[0])
        """
        history_path = self._get_history_path(customer_name)
        backup_path = history_path / f"{timestamp}.json"

        if not backup_path.exists():
            raise ConfigNotFoundError(
                f"History '{timestamp}' for '{customer_name}'"
            )

        try:
            json_string = backup_path.read_text(encoding="utf-8")
            return RBACConfig.from_json(json_string)
        except json.JSONDecodeError as e:
            raise ConfigParseError(str(backup_path), e) from e

    # ==========================================================================
    # LESSON 68: Cloud Compatibility Methods
    # ==========================================================================
    # These methods help the UI adapt to different deployment environments.
    # On Streamlit Cloud, storage is ephemeral, so we guide users to download.

    def is_persistent(self) -> bool:
        """
        Check if storage is persistent in the current environment.

        Returns:
            True if configs will persist across restarts, False otherwise

        Example:
            if not storage.is_persistent():
                st.warning("Configs won't persist. Download to save!")
        """
        # Import here to avoid circular imports
        from core import is_streamlit_cloud
        return not is_streamlit_cloud()

    def get_save_guidance(self) -> str:
        """
        Get user guidance for saving configurations.

        Returns:
            Guidance message appropriate for the current environment

        Example:
            st.info(storage.get_save_guidance())
        """
        if self.is_persistent():
            return (
                "Your configuration will be saved to the server. "
                "You can also download a copy for backup."
            )
        else:
            return (
                "Running on Streamlit Cloud - configurations are temporary. "
                "**Download your config** to save it permanently."
            )

    def get_load_guidance(self) -> str:
        """
        Get user guidance for loading configurations.

        Returns:
            Guidance message appropriate for the current environment
        """
        if self.is_persistent():
            return "Select a saved configuration or upload a JSON file."
        else:
            return (
                "Upload a previously downloaded config file, "
                "or start from a template."
            )


# =============================================================================
# LESSON 69: Module-Level Code for Testing
# =============================================================================
# The if __name__ == "__main__": block runs only when this file is
# executed directly (python storage.py), not when imported.
#
# Useful for quick testing during development.

if __name__ == "__main__":
    # Quick test of the storage service
    print("Testing StorageService...")

    # Create a test config
    from models import Team, EnvironmentGroup

    config = RBACConfig(
        customer_name="Test Customer",
        project_key="test-project",
        teams=[
            Team(key="dev", name="Developer"),
            Team(key="qa", name="QA Team"),
        ],
        env_groups=[
            EnvironmentGroup(key="production", is_critical=True),
            EnvironmentGroup(key="staging", is_critical=False),
        ],
    )

    # Test storage operations
    storage = StorageService()

    # Save
    path = storage.save(config)
    print(f"Saved to: {path}")

    # Load
    loaded = storage.load("Test Customer")
    print(f"Loaded: {loaded.customer_name}")

    # List
    customers = storage.list_customers()
    print(f"Customers: {customers}")

    # List templates
    templates = storage.list_templates()
    print(f"Templates: {templates}")

    print("\nAll tests passed!")
