"""
Antigravity IDA Bridge — Abstract Backend
===========================================
Base class for all AI agent backends.

Changes (v5.2):
- Metadata via @classmethod (eliminates __new__ hacks and memory leaks)
- Centralized fault-tolerant tool dispatcher (_execute_tool)
- DRY tool schema (defined once, converted per-backend)
- Session management with reset()
- Replaced print() with logging
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Union

from core.client import BridgeClient
from core.schema import SchemaLoader

logger = logging.getLogger("Antigravity.Bridge")


class AgentBackend(ABC):
    """Abstract base class for all AI agent backends.

    All backends must implement get_name(), get_default_model(),
    is_available(), and chat() methods.
    """

    _registry: Dict[str, Type['AgentBackend']] = {}

    def __init__(self, client: Optional[BridgeClient] = None, schema: Optional[SchemaLoader] = None, model: Optional[str] = None):
        self.client = client or BridgeClient()
        self.schema = schema or SchemaLoader()
        self.model = model or self.get_default_model()
        self.history: List[Dict[str, Any]] = []
        self.reset()

    # ── Metadata (Class Methods — no __new__ hacks) ──────────────────────

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Human-readable backend name."""
        ...

    @classmethod
    @abstractmethod
    def get_default_model(cls) -> str:
        """Default model identifier."""
        ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this backend is configured and reachable."""
        ...

    # ── Registry ─────────────────────────────────────────────────────────

    @classmethod
    def register(cls, name: str):
        """Decorator to register a backend by name."""
        def decorator(subclass: Type['AgentBackend']):
            cls._registry[name] = subclass
            return subclass
        return decorator

    @classmethod
    def get_backend(cls, name: str) -> Optional[Type['AgentBackend']]:
        """Get backend class by name."""
        return cls._registry.get(name)

    @classmethod
    def list_backends(cls) -> dict:
        """List all registered backends with availability (O(1), no object allocation)."""
        return {
            name: {
                "name": b_cls.get_name(),
                "model": b_cls.get_default_model(),
                "available": b_cls.is_available(),
            }
            for name, b_cls in cls._registry.items()
        }

    @classmethod
    def auto_select(cls) -> Optional[str]:
        """Auto-select the best available backend."""
        priority = ["ollama", "gemini", "openai", "anthropic", "deepseek"]
        for name in priority:
            if (b_cls := cls._registry.get(name)) and b_cls.is_available():
                return name
        return None

    # ── Lifecycle ────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset conversation history to free context window."""
        self.history = [{"role": "system", "content": self.get_system_prompt()}]

    @abstractmethod
    def chat(self, message: str) -> str:
        """Send a message and get a response. Handles tool calling internally."""
        ...

    # ── DRY Tool Schema (Single Source of Truth) ─────────────────────────

    @classmethod
    def get_common_tools(cls) -> List[Dict[str, Any]]:
        """Tool definitions in OpenAI format. Other SDKs convert on the fly."""
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
                    "description": "Execute arbitrary IDAPython script in IDA Pro. Full SDK access. Use result dict to return data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "script_code": {"type": "string", "description": "Python script code"},
                        },
                        "required": ["script_code"],
                    },
                },
            },
        ]

    # ── Fault-Tolerant Tool Dispatcher ───────────────────────────────────

    def _execute_tool(self, func_name: str, func_args: Union[str, Dict[str, Any]]) -> str:
        """
        Executes tool calls with full error recovery.
        Catches LLM hallucinated JSON and runtime crashes,
        returning errors back to the model for self-correction.
        """
        available_functions = {
            "call_bridge_api": self.call_bridge_api,
            "execute_idapython": self.execute_idapython,
        }

        func = available_functions.get(func_name)
        if not func:
            return json.dumps({"error": f"Unknown function requested: {func_name}"})

        # OpenAI/Ollama may pass string args, Anthropic/Gemini pass dicts
        if isinstance(func_args, str):
            try:
                func_args = json.loads(func_args) if func_args.strip() else {}
            except json.JSONDecodeError as e:
                logger.warning(f"LLM hallucinated invalid JSON args for {func_name}")
                return json.dumps({"error": f"Invalid JSON syntax in arguments: {str(e)}. Please fix and retry."})

        if not isinstance(func_args, dict):
            func_args = {}

        try:
            result = func(**func_args)
            return result if isinstance(result, str) else json.dumps(result)
        except TypeError as e:
            return json.dumps({"error": f"Invalid arguments for {func_name}: {str(e)}"})
        except Exception as e:
            logger.exception(f"Tool runtime exception in {func_name}")
            return json.dumps({"error": f"Execution failed: {str(e)}"})

    # ── Tool Implementations ─────────────────────────────────────────────

    def execute_idapython(self, script_code: str) -> str:
        """Execute arbitrary IDAPython script in IDA Pro."""
        logger.info(f"[{self.get_name()}] Executing IDAPython script...")
        try:
            response = self.client.exec_python(script_code)
            return json.dumps(response, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Execution failed: {e}", "success": False})

    def call_bridge_api(self, method: str, path: str, body: Union[str, dict] = "{}") -> str:
        """Call any Antigravity IDA Bridge REST endpoint."""
        logger.info(f"[{self.get_name()}] Bridge call: {method} {path}")

        if isinstance(body, str):
            try:
                data = json.loads(body) if body.strip() and body != "{}" else None
            except json.JSONDecodeError as e:
                return json.dumps({"error": f"Malformed body JSON: {str(e)}", "success": False})
        else:
            data = body

        try:
            result = self.client.call_api(method, path, data)
            result_str = json.dumps(result, indent=2)
            logger.debug(f"Response: {result_str[:500]}..." if len(result_str) > 500 else f"Response: {result_str}")
            return result_str
        except Exception as e:
            return json.dumps({"error": str(e), "success": False})

    def get_tool_instructions(self) -> str:
        """Standard tool usage instructions for system prompt."""
        return (
            "You have two tools:\n"
            "1. `call_bridge_api(method, path, body)` — For structured REST calls to any endpoint.\n"
            "2. `execute_idapython(script_code)` — For arbitrary IDAPython when no endpoint covers your need.\n"
            "Prefer `call_bridge_api` when a dedicated endpoint exists. "
            "Use `execute_idapython` for complex custom logic.\n"
        )

    def get_system_prompt(self) -> str:
        """Generate complete system prompt with tool instructions."""
        return self.schema.generate_system_prompt(self.get_tool_instructions())
