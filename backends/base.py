"""
Antigravity IDA Bridge — Abstract Backend
===========================================
Base class for all AI agent backends.
"""

import json
from abc import ABC, abstractmethod
from core.client import BridgeClient
from core.schema import SchemaLoader


class AgentBackend(ABC):
    """Abstract base class for AI agent backends.
    
    All backends must implement create_agent() and chat() methods.
    The base class provides common tool definitions used by all backends.
    """

    def __init__(self, client: BridgeClient = None, schema: SchemaLoader = None, model: str = None):
        self.client = client or BridgeClient()
        self.schema = schema or SchemaLoader()
        self.model = model or self.default_model
        self.history = []

    # ── Abstract Interface ───────────────────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is configured and reachable."""
        ...

    @abstractmethod
    def chat(self, message: str) -> str:
        """Send a message and get a response. Handles tool calling internally."""
        ...

    # ── Common Tool Definitions ──────────────────────────────────────────

    def execute_idapython(self, script_code: str) -> str:
        """Execute arbitrary IDAPython script in IDA Pro.
        
        The script has full access to IDA APIs (idc, idaapi, idautils, ida_funcs, etc.).
        Place results in the global 'result' dict to return structured data.
        
        Args:
            script_code: Python script to execute in IDA.
        """
        print(f"\n[+] [{self.name}] Executing IDAPython script...")
        response = self.client.exec_python(script_code)
        return json.dumps(response, indent=2)

    def call_bridge_api(self, method: str, path: str, body: str = "{}") -> str:
        """Call any Antigravity IDA Bridge REST endpoint.
        
        Use this for structured API calls to any endpoint in the schema.
        
        Args:
            method: HTTP method — 'GET' or 'POST'
            path: API path, e.g. '/api/function/0x140001000/pseudocode'
            body: JSON string body for POST requests
        """
        print(f"\n[+] [{self.name}] Bridge call: {method} {path}")
        try:
            data = json.loads(body) if body and body != "{}" else None
            result = self.client.call_api(method, path, data)
            result_str = json.dumps(result, indent=2)
            if len(result_str) > 2000:
                print(f"    Response: {len(result_str)} chars")
            else:
                print(f"    Response: {result_str[:500]}")
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

    # ── Registry ─────────────────────────────────────────────────────────

    _registry = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a backend by name."""
        def decorator(subclass):
            cls._registry[name] = subclass
            return subclass
        return decorator

    @classmethod
    def get_backend(cls, name: str) -> type:
        """Get backend class by name."""
        return cls._registry.get(name)

    @classmethod
    def list_backends(cls) -> dict:
        """List all registered backends with availability."""
        result = {}
        for name, backend_cls in cls._registry.items():
            try:
                b = backend_cls.__new__(backend_cls)
                b.client = BridgeClient()
                b.schema = SchemaLoader()
                b.model = b.default_model
                b.history = []
                result[name] = {
                    "name": b.name,
                    "model": b.default_model,
                    "available": b.is_available(),
                }
            except Exception:
                result[name] = {"name": name, "available": False}
        return result

    @classmethod
    def auto_select(cls) -> str:
        """Auto-select the best available backend."""
        # Priority: ollama (free) → gemini → openai → anthropic → deepseek
        priority = ["ollama", "gemini", "openai", "anthropic", "deepseek"]
        for name in priority:
            backend_cls = cls._registry.get(name)
            if backend_cls:
                try:
                    b = backend_cls.__new__(backend_cls)
                    b.client = BridgeClient()
                    b.schema = SchemaLoader()
                    b.model = b.default_model
                    b.history = []
                    if b.is_available():
                        return name
                except Exception:
                    continue
        return None
