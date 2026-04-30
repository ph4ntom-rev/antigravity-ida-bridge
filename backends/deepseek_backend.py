"""
Antigravity IDA Bridge — DeepSeek Backend
===========================================
DeepSeek V3/R1 via OpenAI-compatible API.
Thin wrapper over OpenAI backend with different base URL.

Changes (v5.2):
- Clean polymorphism via OpenAI base class (DRY)
"""

import os
from .openai_backend import OpenAIBackend
from .base import AgentBackend


@AgentBackend.register("deepseek")
class DeepSeekBackend(OpenAIBackend):

    @classmethod
    def get_name(cls) -> str:
        return "DeepSeek"

    @classmethod
    def get_default_model(cls) -> str:
        return os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    @classmethod
    def get_api_key_env(cls) -> str:
        return "DEEPSEEK_API_KEY"

    def get_base_url(self) -> str:
        return "https://api.deepseek.com"
