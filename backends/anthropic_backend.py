"""
Antigravity IDA Bridge — Anthropic Backend
============================================
Claude Sonnet/Opus with native tool use.
"""

import os
import json
from .base import AgentBackend

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None
    HAS_ANTHROPIC = False


@AgentBackend.register("anthropic")
class AnthropicBackend(AgentBackend):

    @property
    def name(self) -> str:
        return "Anthropic Claude"

    @property
    def default_model(self) -> str:
        return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    def is_available(self) -> bool:
        return HAS_ANTHROPIC and bool(os.environ.get("ANTHROPIC_API_KEY"))

    def _get_tools_schema(self) -> list:
        """Anthropic tool definitions format."""
        return [
            {
                "name": "call_bridge_api",
                "description": "Call any Antigravity IDA Bridge REST endpoint.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST"]},
                        "path": {"type": "string", "description": "API path"},
                        "body": {"type": "string", "description": "JSON body for POST", "default": "{}"},
                    },
                    "required": ["method", "path"],
                },
            },
            {
                "name": "execute_idapython",
                "description": "Execute IDAPython script in IDA Pro. Full SDK access.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "script_code": {"type": "string", "description": "Python script"},
                    },
                    "required": ["script_code"],
                },
            },
        ]

    def chat(self, message: str) -> str:
        if not hasattr(self, "_client"):
            self._client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY", "")
            )
            self._messages = []
            self._system = self.get_system_prompt()

        self._messages.append({"role": "user", "content": message})

        available_functions = {
            "call_bridge_api": self.call_bridge_api,
            "execute_idapython": self.execute_idapython,
        }

        max_iterations = 10
        for _ in range(max_iterations):
            response = self._client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=self._system,
                tools=self._get_tools_schema(),
                messages=self._messages,
            )

            # Check for tool use
            if response.stop_reason == "tool_use":
                # Collect assistant response
                self._messages.append({"role": "assistant", "content": response.content})

                # Process each tool use block
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        func = available_functions.get(block.name)
                        if func:
                            result = func(**block.input)
                        else:
                            result = json.dumps({"error": f"Unknown: {block.name}"})

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                self._messages.append({"role": "user", "content": tool_results})
            else:
                # Extract text response
                text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text += block.text
                self._messages.append({"role": "assistant", "content": response.content})
                return text

        return "[Agent reached max iterations]"
