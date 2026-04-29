"""
Antigravity IDA Bridge — Ollama Backend (Local LLM)
=====================================================
Fully offline, private, free. Runs models locally via Ollama.
Supports: llama3.1, qwen2.5, mistral, deepseek-r1, codestral, etc.
"""

import os
import json
from .base import AgentBackend

try:
    import ollama as ollama_sdk
    HAS_OLLAMA = True
except ImportError:
    ollama_sdk = None
    HAS_OLLAMA = False


@AgentBackend.register("ollama")
class OllamaBackend(AgentBackend):

    @property
    def name(self) -> str:
        return "Ollama (Local)"

    @property
    def default_model(self) -> str:
        return os.environ.get("OLLAMA_MODEL", "llama3.1")

    def is_available(self) -> bool:
        """Check if Ollama is running locally."""
        if not HAS_OLLAMA:
            return False
        try:
            ollama_sdk.list()
            return True
        except Exception:
            return False

    def _get_tools_schema(self) -> list:
        """Generate OpenAI-compatible tool schemas for Ollama."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "call_bridge_api",
                    "description": "Call any Antigravity IDA Bridge REST endpoint. Use for structured API calls.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "method": {"type": "string", "description": "HTTP method: GET or POST", "enum": ["GET", "POST"]},
                            "path": {"type": "string", "description": "API path, e.g. /api/function/0x140001000/pseudocode"},
                            "body": {"type": "string", "description": "JSON body for POST requests", "default": "{}"},
                        },
                        "required": ["method", "path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_idapython",
                    "description": "Execute arbitrary IDAPython script in IDA Pro. Full SDK access. Use result dict to return data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "script_code": {"type": "string", "description": "Python script to execute in IDA"},
                        },
                        "required": ["script_code"],
                    },
                },
            },
        ]

    def chat(self, message: str) -> str:
        if not hasattr(self, "_messages"):
            self._messages = [
                {"role": "system", "content": self.get_system_prompt()},
            ]

        self._messages.append({"role": "user", "content": message})

        available_functions = {
            "call_bridge_api": self.call_bridge_api,
            "execute_idapython": self.execute_idapython,
        }

        # Agent loop — keep calling until model gives a text response
        max_iterations = 10
        for _ in range(max_iterations):
            response = ollama_sdk.chat(
                model=self.model,
                messages=self._messages,
                tools=self._get_tools_schema(),
            )

            msg = response.message

            # If no tool calls, we have our final answer
            if not msg.tool_calls:
                self._messages.append({"role": "assistant", "content": msg.content})
                return msg.content

            # Execute tool calls
            self._messages.append(msg.model_dump())

            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = tool_call.function.arguments
                func = available_functions.get(func_name)

                if func:
                    result = func(**func_args)
                else:
                    result = json.dumps({"error": f"Unknown function: {func_name}"})

                self._messages.append({
                    "role": "tool",
                    "content": result,
                })

        return "[Agent reached max iterations without final response]"
