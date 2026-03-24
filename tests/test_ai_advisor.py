"""
Tests for Phase 27: AI Advisor
===============================

Tests the RBAC knowledge base, prompt building, response parsing,
and recommendation application logic.

We mock the Gemini API — no real API calls in tests.

Run with: pytest tests/test_ai_advisor.py -v
"""

import json

import pandas as pd
import pytest

from core.rbac_knowledge import (
    build_system_prompt,
    TEAM_ARCHETYPES,
    ENVIRONMENT_PATTERNS,
    PERMISSION_REFERENCE,
    ANTI_PATTERNS,
    FEW_SHOT_EXAMPLE,
)
from services.ai_advisor import RBACAdvisor, AdvisorError


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_teams():
    return ["Developer", "QA"]


@pytest.fixture
def sample_environments():
    return [
        {"key": "test", "critical": False},
        {"key": "production", "critical": True},
    ]


@pytest.fixture
def sample_project_key():
    return "voya-web"


@pytest.fixture
def sample_recommendation():
    """A realistic recommendation JSON matching our output format."""
    return {
        "project": {
            "Developer": {
                "Create Flags": True,
                "Update Flags": True,
                "View Project": True,
            },
            "QA": {
                "View Project": True,
            },
        },
        "environment": {
            "Developer": {
                "test": {
                    "Update Targeting": True,
                    "Manage Segments": True,
                },
                "production": {
                    "Update Targeting": True,
                },
            },
            "QA": {
                "test": {
                    "Update Targeting": True,
                    "Manage Segments": True,
                },
                "production": {
                    "Review Changes": True,
                },
            },
        },
    }


# =============================================================================
# Group 1: Knowledge Base & Prompt Building (TC-AI-01 to TC-AI-04)
# =============================================================================

class TestPromptBuilding:

    def test_system_prompt_includes_customer_context(
        self, sample_teams, sample_environments, sample_project_key
    ):
        """TC-AI-01: System prompt includes customer teams, envs, project."""
        result = build_system_prompt(
            teams=sample_teams,
            environments=sample_environments,
            project_key=sample_project_key,
            available_project_permissions=["Create Flags", "View Project"],
            available_env_permissions=["Update Targeting"],
        )
        assert "voya-web" in result
        assert "Developer" in result
        assert "QA" in result
        assert "test" in result
        assert "production" in result
        assert "critical" in result

    def test_system_prompt_includes_knowledge_sections(
        self, sample_teams, sample_environments, sample_project_key
    ):
        """TC-AI-02: System prompt includes all knowledge base sections."""
        result = build_system_prompt(
            teams=sample_teams,
            environments=sample_environments,
            project_key=sample_project_key,
            available_project_permissions=["Create Flags"],
            available_env_permissions=["Update Targeting"],
        )
        assert "Team Archetypes" in result
        assert "Environment Classification" in result
        assert "Permission Quick Reference" in result
        assert "Anti-Patterns" in result

    def test_system_prompt_includes_available_permissions(
        self, sample_teams, sample_environments, sample_project_key
    ):
        """TC-AI-03: System prompt lists available permissions."""
        result = build_system_prompt(
            teams=sample_teams,
            environments=sample_environments,
            project_key=sample_project_key,
            available_project_permissions=["Create Flags", "Update Flags"],
            available_env_permissions=["Update Targeting", "Manage Segments"],
        )
        assert "Create Flags" in result
        assert "Update Flags" in result
        assert "Update Targeting" in result
        assert "Manage Segments" in result

    def test_system_prompt_handles_empty_context(self):
        """TC-AI-04: Empty context doesn't crash, uses placeholder text."""
        result = build_system_prompt(
            teams=[],
            environments=[],
            project_key="",
            available_project_permissions=[],
            available_env_permissions=[],
        )
        assert "not set yet" in result or "none configured" in result
        assert isinstance(result, str)
        assert len(result) > 100

    def test_system_prompt_includes_guardrails(
        self, sample_teams, sample_environments, sample_project_key
    ):
        """System prompt includes scope guardrails."""
        result = build_system_prompt(
            teams=sample_teams,
            environments=sample_environments,
            project_key=sample_project_key,
            available_project_permissions=["Create Flags"],
            available_env_permissions=["Update Targeting"],
        )
        assert "SCOPE GUARDRAILS" in result
        assert "NOT ALLOWED" in result
        assert "RBAC Advisor" in result

    def test_system_prompt_includes_few_shot_example(
        self, sample_teams, sample_environments, sample_project_key
    ):
        """System prompt includes a few-shot example."""
        result = build_system_prompt(
            teams=sample_teams,
            environments=sample_environments,
            project_key=sample_project_key,
            available_project_permissions=["Create Flags"],
            available_env_permissions=["Update Targeting"],
        )
        assert "EXAMPLE CONVERSATION" in result
        assert '"recommendation"' in result


# =============================================================================
# Group 2: Response Parsing (TC-AI-05 to TC-AI-08)
# =============================================================================

