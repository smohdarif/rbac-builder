"""
Terraform Generator Service
============================

Generates a complete, runnable Terraform package from a DeployPayload.

The client unzips the package and runs:
    terraform init
    terraform plan
    terraform apply

LESSON: Code Generation
========================
This module generates HCL (HashiCorp Configuration Language) text files
from Python data. The key challenge: LaunchDarkly uses ${roleAttribute/...}
placeholders in resource strings, but HCL also uses ${...} for its own
interpolation. We must escape ${ → $${ so HCL passes them through unchanged.

See docs/phases/phase16/TERRAFORM_CONCEPTS.md for a full explanation.
"""

import io
import textwrap
import zipfile
from datetime import datetime
from typing import Dict, List, Set

from services.payload_builder import DeployPayload


class TerraformGenerationError(Exception):
    """Raised when Terraform package generation fails."""
    pass


# =============================================================================
# LESSON: HCL formatting helpers
# =============================================================================

def tf_resource_name(key: str) -> str:
    """
    Convert a LaunchDarkly key to a valid Terraform resource name.

    Terraform resource names must be valid identifiers:
    letters, digits, underscores — NO hyphens.

    Example:
        >>> tf_resource_name("create-flags")
        'create_flags'
        >>> tf_resource_name("voya-web-dev")
        'voya_web_dev'
    """
    return key.replace("-", "_")


def hcl_list(values: List[str]) -> str:
    """
    Format a Python list as an HCL list literal.

    Example:
        >>> hcl_list(["production", "staging"])
        '["production", "staging"]'
    """
    items = ", ".join(f'"{v}"' for v in values)
    return f"[{items}]"


def hcl_list_escaped(resources: List[str]) -> str:
    """
    Format resource strings for HCL, escaping ${...} placeholders.

    LESSON: The escaping problem
    ==============================
    JSON uses ${roleAttribute/projects} — just a plain string.
    HCL uses ${...} for its own interpolation. If we put
    ${roleAttribute/projects} in an HCL string, Terraform tries to
    evaluate it as a variable reference and fails.

    Fix: replace ${ with $${ — HCL outputs ${ as a literal character.

    Example:
        JSON:  "proj/${roleAttribute/projects}:env/*:flag/*"
        HCL:   ["proj/$${roleAttribute/projects}:env/*:flag/*"]
        LD:    "proj/${roleAttribute/projects}:env/*:flag/*"   ← correct

        >>> hcl_list_escaped(["proj/${roleAttribute/projects}:env/*:flag/*"])
        '["proj/$${roleAttribute/projects}:env/*:flag/*"]'
    """
    escaped = [r.replace("${", "$${") for r in resources]
    return hcl_list(escaped)


# =============================================================================
# Main class
# =============================================================================

