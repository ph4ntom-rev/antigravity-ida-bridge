"""
Antigravity IDA Bridge — Anthropic Backend
============================================
Claude Sonnet/Opus with native tool use.

Changes (v5.2):
- Auto-converts OpenAI tool schema to Anthropic format (DRY)
- Uses centralized _execute_tool() for fault tolerance
- Proper reset() lifecycle
"""

import os
import json
import logging
from typing import List, Dict, Any
from .base import AgentBackend

logger = logging.getLogger("Antigravity.Bridge")

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None
    HAS_ANTHROPIC = False


@AgentBackend.register("anthropic")
class AnthropicBackend(AgentBackend):

    @classmethod
    def get_name(cls) -> str:
        return "Anthropic Claude"

    @classmethod
    def get_default_model(cls) -> str:
        return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    @classmethod
    def is_available(cls) -> bool:
        return HAS_ANTHROPIC and bool(os.environ.get("ANTHROPIC_API_KEY"))

    def reset(self) -> None:
        # Anthropic doesn't accept system prompt inside the messages list
        self.history = []
        self._system_prompt = self.get_system_prompt()
        self._client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        ) if self.is_available() else None

    @classmethod
    def get_anthropic_tools(cls) -> List[Dict[str, Any]]:
        """Transform base OpenAI schema to Anthropic Tool Use format on the fly."""
        return [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            }
            for t in cls.get_common_tools()
        ]

    def chat(self, message: str) -> str:
        if not getattr(self, "_client", None):
            return "[Error: Anthropic client not initialized]"

        self.history.append({"role": "user", "content": message})

        max_iterations = 10
        for _ in range(max_iterations):
            response = self._client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=self._system_prompt,
                tools=self.get_anthropic_tools(),
                messages=self.history,
            )

            if response.stop_reason == "tool_use":
                self.history.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Anthropic provides args as a ready dict in block.input
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                # Anthropic specifics: tool results are sent as 'user' role
                self.history.append({"role": "user", "content": tool_results})
            else:
                text = "".join(block.text for block in response.content if hasattr(block, "text"))
                self.history.append({"role": "assistant", "content": response.content})
                return text

        return "[Agent reached max iterations]"
