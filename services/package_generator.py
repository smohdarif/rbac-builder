"""
Package Generator Service
=========================

Generates a self-contained client delivery ZIP package.

The client receives a ZIP they can unzip and run one command:
    pip install requests
    python deploy.py

LESSON: In-Memory ZIP with BytesIO
====================================
We use io.BytesIO as an in-memory buffer — it behaves like a file
but lives entirely in RAM. No temporary files on disk are needed,
which is important for Streamlit Cloud where the filesystem is ephemeral.

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("file.txt", "content")
    return buffer.getvalue()  # → bytes

LESSON: Code Generation
========================
deploy.py is a Python script we generate dynamically as a string.
We embed the customer name and project key into the script header.
The trick: use {{ and }} for literal braces inside f-strings.
"""

import io
import json
import textwrap
import zipfile
from datetime import datetime
from typing import List, Tuple

from services.payload_builder import DeployPayload


class PackageGenerationError(Exception):
    """Raised when package generation fails."""
    pass


class PackageGenerator:
    """
    Generates a self-contained client delivery ZIP package.

    ZIP contents:
        {slug}_rbac_deployment/
        ├── README.md
        ├── deploy.py
        ├── requirements.txt
        ├── settings.json
        ├── rollback.json
        ├── 01_roles/
        │   ├── 01_create-flags.json
        │   └── ...
        └── 02_teams/
            └── 01_{team-key}.json

    Usage:
        generator = PackageGenerator(payload, "voya-web")
        zip_bytes = generator.generate_package()
        st.download_button(data=zip_bytes, ...)
    """

    def __init__(self, payload: DeployPayload, project_key: str):
        """
        Initialise the generator.

        Args:
            payload: The built DeployPayload containing roles and teams
            project_key: LaunchDarkly project key (e.g. "voya-web")
        """
        if not payload.roles and not payload.teams:
            raise PackageGenerationError(
                "Cannot generate package: payload has no roles or teams."
            )

        self.payload = payload
        self.project_key = project_key
        # =================================================================
        # LESSON: slugify — make a string safe for use in filenames/paths
        # Lower case, replace spaces and special chars with underscores
        # =================================================================
        self.customer_slug = (
            payload.customer_name
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
        self.root = f"{self.customer_slug}_rbac_deployment"

    # =========================================================================
    # PUBLIC: Main entry point
    # =========================================================================

    def generate_package(self) -> bytes:
        """
        Build the complete ZIP package and return as bytes.

        LESSON: context manager (with statement)
        =========================================
        'with zipfile.ZipFile(...) as zf:' ensures the ZIP is properly
        finalised and closed even if an error occurs inside the block.
        This is the same principle as 'with open(...) as f:' for files.

        Returns:
            bytes: Complete ZIP file, ready to pass to st.download_button
        """
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:

            # ── Role files (01_roles/) ────────────────────────────────────
            for filename, content in self._build_role_files():
                zf.writestr(f"{self.root}/01_roles/{filename}", content)

            # ── Team files (02_teams/) ────────────────────────────────────
            for filename, content in self._build_team_files():
                zf.writestr(f"{self.root}/02_teams/{filename}", content)

            # ── Supporting files ──────────────────────────────────────────
            zf.writestr(f"{self.root}/deploy.py",        self._build_deploy_script())
            zf.writestr(f"{self.root}/settings.json",    self._build_settings_template())
            zf.writestr(f"{self.root}/requirements.txt", "requests>=2.28.0\n")
            zf.writestr(f"{self.root}/rollback.json",    "{}")
            zf.writestr(f"{self.root}/README.md",        self._build_readme())

        return buffer.getvalue()

    # =========================================================================
    # PRIVATE: File builders
    # =========================================================================

    def _build_role_files(self) -> List[Tuple[str, str]]:
        """
        Build one (filename, json_content) tuple per role.

        LESSON: str.zfill() — zero-padding numbers
        ============================================
        Files are prefixed with a zero-padded number so they sort
        correctly in any file browser:
            str(1).zfill(2)  → "01"   (not "1")
            str(10).zfill(2) → "10"
        Without zero-padding, "10_..." sorts before "2_..." alphabetically.

        Returns:
            List of (filename, json_string) tuples
        """
        files = []
        for index, role in enumerate(self.payload.roles, start=1):
            # =================================================================
            # Strip to only LD API fields — no rbac-builder internal metadata
            # =================================================================
            role_payload = {
                "key":              role["key"],
                "name":             role["name"],
                "description":      role.get("description", ""),
                "base_permissions": role.get("base_permissions", "no_access"),
                "policy":           role["policy"],
            }
            prefix   = str(index).zfill(2)
            filename = f"{prefix}_{role['key']}.json"
            files.append((filename, json.dumps(role_payload, indent=2)))

        return files

    def _build_team_files(self) -> List[Tuple[str, str]]:
        """
        Build one (filename, json_content) tuple per team.

        Returns:
            List of (filename, json_string) tuples
        """
        files = []
        for index, team in enumerate(self.payload.teams, start=1):
            team_payload = {
                "key":            team["key"],
                "name":           team["name"],
                "description":    team.get("description", ""),
                "customRoleKeys": team["customRoleKeys"],
                "roleAttributes": team["roleAttributes"],
            }
            prefix   = str(index).zfill(2)
            filename = f"{prefix}_{team['key']}.json"
            files.append((filename, json.dumps(team_payload, indent=2)))

        return files

    def _build_settings_template(self) -> str:
        """Returns the settings.json template the client fills in."""
        settings = {
            "api_key":                    "YOUR_API_KEY_HERE",
            "base_url":                   "https://app.launchdarkly.com",
            "dry_run":                    False,
            "rate_limit_pause_seconds":   0.2,
        }
        return json.dumps(settings, indent=2)

    def _build_readme(self) -> str:
        """Returns a README.md with deployment instructions."""
        from services.doc_generator import generate_deployment_guide
        return generate_deployment_guide(self.payload, self.project_key)

    # =========================================================================
    # PRIVATE: deploy.py script generator
    # =========================================================================

    def _build_deploy_script(self) -> str:
        """
        Generate the complete deploy.py script as a string.

        LESSON: Code generation with placeholder replacement
        ====================================================
        Generating code that contains its own { } braces inside an f-string
        requires escaping every brace ({{ → {, }} → }), which is error-prone
        in a large script. Instead, we write the script as a plain string with
        uppercase placeholder markers (__CUSTOMER__, __PROJECT__, etc.) and
        then do simple string replacements at the end.

        This keeps the template readable and avoids escaping mistakes.

        Returns:
            str: Complete Python script content
        """
        generated_at = datetime.now().strftime("%Y-%m-%d")
        role_count   = self.payload.get_role_count()
        team_count   = self.payload.get_team_count()

        # =================================================================
        # LESSON: textwrap.dedent
        # ========================
        # Removes the common leading whitespace from all lines in a string.
        # =================================================================

        # Write the script as a plain string — no f-prefix, no brace escaping.
        # __PLACEHOLDER__ markers are replaced with actual values below.
        template = textwrap.dedent("""\
            #!/usr/bin/env python3
            '''
            LaunchDarkly RBAC Deployment Script
            ====================================
            Customer : __CUSTOMER__
            Project  : __PROJECT__
            Generated: __DATE__
            Roles    : __ROLE_COUNT__
            Teams    : __TEAM_COUNT__

            Usage
            -----
            Requirements: Python 3.8+ and the requests library.

              pip install requests
              python deploy.py

            Set "dry_run": true in settings.json to preview without making API calls.
            '''

            import json
            import sys
            import time
            from pathlib import Path

            import requests

            # ── Constants baked in at generation time ──────────────────────────────
            CUSTOMER_NAME = "__CUSTOMER__"
            PROJECT_KEY   = "__PROJECT__"

            # ── Paths ──────────────────────────────────────────────────────────────
            BASE_DIR      = Path(__file__).parent
            ROLES_DIR     = BASE_DIR / "01_roles"
            TEAMS_DIR     = BASE_DIR / "02_teams"
            SETTINGS_FILE = BASE_DIR / "settings.json"
            ROLLBACK_FILE = BASE_DIR / "rollback.json"


            # ── Settings ───────────────────────────────────────────────────────────

            def load_settings():
                if not SETTINGS_FILE.exists():
                    print("Error: settings.json not found. Did you unzip the package correctly?")
                    sys.exit(1)
                with open(SETTINGS_FILE) as f:
                    return json.load(f)


            def validate_settings(settings):
                if settings.get("api_key") == "YOUR_API_KEY_HERE":
                    print("Error: Please set your API key in settings.json before running.")
                    sys.exit(1)


            # ── LD API Client ──────────────────────────────────────────────────────

            class LDClient:

                def __init__(self, api_key, base_url):
                    self.base_url = base_url.rstrip("/")
                    self.headers  = {
                        "Authorization": api_key,
                        "Content-Type":  "application/json",
                    }

                def _post(self, path, data):
                    url  = self.base_url + path
                    resp = requests.post(url, headers=self.headers, json=data, timeout=30)
                    if resp.status_code == 429:
                        time.sleep(1)
                        resp = requests.post(url, headers=self.headers, json=data, timeout=30)
                    return resp

                def _get(self, path):
                    return requests.get(self.base_url + path, headers=self.headers, timeout=30)

                def role_exists(self, key):
                    return self._get("/api/v2/roles/" + key).status_code == 200

                def team_exists(self, key):
                    return self._get("/api/v2/teams/" + key).status_code == 200

                def create_role(self, role):
                    return self._post("/api/v2/roles", role)

                def create_team(self, team):
                    return self._post("/api/v2/teams", team)


            # ── Result tracking ────────────────────────────────────────────────────

            class DeployResult:
                def __init__(self):
                    self.created = []
                    self.skipped = []
                    self.failed  = []
                    self.errors  = {}

                @property
                def all_failed(self):
                    return len(self.failed) > 0 and len(self.created) == 0 and len(self.skipped) == 0


            # ── File loader ────────────────────────────────────────────────────────

            def load_json_files(directory):
                files  = sorted(directory.glob("*.json"))
                result = []
                for f in files:
                    with open(f) as fp:
                        result.append((f.name, json.load(fp)))
                return result


            # ── Deployment logic ───────────────────────────────────────────────────

            class Deployer:

                def __init__(self, settings):
                    self.client  = LDClient(
                        settings["api_key"],
                        settings.get("base_url", "https://app.launchdarkly.com")
                    )
                    self.dry_run = settings.get("dry_run", False)
                    self.pause   = settings.get("rate_limit_pause_seconds", 0.2)

                def run(self):
                    print()
                    print("=" * 56)
                    print("  LaunchDarkly RBAC Deployment")
                    print("  Customer: " + CUSTOMER_NAME)
                    print("  Project:  " + PROJECT_KEY)
                    print("=" * 56)
                    if self.dry_run:
                        print("  [DRY RUN - no API calls will be made]")
                    print()

                    role_result = self._deploy_resources(
                        ROLES_DIR, "Custom Roles",
                        self.client.role_exists, self.client.create_role
                    )

                    if role_result.all_failed:
                        print("ERROR: All roles failed. Aborting — teams require roles to exist first.")
                        self._print_summary(role_result, DeployResult())
                        sys.exit(1)

                    team_result = self._deploy_resources(
                        TEAMS_DIR, "Teams",
                        self.client.team_exists, self.client.create_team
                    )

                    self._print_summary(role_result, team_result)

                    if not self.dry_run:
                        self._write_rollback(role_result.created, team_result.created)
                        print("  Rollback file written: rollback.json")

                    total_failed = len(role_result.failed) + len(team_result.failed)
                    if total_failed > 0:
                        print("WARNING: Deployment completed with " + str(total_failed) + " failure(s). Check errors above.")
                        sys.exit(1)
                    else:
                        print("Deployment complete!")

                def _deploy_resources(self, directory, label, exists_fn, create_fn):
                    result = DeployResult()
                    files  = load_json_files(directory)

                    print("-- " + label + " (" + str(len(files)) + " resources) --")
                    print()

                    for filename, data in files:
                        key = data.get("key", filename)

                        if self.dry_run:
                            print("  [DRY RUN] " + key)
                            result.created.append(key)
                            continue

                        if exists_fn(key):
                            print("  SKIP  " + key + " (already exists)")
                            result.skipped.append(key)
                            continue

                        resp = create_fn(data)

                        if resp.status_code in (200, 201):
                            print("  OK    " + key)
                            result.created.append(key)
                        elif resp.status_code == 401:
                            print("  ERROR " + key + " - 401 Unauthorized. Check your API key.")
                            sys.exit(1)
                        elif resp.status_code == 403:
                            print("  ERROR " + key + " - 403 Forbidden. Insufficient permissions.")
                            sys.exit(1)
                        else:
                            error = resp.text[:200]
                            print("  FAIL  " + key + " (" + str(resp.status_code) + "): " + error)
                            result.failed.append(key)
                            result.errors[key] = str(resp.status_code) + ": " + error

                        time.sleep(self.pause)

                    print()
                    return result

                def _print_summary(self, role_result, team_result):
                    print("-- Summary --")
                    print("  Roles: " + str(len(role_result.created)) + " created, " +
                          str(len(role_result.skipped)) + " skipped, " +
                          str(len(role_result.failed)) + " failed")
                    print("  Teams: " + str(len(team_result.created)) + " created, " +
                          str(len(team_result.skipped)) + " skipped, " +
                          str(len(team_result.failed)) + " failed")
                    if role_result.errors or team_result.errors:
                        print("  Errors:")
                        all_errors = {}
                        all_errors.update(role_result.errors)
                        all_errors.update(team_result.errors)
                        for key, msg in all_errors.items():
                            print("    " + key + ": " + msg)
                    print()

                def _write_rollback(self, created_roles, created_teams):
                    import datetime
                    rollback = {
                        "deployed_at":   datetime.datetime.now().isoformat(),
                        "customer":      CUSTOMER_NAME,
                        "project":       PROJECT_KEY,
                        "created_roles": created_roles,
                        "created_teams": created_teams,
                        "rollback_commands": (
                            ["DELETE /api/v2/teams/" + k for k in reversed(created_teams)] +
                            ["DELETE /api/v2/roles/"  + k for k in reversed(created_roles)]
                        ),
                    }
                    with open(ROLLBACK_FILE, "w") as f:
                        json.dump(rollback, f, indent=2)


            # ── Entry point ────────────────────────────────────────────────────────

            if __name__ == "__main__":
                settings = load_settings()
                validate_settings(settings)
                deployer  = Deployer(settings)
                deployer.run()
        """)

        # Replace placeholders with actual values
        return (
            template
            .replace("__CUSTOMER__",   self.payload.customer_name)
            .replace("__PROJECT__",    self.project_key)
            .replace("__DATE__",       generated_at)
            .replace("__ROLE_COUNT__", str(role_count))
            .replace("__TEAM_COUNT__", str(team_count))
        )
