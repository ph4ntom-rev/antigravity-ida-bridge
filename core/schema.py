"""
Antigravity IDA Bridge — Schema Loader
========================================
Loads and caches api_schema.json, generates system prompts for AI backends.
"""

import os
import json


class SchemaLoader:
    """Loads API schema and generates system prompts for any backend."""

    def __init__(self, schema_path: str = None):
        if schema_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            schema_path = os.path.join(base, "api_schema.json")
        
        self.schema_path = schema_path
        self._schema = None

    @property
    def schema(self) -> dict:
        """Lazy-load and cache schema."""
        if self._schema is None:
            if os.path.exists(self.schema_path):
                with open(self.schema_path, "r", encoding="utf-8") as f:
                    self._schema = json.load(f)
            else:
                self._schema = {}
        return self._schema

    @property
    def is_loaded(self) -> bool:
        return bool(self.schema)

    @property
    def endpoint_count(self) -> tuple:
        """Returns (read_count, write_count)."""
        endpoints = self.schema.get("endpoints", {})
        return len(endpoints.get("read", [])), len(endpoints.get("write", []))

    def generate_system_prompt(self, tool_instructions: str = "") -> str:
        """Generate a full system prompt from schema + custom tool instructions.
        
        Args:
            tool_instructions: Backend-specific tool usage instructions to append.
        """
        if not self.is_loaded:
            return (
                "You are an expert reverse engineering AI agent connected to IDA Pro "
                "via the Antigravity Bridge API. Use the available tools to analyze binaries."
            )

        parts = []

        # Base system prompt from schema
        base = self.schema.get("system_prompt", "")
        if base:
            parts.append(base)

        # Endpoints reference
        endpoints = self.schema.get("endpoints", {})
        if endpoints:
            parts.append("## Available API Endpoints\n")
            parts.append(json.dumps(endpoints, indent=1))

        # Workflows
        workflows = self.schema.get("workflows", [])
        if workflows:
            parts.append("\n## Workflows\n")
            parts.append(json.dumps(workflows, indent=1))

        # Tips
        tips = self.schema.get("tips", [])
        if tips:
            parts.append("\n## Tips\n")
            parts.append(json.dumps(tips, indent=1))

        # Backend-specific tool instructions
        if tool_instructions:
            parts.append(f"\n## Tool Usage\n\n{tool_instructions}")

        return "\n\n".join(parts)
