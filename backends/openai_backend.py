"""
Antigravity IDA Bridge — OpenAI Backend
=========================================
OpenAI GPT-4o, o3, o4-mini with function calling.
Also used as base for DeepSeek (compatible API).
"""

import os
import json
from openai import OpenAI
from .base import AgentBackend


@AgentBackend.register("openai")
class OpenAIBackend(AgentBackend):

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def default_model(self) -> str:
        return os.environ.get("OPENAI_MODEL", "gpt-4o")

    @property
    def api_key_env(self) -> str:
        return "OPENAI_API_KEY"

    @property
    def base_url(self) -> str:
        return None  # Uses default OpenAI URL

    def is_available(self) -> bool:
        return bool(os.environ.get(self.api_key_env))

    def _get_client(self) -> OpenAI:
        return OpenAI(
            api_key=os.environ.get(self.api_key_env, ""),
            base_url=self.base_url,
        )

    def _get_tools_schema(self) -> list:
        """OpenAI function calling tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "call_bridge_api",
                    "description": "Call any Antigravity IDA Bridge REST endpoint.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "method": {"type": "string", "enum": ["GET", "POST"]},
                            "path": {"type": "string", "description": "API path"},
                            "body": {"type": "string", "description": "JSON body for POST", "default": "{}"},
                        },
                        "required": ["method", "path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_idapython",
                    "description": "Execute IDAPython script in IDA Pro. Use result dict to return data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "script_code": {"type": "string", "description": "Python script"},
                        },
                        "required": ["script_code"],
                    },
                },
            },
        ]

    def chat(self, message: str) -> str:
        if not hasattr(self, "_messages"):
            self._client = self._get_client()
            self._messages = [
                {"role": "system", "content": self.get_system_prompt()},
            ]

        self._messages.append({"role": "user", "content": message})

        available_functions = {
            "call_bridge_api": self.call_bridge_api,
            "execute_idapython": self.execute_idapython,
        }

        max_iterations = 10
        for _ in range(max_iterations):
            response = self._client.chat.completions.create(
                model=self.model,
                messages=self._messages,
                tools=self._get_tools_schema(),
                temperature=0.2,
            )

            choice = response.choices[0]
            msg = choice.message

            if not msg.tool_calls:
                self._messages.append({"role": "assistant", "content": msg.content})
                return msg.content or ""

            # Process tool calls
            self._messages.append(msg.model_dump())

            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                func = available_functions.get(func_name)

                if func:
                    result = func(**func_args)
                else:
                    result = json.dumps({"error": f"Unknown function: {func_name}"})

                self._messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return "[Agent reached max iterations]"
