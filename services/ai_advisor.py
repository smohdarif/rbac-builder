"""
AI Advisor Service — Gemini-powered RBAC Recommendations
=========================================================

Manages conversations with Google Gemini for RBAC role design.
Uses the new google.genai SDK (not the deprecated google.generativeai).

LESSON: API Client Pattern
============================
This class wraps the Gemini API with:
- Configuration (API key, model, system prompt)
- Session management (chat history preserved across turns)
- Streaming (yield chunks as they arrive for responsive UI)
- Error wrapping (library exceptions → AdvisorError)
- Structured output parsing (extract JSON from markdown response)

See docs/phases/phase27/PYTHON_CONCEPTS.md for detailed explanations.
"""

import json
import re
from typing import Generator, Optional, List, Dict

from google import genai
from google.genai import types

from core.rbac_knowledge import build_system_prompt
from core.ld_actions import (
    get_all_project_permissions,
    get_all_env_permissions,
)


class AdvisorError(Exception):
    """Raised when the AI advisor encounters an error."""
    pass


class RBACAdvisor:
    """
    Manages conversations with Gemini for RBAC recommendations.

    Usage:
        advisor = RBACAdvisor(api_key="your-gemini-key")
        advisor.set_context(teams=["Dev", "QA"], environments=[...], project_key="web")

        # Streaming response
        for chunk in advisor.stream_recommendation("Developers need..."):
            print(chunk, end="")

        # Parse structured output from full response
        matrix = RBACAdvisor.parse_recommendation(full_response_text)
    """

    # =================================================================
    # LESSON: Model Selection
    # =================================================================
    # Gemini 2.5 Flash: fast, cheap, good at structured output.
    MODEL_NAME = "gemini-2.5-flash"

    def __init__(self, api_key: str):
        """
        Initialize the advisor with a Gemini API key.

        Args:
            api_key: Google AI Studio API key

        Raises:
            AdvisorError: If the API key is empty
        """
        if not api_key or not api_key.strip():
            raise AdvisorError("Gemini API key is required")

        # =============================================================
        # LESSON: New google.genai Client
        # =============================================================
        # The new SDK uses a Client object instead of genai.configure().
        # The client is passed to all API calls.
        self.client = genai.Client(
            api_key=api_key,
            http_options={"timeout": 120_000},  # 120 seconds
        )
        self.chat = None
        self.system_prompt: str = ""

    def set_context(
        self,
        teams: List[str],
        environments: List[Dict],
        project_key: str,
    ) -> None:
        """
        Set customer context and initialize a new chat session.

        Builds the system prompt from the knowledge base + customer context,
        then starts a fresh Gemini chat session.
        """
        self.system_prompt = build_system_prompt(
            teams=teams,
            environments=environments,
            project_key=project_key,
            available_project_permissions=get_all_project_permissions(),
            available_env_permissions=get_all_env_permissions(),
        )

        # =============================================================
        # LESSON: Chat Session with System Instruction
        # =============================================================
        # The new SDK uses client.chats.create() with a config object.
        # system_instruction sets the AI's persona (sent once).
        self.chat = self.client.chats.create(
            model=self.MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
            ),
        )

    def stream_recommendation(
        self, user_message: str
    ) -> Generator[str, None, None]:
        """
        Send a message and yield response chunks as they arrive.

        LESSON: Generator Functions
        ============================
        Using 'yield' instead of 'return' makes this a generator.
        Each chunk is yielded as soon as Gemini sends it, so the UI
        can display text progressively (typewriter effect).
        """
        if self.chat is None:
            raise AdvisorError(
                "Context not set. Call set_context() before sending messages."
            )

        try:
            # ==========================================================
            # LESSON: Streaming with the new SDK
            # ==========================================================
            # send_message_stream yields chunks as they arrive.
            for chunk in self.chat.send_message_stream(user_message):
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            raise AdvisorError(f"Gemini API error: {e}") from e

    def get_recommendation(self, user_message: str) -> str:
        """
        Send a message and return the complete response (non-streaming).
        Useful for testing.
        """
        chunks = list(self.stream_recommendation(user_message))
        return "".join(chunks)

    @staticmethod
    def parse_recommendation(response_text: str) -> Optional[Dict]:
        """
        Extract the structured JSON recommendation from the AI response.

        The AI is instructed to include a ```json block at the end.
        This method finds the last such block and parses it.

        LESSON: Regex with re.DOTALL
        =============================
        re.DOTALL makes '.' match newlines too, so we can capture
        multi-line JSON inside the fenced code block.
        We use .*? (non-greedy) to match each block individually.
        We take matches[-1] because the actual recommendation is
        always the last JSON block (earlier blocks may be examples).

        Returns:
            dict with "project" and "environment" keys, or None
        """
        # Find all ```json ... ``` blocks
        pattern = r"```json\s*(.*?)\s*```"
        matches = re.findall(pattern, response_text, re.DOTALL)

        if not matches:
            return None

        try:
            parsed = json.loads(matches[-1])
            # Handle both {"recommendation": {...}} and direct format
            if "recommendation" in parsed:
                return parsed["recommendation"]
            return parsed
        except json.JSONDecodeError:
            return None
