"""
Antigravity IDA Bridge — OpenAI Backend
=========================================
OpenAI GPT-4o, o3, o4-mini with function calling.
Also used as base for DeepSeek (compatible API).

Changes (v5.2):
- Uses centralized tool schema from base class
- exclude_none=True on model_dump() to prevent 400 Bad Request
- Fault-tolerant tool execution via _execute_tool()
- Proper reset() lifecycle
"""

import os
import json
from typing import Optional
from .base import AgentBackend

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    OpenAI = None
    HAS_OPENAI = False


@AgentBackend.register("openai")
class OpenAIBackend(AgentBackend):

    @classmethod
    def get_name(cls) -> str:
        return "OpenAI"

    @classmethod
    def get_default_model(cls) -> str:
        return os.environ.get("OPENAI_MODEL", "gpt-4o")

    @classmethod
    def get_api_key_env(cls) -> str:
        return "OPENAI_API_KEY"

    @classmethod
    def is_available(cls) -> bool:
        return HAS_OPENAI and bool(os.environ.get(cls.get_api_key_env()))

    def get_base_url(self) -> Optional[str]:
        return None  # Uses default OpenAI URL

    def reset(self) -> None:
        super().reset()
        self._client = OpenAI(
            api_key=os.environ.get(self.get_api_key_env(), ""),
            base_url=self.get_base_url(),
        ) if self.is_available() else None

    def chat(self, message: str) -> str:
        if not getattr(self, "_client", None):
            return "[Error: OpenAI client not initialized]"

        self.history.append({"role": "user", "content": message})

        max_iterations = 10
        for _ in range(max_iterations):
            response = self._client.chat.completions.create(
                model=self.model,
                messages=self.history,
                tools=self.get_common_tools(),
                temperature=0.2,
            )

            msg = response.choices[0].message

            if not msg.tool_calls:
                self.history.append({"role": "assistant", "content": msg.content or ""})
                return msg.content or ""

            # exclude_none=True prevents sending function_call=None (fixes 400 Bad Request)
            self.history.append(msg.model_dump(exclude_none=True))

            for tool_call in msg.tool_calls:
                result = self._execute_tool(tool_call.function.name, tool_call.function.arguments)
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return "[Agent reached max iterations]"
