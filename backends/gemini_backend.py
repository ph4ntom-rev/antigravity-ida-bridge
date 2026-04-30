"""
Antigravity IDA Bridge — Gemini Backend
=========================================
Google Gemini with native function calling.

Changes (v5.2):
- Uses classmethods for metadata
- Proper reset() lifecycle with chat session recreation
- Error handling for Gemini exceptions
"""

import os
import logging
from .base import AgentBackend

logger = logging.getLogger("Antigravity.Bridge")

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    genai = None
    types = None
    HAS_GENAI = False


@AgentBackend.register("gemini")
class GeminiBackend(AgentBackend):

    @classmethod
    def get_name(cls) -> str:
        return "Gemini"

    @classmethod
    def get_default_model(cls) -> str:
        return os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")

    @classmethod
    def is_available(cls) -> bool:
        return HAS_GENAI and bool(os.environ.get("GEMINI_API_KEY"))

    def reset(self) -> None:
        # Gemini manages its own history via chat session
        self.history = []
        if not self.is_available():
            self._chat_session = None
            return

        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
        config = types.GenerateContentConfig(
            system_instruction=self.get_system_prompt(),
            tools=[self.execute_idapython, self.call_bridge_api],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
            temperature=0.2,
        )
        self._chat_session = client.chats.create(model=self.model, config=config)

    def chat(self, message: str) -> str:
        if getattr(self, "_chat_session", None) is None:
            return "[Error: Gemini client not initialized]"

        try:
            response = self._chat_session.send_message(message)
            return response.text
        except Exception as e:
            logger.exception("Gemini execution failed")
            return f"[Error: {str(e)}]"
