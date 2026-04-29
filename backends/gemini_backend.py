"""
Antigravity IDA Bridge — Gemini Backend
=========================================
Google Gemini with native function calling.
"""

import os
from google import genai
from google.genai import types
from .base import AgentBackend


@AgentBackend.register("gemini")
class GeminiBackend(AgentBackend):

    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def default_model(self) -> str:
        return os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")

    def is_available(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))

    def chat(self, message: str) -> str:
        if not hasattr(self, "_chat"):
            api_key = os.environ.get("GEMINI_API_KEY", "")
            client = genai.Client(api_key=api_key)
            
            config = types.GenerateContentConfig(
                system_instruction=self.get_system_prompt(),
                tools=[self.execute_idapython, self.call_bridge_api],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
                temperature=0.2,
            )
            self._chat = client.chats.create(model=self.model, config=config)

        response = self._chat.send_message(message)
        return response.text
