"""
Antigravity IDA Bridge — MCP Server (Refactored)
===================================================
FastMCP 3.x server using Core SDK. No duplicated HTTP logic.

Fixes (v5.2):
- Uses shared BridgeClient instead of raw requests
- Removed all duplicated session/token/error handling code
"""

import json
from fastmcp import FastMCP
from core.client import BridgeClient

client = BridgeClient()

mcp = FastMCP(
    "Antigravity IDA Bridge",
    description="AI-powered IDA Pro reverse engineering interface via MCP."
)


@mcp.resource("ida://info")
def binary_info() -> str:
    return json.dumps(client.info(), indent=2)


@mcp.tool
def ping() -> str:
    """Check if IDA Bridge is running."""
    return json.dumps(client.ping())


@mcp.tool
def get_binary_info() -> str:
    """Get binary metadata: filename, processor, bitness."""
    return json.dumps(client.info(), indent=2)


@mcp.tool
def list_functions() -> str:
    """List all functions in the binary."""
    return json.dumps(client.functions(), indent=2)


@mcp.tool
def decompile(ea: str) -> str:
    """Decompile function at address to C pseudocode."""
    return json.dumps(client.pseudocode(ea), indent=2)


@mcp.tool
def rename_function(ea: str, name: str) -> str:
    """Rename function at address."""
    return json.dumps(client.rename_func(ea, name), indent=2)


@mcp.tool
def batch_mutations(mutations: str) -> str:
    """Execute multiple mutations atomically. Pass JSON array string."""
    try:
        ops = json.loads(mutations)
        return json.dumps(client.batch(ops), indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})


@mcp.tool
def execute_idapython(script: str) -> str:
    """Execute arbitrary IDAPython script in IDA Pro."""
    return json.dumps(client.exec_python(script), indent=2)


@mcp.tool
def call_bridge(method: str, path: str, body: str = "{}") -> str:
    """Call any IDA Bridge REST endpoint. method: GET or POST."""
    try:
        data = json.loads(body) if body.strip() and body != "{}" else None
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid body JSON: {e}"})
    return json.dumps(client.call_api(method, path, data), indent=2)


if __name__ == "__main__":
    mcp.run()
