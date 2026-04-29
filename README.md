# Antigravity IDA Bridge 🌉

> **AI-native reverse engineering platform** — Any AI agent controls IDA Pro.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://python.org)
[![IDA Pro 9.x](https://img.shields.io/badge/IDA_Pro-9.x-blueviolet?style=flat-square)](https://hex-rays.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![Endpoints](https://img.shields.io/badge/endpoints-90+-orange?style=flat-square)](#api-coverage)
[![MCP](https://img.shields.io/badge/MCP-Compatible-00ff41?style=flat-square)](#2-mcp-server)
[![Backends](https://img.shields.io/badge/AI_backends-5-ff6b6b?style=flat-square)](#3-standalone-agent)

---

## What Is This?

A plugin for **IDA Pro** that turns it into an API server with **90+ REST endpoints**. Any AI agent — IDE-based, cloud, local, or MCP — can control IDA Pro, decompile code, trace cross-references, rename functions, and even **generate and execute IDAPython scripts on the fly**.

```
              ┌─────────────────────────────────────────┐
              │             IDA Pro 9.x                  │
              │  antigravity_server.py (90+ endpoints)   │
              │  http://127.0.0.1:13370                  │
              └──────────────────┬──────────────────────┘
                                 │ REST / JSON
         ┌───────────┬───────────┼───────────┬───────────┐
         ▼           ▼           ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │Antigravity│ │   MCP    │ │Standalone│ │ Direct │ │ Swarm  │
   │   IDE    │ │ Server   │ │ Agent  │ │  API   │ │ Worker │
   │          │ │          │ │        │ │        │ │        │
   │ bridge.py│ │ 45 tools │ │ 5 LLMs │ │ curl / │ │ Bulk   │
   │ + skill  │ │ Claude   │ │ Ollama │ │ Python │ │ scan   │
   │          │ │ Cursor   │ │ Gemini │ │        │ │        │
   └──────────┘ └──────────┘ └────────┘ └────────┘ └────────┘
```

## 4 Ways to Connect

### 1. AI IDE Agent (Antigravity IDE / Cursor / Windsurf)

Your IDE already has an AI agent. Give it **hands inside IDA** — it reads `agent_config.json`, calls `bridge.py`, gets JSON back.

```
You: "find all network functions in this binary"
IDE Agent reads: agent_config.json (knows all commands + script execution)
IDE Agent runs:  python bridge.py strings --filter socket    → JSON
IDE Agent runs:  python bridge.py decompile 0x140005A00      → JSON
IDE Agent runs:  python bridge.py exec "print(idautils...)"  → JSON
IDE Agent:       "Found 3 network functions, here's what they do..."
```

**Setup:** Place `AGENT_SKILL.md` and `agent_config.json` in your workspace. The agent reads them automatically.

### 2. MCP Server (Claude Desktop / Cursor / Cline)

45 native MCP tools. Zero configuration beyond pointing to the server.

```json
{
  "mcpServers": {
    "ida-bridge": {
      "command": "python",
      "args": ["path/to/integrations/mcp_server.py"]
    }
  }
}
```

### 3. Standalone Agent (no IDE needed)

Built-in AI agent with 5 interchangeable backends:

```bash
python agent.py                          # Auto-detect best backend
python agent.py --backend ollama         # 🏠 Local (free, private)
python agent.py --backend gemini         # ☁️ Google Gemini
python agent.py --backend openai         # ☁️ OpenAI GPT-4o
python agent.py --backend anthropic      # ☁️ Anthropic Claude
python agent.py --backend deepseek       # ☁️ DeepSeek
```

### 4. Direct REST API (any HTTP client)

```bash
curl http://127.0.0.1:13370/api/info
curl http://127.0.0.1:13370/api/function/0x140001000/pseudocode
curl -X POST http://127.0.0.1:13370/api/exec -d '{"script":"print(here())"}'
```

## Dynamic Script Execution

The most powerful feature: **the AI agent can generate Python scripts and execute them inside IDA Pro in real-time**.

This isn't limited to the 90 pre-built endpoints. The agent can write *any* IDAPython code:

```python
# Agent generates this script on the fly and sends it to /api/exec:
import idautils, idc

result['suspicious'] = []
for ea in idautils.Functions():
    name = idc.get_func_name(ea)
    for ref in idautils.CodeRefsFrom(ea, 0):
        api = idc.get_func_name(ref)
        if api in ['CreateRemoteThread', 'VirtualAllocEx', 'WriteProcessMemory']:
            result['suspicious'].append({
                'function': name,
                'address': hex(ea),
                'calls': api
            })
```

Available IDA SDK modules: `idc`, `idaapi`, `idautils`, `ida_hexrays`, `ida_funcs`, `ida_bytes`, `ida_struct`, `ida_dbg`, `ida_typeinf`, `ida_segment`, `ida_xref`, `ida_auto`, and 10+ more.

The agent sees the full list in `agent_config.json` with examples.

## Quick Start

### 1. Install Plugin

Copy `ida_plugin/antigravity_server.py` → IDA `plugins/` folder.

### 2. Install Dependencies

```bash
pip install requests                    # Core (required)
pip install ollama                      # Local LLM backend
pip install google-genai                # Gemini backend
pip install openai                      # OpenAI / DeepSeek backend
pip install anthropic                   # Claude backend
pip install fastmcp                     # MCP Server
```

### 3. Use

```bash
# Terminal CLI
python bridge.py ping
python bridge.py info
python bridge.py decompile 0x140001000
python bridge.py strings --filter password
python bridge.py launch binary.exe
python bridge.py exec "print(idc.get_func_name(here()))"

# Interactive agent
python agent.py --backend ollama
```

## Key Files

| File | For Whom | Purpose |
|:-----|:---------|:--------|
| `agent_config.json` | **Any AI agent** | Machine-readable config — all commands, all modes, script examples |
| `AGENT_SKILL.md` | **IDE agents** | Human-readable instructions for IDE AI agents |
| `bridge.py` | **IDE agents** | Single-file CLI — all commands, clean JSON output |
| `ida_plugin/antigravity_server.py` | **IDA Pro** | HTTP server plugin (90+ endpoints) |
| `integrations/mcp_server.py` | **MCP clients** | 45 MCP tools for Claude/Cursor/Cline |
| `agent.py` | **Terminal users** | Standalone agent with 5 AI backends |
| `api_schema.json` | **Agents** | Full API specification (system prompt) |

## API Coverage

<details>
<summary><b>📖 Full Endpoint List (90+)</b></summary>

### Read Endpoints (GET)

| Category | Endpoints |
|:---------|:----------|
| **Binary Info** | `/api/info`, `/api/ping`, `/api/schema` |
| **Functions** | `/api/functions`, `/api/functions-page`, `/api/function/<ea>/details` |
| **Decompilation** | `/api/function/<ea>/pseudocode`, `/api/function/<ea>/ctree`, `/api/function/<ea>/microcode` |
| **Variables** | `/api/function/<ea>/lvar-map`, `/api/function/<ea>/args`, `/api/function/<ea>/stack-vars` |
| **Cross-References** | `/api/function/<ea>/xrefs-to`, `/api/function/<ea>/xrefs-from`, `/api/data-xrefs/<ea>`, `/api/code-xrefs/<ea>` |
| **Navigation** | `/api/function/<ea>/callers`, `/api/function/<ea>/callees`, `/api/function/<ea>/call-graph`, `/api/function/<ea>/strings-used` |
| **Control Flow** | `/api/function/<ea>/basic-blocks` |
| **Strings & Search** | `/api/strings`, `/api/search-func/<name>`, `/api/search-bytes/<pattern>`, `/api/search-text/<text>` |
| **Imports/Exports** | `/api/imports`, `/api/exports` |
| **Types & Structs** | `/api/structs`, `/api/struct/<name>`, `/api/enums`, `/api/enum/<name>`, `/api/types`, `/api/type/<name>`, `/api/type-libraries` |
| **Memory** | `/api/bytes/<ea>/<size>`, `/api/vtable/<ea>`, `/api/segments`, `/api/global-vars` |
| **Debugger** | `/api/dbg/regs`, `/api/dbg/breakpoints`, `/api/dbg/threads`, `/api/dbg/stack`, `/api/dbg/memory/<ea>/<size>` |
| **UI** | `/api/cursor`, `/api/selection`, `/api/bookmarks`, `/api/patches`, `/api/gaps` |

### Write Endpoints (POST)

| Category | Endpoints |
|:---------|:----------|
| **Naming** | `rename`, `lvar-rename`, `set-name`, `comment`, `lvar-comment` |
| **Types** | `set-type`, `lvar-set-type`, `type/create`, `type/delete`, `type-library/load` |
| **Structures** | `struct/create`, `struct/add-member`, `delete-struct`, `apply-struct` |
| **Enums** | `enum/create`, `enum/add-member`, `delete-enum` |
| **Segments** | `segment/create`, `segment/delete`, `segment/set-attrs` |
| **Binary Mod** | `patch-bytes`, `make-code`, `make-data`, `make-func`, `delete-func`, `undefine` |
| **Debugger** | `dbg/start`, `dbg/attach`, `dbg/detach`, `dbg/breakpoint`, `dbg/step-into`, `dbg/step-over`, `dbg/continue`, `dbg/pause`, `dbg/write-memory` |
| **Script** | `exec` — **execute any IDAPython script generated by the AI** |
| **Utility** | `batch`, `save`, `undo`, `redo`, `navigate`, `reanalyze` |

</details>

## Security

- **Bearer Token Auth** — Auto-generated per session, stored in temp file
- **Localhost Only** — Binds to `127.0.0.1`, not exposed to network
- **Path Hardening** — Directory traversal and UNC path protection
- **Atomic Rollback** — `undo` endpoint reverts AI mistakes

## License

MIT
