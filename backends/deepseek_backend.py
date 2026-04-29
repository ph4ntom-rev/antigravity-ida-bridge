"""
Antigravity IDA Bridge — DeepSeek Backend
===========================================
DeepSeek V3/R1 via OpenAI-compatible API.
Thin wrapper over OpenAI backend with different base URL.
"""

import os
from .openai_backend import OpenAIBackend
from .base import AgentBackend


@AgentBackend.register("deepseek")
class DeepSeekBackend(OpenAIBackend):

    @property
    def name(self) -> str:
        return "DeepSeek"

    @property
    def default_model(self) -> str:
        return os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    @property
    def api_key_env(self) -> str:
        return "DEEPSEEK_API_KEY"

    @property
    def base_url(self) -> str:
        return "https://api.deepseek.com"