class TerraformGenerator:
    """
    Generates a complete Terraform package as a ZIP of .tf files.

    Usage:
        generator = TerraformGenerator(payload, "voya-web")
        zip_bytes = generator.generate_package()
        st.download_button(data=zip_bytes, ...)
    """

    def __init__(self, payload: DeployPayload, project_key: str):
        """
        Args:
            payload:     The built DeployPayload containing roles and teams
            project_key: LaunchDarkly project key (e.g. "voya-web")
        """
        if not payload.roles and not payload.teams:
            raise TerraformGenerationError(
                "Cannot generate Terraform: payload has no roles or teams."
            )

        self.payload     = payload
        self.project_key = project_key
        # Slugify customer name for use in file/folder names
        self.slug = (
            payload.customer_name
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
        self.root = f"{self.slug}_terraform"

    # =========================================================================
    # PUBLIC: Main entry point
    # =========================================================================

    def generate_package(self) -> bytes:
        """
        Build the complete Terraform ZIP and return as bytes.

        LESSON: Same BytesIO + ZipFile pattern as Phase 13 PackageGenerator.
        In-memory ZIP — no disk write needed, works on Streamlit Cloud.

        Returns:
            bytes: ZIP file contents, ready for st.download_button
        """
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{self.root}/providers.tf",  self._build_providers_tf())
            zf.writestr(f"{self.root}/variables.tf",  self._build_variables_tf())
            zf.writestr(f"{self.root}/main.tf",       self._build_main_tf())
            zf.writestr(f"{self.root}/README.md",     self._build_readme())

        return buffer.getvalue()

    # =========================================================================
    # PRIVATE: Static file builders
    # =========================================================================

    def _build_providers_tf(self) -> str:
        """
        Returns the providers.tf content (always the same).

        Tells Terraform which provider to use (LaunchDarkly) and
        where to find the API key (from a variable).
        """
        return textwrap.dedent("""\
            terraform {
              required_providers {
                launchdarkly = {
                  source  = "launchdarkly/launchdarkly"
                  version = "~> 2.25"
                }
              }
              required_version = ">= 1.0"
            }

            provider "launchdarkly" {
              access_token = var.launchdarkly_access_token
            }
        """)

    def _build_variables_tf(self) -> str:
        """
        Returns the variables.tf content (always the same).

        Declares the API key as a sensitive variable so it is
        never printed in Terraform logs or plan output.
        """
        return textwrap.dedent("""\
            variable "launchdarkly_access_token" {
              type        = string
              description = "LaunchDarkly API access token with createRole and createTeam permissions"
              sensitive   = true
            }
        """)

    # =========================================================================
    # PRIVATE: Dynamic main.tf builder
    # =========================================================================

    def _build_main_tf(self) -> str:
        """
        Dynamically generate main.tf from the payload.

        Structure:
          1. Header comment (customer, project, date, counts)
          2. Custom role resources (one per role)
          3. Team resources (one per team)
        """
        generated_at = datetime.now().strftime("%Y-%m-%d")
        sections = []

        # Header comment
        sections.append(textwrap.dedent(f"""\
            /**
             * Generated by RBAC Builder
             * Customer  : {self.payload.customer_name}
             * Project   : {self.project_key}
             * Generated : {generated_at}
             * Roles     : {self.payload.get_role_count()}
             * Teams     : {self.payload.get_team_count()}
             *
             * Usage:
             *   terraform init
             *   terraform plan
             *   terraform apply
             */"""))

        # Custom roles section
        sections.append(
            "# " + "─" * 76 + "\n"
            "# Custom Roles — create these first\n"
            "# " + "─" * 76
        )
        for role in self.payload.roles:
            sections.append(self._role_to_hcl(role))

        # Teams section
        role_keys: Set[str] = {role["key"] for role in self.payload.roles}
        sections.append(
            "# " + "─" * 76 + "\n"
            "# Teams — created after all custom roles exist\n"
            "# " + "─" * 76
        )
        for team in self.payload.teams:
            sections.append(self._team_to_hcl(team, role_keys))

        return "\n\n".join(sections) + "\n"

    # =========================================================================
    # PRIVATE: HCL resource builders
    # =========================================================================

    def _role_to_hcl(self, role: Dict) -> str:
        """
        Convert one role dict to a launchdarkly_custom_role HCL block.

        LESSON: Building HCL block as a list of lines, joined at the end.
        More readable than string concatenation. The resource name uses
        underscores (hyphens are not valid in HCL identifiers).

        Args:
            role: Role dict with key, name, description, base_permissions, policy

        Returns:
            Complete HCL resource block as a string
        """
        resource_name = tf_resource_name(role["key"])
        lines = [
            f'resource "launchdarkly_custom_role" "{resource_name}" {{',
            f'  key              = "{role["key"]}"',
            f'  name             = "{role["name"]}"',
            f'  description      = "{role.get("description", "")}"',
            f'  base_permissions = "no_access"',
            "",
        ]

        for stmt in role.get("policy", []):
            lines += [
                "  policy_statements {",
                f'    effect    = "{stmt["effect"]}"',
                f'    actions   = {hcl_list(stmt["actions"])}',
                f'    resources = {hcl_list_escaped(stmt["resources"])}',
                "  }",
                "",
            ]

        lines.append("}")
        return "\n".join(lines)

    def _team_to_hcl(self, team: Dict, role_keys: Set[str]) -> str:
        """
        Convert one team dict to a launchdarkly_team HCL block.

        LESSON: Resource references vs string literals
        ================================================
        We use launchdarkly_custom_role.create_flags.key (a TF reference)
        instead of "create-flags" (a string). This creates a dependency
        graph: Terraform knows to create roles before teams.

        We only reference roles that ARE in our payload (role_keys set).
        Any extra keys (e.g. global roles like view_teams that we don't
        generate) are silently skipped to avoid broken TF references.

        Args:
            team:      Team dict with key, name, description, customRoleKeys, roleAttributes
            role_keys: Set of role keys present in the payload

        Returns:
            Complete HCL resource block as a string
        """
        resource_name = tf_resource_name(team["key"])

        # Build role references (TF resource references, not string literals)
        role_refs = [
            f"    launchdarkly_custom_role.{tf_resource_name(k)}.key,"
            for k in team.get("customRoleKeys", [])
            if k in role_keys   # only reference roles we generated
        ]

        lines = [
            f'resource "launchdarkly_team" "{resource_name}" {{',
            f'  key         = "{team["key"]}"',
            f'  name        = "{team["name"]}"',
            f'  description = "{team.get("description", "")}"',
            "",
        ]

        if role_refs:
            lines.append("  custom_role_keys = [")
            lines.extend(role_refs)
            lines.append("  ]")
            lines.append("")

        # Role attributes blocks
        for attr in team.get("roleAttributes", []):
            lines += [
                "  role_attributes {",
                f'    key    = "{attr["key"]}"',
                f'    values = {hcl_list(attr["values"])}',
                "  }",
                "",
            ]

        # lifecycle block — always present to protect member assignments
        lines += [
            "  lifecycle {",
            "    ignore_changes = [member_ids, maintainers]",
            "  }",
            "}",
        ]

        return "\n".join(lines)

    def _build_readme(self) -> str:
        """Returns a README.md with Terraform usage instructions."""
        generated_at = datetime.now().strftime("%Y-%m-%d")
        return textwrap.dedent(f"""\
            # LaunchDarkly RBAC — Terraform Configuration

            | Field | Value |
            |-------|-------|
            | **Customer** | {self.payload.customer_name} |
            | **Project** | `{self.project_key}` |
            | **Generated** | {generated_at} |
            | **Custom Roles** | {self.payload.get_role_count()} |
            | **Teams** | {self.payload.get_team_count()} |

            ---

            ## Prerequisites

            - [Terraform CLI](https://developer.hashicorp.com/terraform/install) >= 1.0
            - LaunchDarkly API access token with **Admin** or **Owner** role

            ## Deployment

            ```bash
            # 1. Provide your API key (never hardcode it)
            export TF_VAR_launchdarkly_access_token="api-xxxxxxxxxxxxxxxx"

            # 2. Download the LaunchDarkly provider plugin (once)
            terraform init

            # 3. Preview what will be created (no changes made)
            terraform plan

            # 4. Create all roles and teams
            terraform apply
            ```

            ## Deployment Order

            Terraform automatically creates **custom roles before teams**
            because teams reference role resources (`launchdarkly_custom_role.xxx.key`).

            ## Important Notes

            - **`terraform.tfstate`**: Created after apply. Keep this file — it's Terraform's memory of what it created.
            - **Members**: Team members are managed outside Terraform (via SSO/SCIM or LD UI). The `lifecycle {{ ignore_changes = [member_ids] }}` block prevents Terraform from removing members.
            - **Role attributes**: The `role_attributes` blocks on each team fill in the `${{roleAttribute/...}}` placeholders in role resource strings at runtime in LD.
        """)