class TestResponseParsing:

    def test_parse_valid_json_recommendation(self):
        """TC-AI-05: Parse valid JSON recommendation from response."""
        response = (
            "Here is my recommendation:\n\n"
            "```json\n"
            '{"recommendation": {"project": {"Dev": {"Create Flags": true}}, '
            '"environment": {"Dev": {"test": {"Update Targeting": true}}}}}\n'
            "```"
        )
        result = RBACAdvisor.parse_recommendation(response)
        assert result is not None
        assert "project" in result
        assert result["project"]["Dev"]["Create Flags"] is True

    def test_parse_response_with_no_json(self):
        """TC-AI-06: Returns None when no JSON block found."""
        response = "I recommend giving developers access to create flags."
        result = RBACAdvisor.parse_recommendation(response)
        assert result is None

    def test_parse_response_with_invalid_json(self):
        """TC-AI-07: Returns None for malformed JSON (no exception)."""
        response = "```json\n{invalid json here}\n```"
        result = RBACAdvisor.parse_recommendation(response)
        assert result is None

    def test_parse_response_uses_last_json_block(self):
        """TC-AI-08: When multiple JSON blocks exist, uses the last one."""
        response = (
            "Here's an example:\n"
            '```json\n{"example": true}\n```\n\n'
            "And here's the actual recommendation:\n"
            '```json\n{"recommendation": {"project": {"QA": {"View Project": true}}, '
            '"environment": {}}}\n```'
        )
        result = RBACAdvisor.parse_recommendation(response)
        assert result is not None
        assert "project" in result
        assert "QA" in result["project"]

    def test_parse_direct_format_without_recommendation_key(self):
        """Handles JSON without 'recommendation' wrapper."""
        response = (
            '```json\n{"project": {"Dev": {"View Project": true}}, '
            '"environment": {}}\n```'
        )
        result = RBACAdvisor.parse_recommendation(response)
        assert result is not None
        assert "project" in result

    def test_parse_multiline_json(self):
        """Handles pretty-printed multi-line JSON."""
        response = (
            "```json\n"
            "{\n"
            '  "recommendation": {\n'
            '    "project": {\n'
            '      "Developer": {\n'
            '        "Create Flags": true,\n'
            '        "View Project": true\n'
            "      }\n"
            "    },\n"
            '    "environment": {}\n'
            "  }\n"
            "}\n"
            "```"
        )
        result = RBACAdvisor.parse_recommendation(response)
        assert result is not None
        assert result["project"]["Developer"]["Create Flags"] is True


# =============================================================================
# Group 3: Error Handling (TC-AI-11 to TC-AI-12)
# =============================================================================

class TestErrorHandling:

    def test_empty_api_key_raises_error(self):
        """TC-AI-11: Empty API key raises AdvisorError."""
        with pytest.raises(AdvisorError, match="API key is required"):
            RBACAdvisor("")

    def test_whitespace_api_key_raises_error(self):
        """Whitespace-only API key raises AdvisorError."""
        with pytest.raises(AdvisorError, match="API key is required"):
            RBACAdvisor("   ")

    def test_stream_before_set_context_raises_error(self):
        """TC-AI-12: Streaming before set_context raises AdvisorError."""
        advisor = RBACAdvisor("fake-key-for-testing")
        with pytest.raises(AdvisorError, match="Context not set"):
            list(advisor.stream_recommendation("hello"))


# =============================================================================
# Group 4: Knowledge Base Constants
# =============================================================================

class TestKnowledgeBase:

    def test_team_archetypes_covers_common_types(self):
        """Knowledge base covers standard team archetypes."""
        assert "Developer" in TEAM_ARCHETYPES
        assert "QA" in TEAM_ARCHETYPES
        assert "SRE" in TEAM_ARCHETYPES
        assert "Product" in TEAM_ARCHETYPES
        assert "Release Manager" in TEAM_ARCHETYPES

    def test_environment_patterns_covers_critical(self):
        """Knowledge base covers critical vs non-critical patterns."""
        assert "Critical" in ENVIRONMENT_PATTERNS
        assert "Non-Critical" in ENVIRONMENT_PATTERNS
        assert "Separation of Duties" in ENVIRONMENT_PATTERNS

    def test_permission_reference_covers_all_scopes(self):
        """Knowledge base covers project and environment scoped permissions."""
        assert "Project-Scoped" in PERMISSION_REFERENCE
        assert "Environment-Scoped" in PERMISSION_REFERENCE
        assert "Observability" in PERMISSION_REFERENCE
        assert "View Project" in PERMISSION_REFERENCE

    def test_anti_patterns_has_entries(self):
        """Anti-patterns list is non-empty and covers key issues."""
        assert "Admin" in ANTI_PATTERNS
        assert "View Project" in ANTI_PATTERNS
        assert "separation of duties" in ANTI_PATTERNS.lower()

    def test_few_shot_example_has_json(self):
        """Few-shot example includes parseable JSON."""
        assert "```json" in FEW_SHOT_EXAMPLE
        assert '"recommendation"' in FEW_SHOT_EXAMPLE
        assert '"project"' in FEW_SHOT_EXAMPLE
        assert '"environment"' in FEW_SHOT_EXAMPLE
