"""
Antigravity IDA Bridge — Ollama Backend (Local LLM)
=====================================================
Fully offline, private, free. Runs models locally via Ollama.
Supports: llama3.1, qwen2.5, mistral, deepseek-r1, codestral, etc.

Changes (v5.2):
- Uses centralized tool schema from base class
- Fault-tolerant tool execution via _execute_tool()
- Handles both dict and Pydantic responses from Ollama SDK
- exclude_none on model_dump()
"""

import os
import json
import logging
from .base import AgentBackend

logger = logging.getLogger("Antigravity.Bridge")

try:
    import ollama as ollama_sdk
    HAS_OLLAMA = True
except ImportError:
    ollama_sdk = None
    HAS_OLLAMA = False


@AgentBackend.register("ollama")
class OllamaBackend(AgentBackend):

    @classmethod
    def get_name(cls) -> str:
        return "Ollama (Local)"

    @classmethod
    def get_default_model(cls) -> str:
        return os.environ.get("OLLAMA_MODEL", "llama3.1")

    @classmethod
    def is_available(cls) -> bool:
        """Check if Ollama is running locally."""
        if not HAS_OLLAMA:
            return False
        try:
            ollama_sdk.list()
            return True
        except Exception:
            return False

    def chat(self, message: str) -> str:
        self.history.append({"role": "user", "content": message})

        max_iterations = 10
        for _ in range(max_iterations):
            response = ollama_sdk.chat(
                model=self.model,
                messages=self.history,
                tools=self.get_common_tools(),
            )

            # Handle both dict and Pydantic responses for Ollama SDK version compat
            msg = response.get("message") if isinstance(response, dict) else response.message
            tool_calls = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)

            if not tool_calls:
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
                self.history.append({"role": "assistant", "content": content})
                return content

            # Append assistant message
            try:
                self.history.append(msg.model_dump(exclude_none=True))
            except AttributeError:
                self.history.append(dict(msg))

            # Execute each tool call
            for tool_call in tool_calls:
                tc = tool_call if isinstance(tool_call, dict) else dict(tool_call)
                func = tc.get("function", {})

                func_name = func.get("name", "") if isinstance(func, dict) else getattr(func, "name", "")
                func_args = func.get("arguments", {}) if isinstance(func, dict) else getattr(func, "arguments", {})

                result = self._execute_tool(func_name, func_args)
                self.history.append({"role": "tool", "content": result})

        return "[Agent reached max iterations without final response]"
