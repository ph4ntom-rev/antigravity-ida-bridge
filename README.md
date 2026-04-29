# Antigravity IDA Bridge 🌉

> **AI-native reverse engineering platform** — Your IDE agent controls IDA Pro.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://python.org)
[![IDA Pro 9.x](https://img.shields.io/badge/IDA_Pro-9.x-blueviolet?style=flat-square)](https://hex-rays.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![Endpoints](https://img.shields.io/badge/endpoints-90+-orange?style=flat-square)](#api-coverage)
[![MCP](https://img.shields.io/badge/MCP-Compatible-00ff41?style=flat-square)](#mcp-server)
[![Backends](https://img.shields.io/badge/AI_backends-5-ff6b6b?style=flat-square)](#standalone-ai-agent)

---

## How It Works

You talk to your AI agent. The agent controls IDA Pro through the bridge. That's it.

```
┌──────────────────────────────────────────────────────────────┐
│  You (in Antigravity IDE / Cursor / Claude Desktop)          │
│                                                              │
│  "open malware.exe and find all C2 communication logic"      │
│                          │                                   │
│                          ▼                                   │
│                   ┌──────────────┐                           │
│                   │   AI Agent   │  ← The IDE agent IS the   │
│                   │  (built-in)  │    brain. No separate app. │
│                   └──────┬───────┘                           │
│                          │ calls bridge.py                   │
│                          ▼                                   │
│                   ┌──────────────┐                           │
│                   │  bridge.py   │  ← Single-file CLI tool.  │
│                   │  (JSON I/O)  │    All commands, one file. │
│                   └──────┬───────┘                           │
└──────────────────────────┼───────────────────────────────────┘
                           │ HTTP / REST
                           ▼
                   ┌──────────────────┐
                   │    IDA Pro 9.x   │
                   │  + plugin (90+   │
                   │    endpoints)    │
                   └──────────────────┘
```

### The Key Idea

Your IDE already has an AI agent built in. **You don't need another AI** — you just need to give your agent **hands inside IDA Pro**. That's what `bridge.py` does.

| File | Role |
|:-----|:-----|
| `AGENT_SKILL.md` | Instructions for the AI agent — what commands exist, how to analyze |
| `bridge.py` | The tool — one file, all commands, clean JSON output |
| `ida_plugin/antigravity_server.py` | The server — runs inside IDA, exposes 90+ REST endpoints |

## Quick Start

### 1. Install the IDA Plugin

Copy `ida_plugin/antigravity_server.py` → your IDA `plugins/` folder.

Or load manually: **File → Script File → antigravity_server.py**

```
[Antigravity] ✅ Bridge server started on http://127.0.0.1:13370
[Antigravity] 🔑 Auth token: a1b2c3d4e5f6...
```

### 2. Install Dependencies

```bash
pip install requests
```

### 3. Use from Your IDE

Open `AGENT_SKILL.md` in your workspace. Your IDE agent will read it and learn how to use the bridge.

Then just talk to your agent:
> "Launch IDA with `C:\samples\malware.exe` and find all encryption routines"

The agent will call `bridge.py` commands automatically:

```bash
python bridge.py launch C:\samples\malware.exe
python bridge.py wait
python bridge.py info
python bridge.py strings --filter crypt
python bridge.py decompile 0x140005A00
python bridge.py rename 0x140005A00 aes_encrypt
```

### 4. Or Use from Terminal

```bash
python bridge.py ping                          # Check connection
python bridge.py info                          # Binary metadata
python bridge.py decompile 0x140001000         # Decompile function
python bridge.py strings --filter password     # Search strings
python bridge.py functions --limit 50          # List functions
python bridge.py xrefs 0x140001000             # Cross-references
python bridge.py callers 0x140001000           # Who calls this?
python bridge.py rename 0x140001000 main       # Rename function
python bridge.py comment 0x140001000 "entry"   # Add comment
python bridge.py exec "print(here())"          # Run IDAPython
python bridge.py launch binary.exe             # Find IDA + open binary
python bridge.py wait                          # Wait for bridge
```

## MCP Server

Universal AI client interface — works with **Claude Desktop**, **Cursor**, **Cline**, **Windsurf**.

### Claude Desktop

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ida-bridge": {
      "command": "python",
      "args": ["C:/path/to/integrations/mcp_server.py"]
    }
  }
}
```

### Cursor / Windsurf

Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "ida-bridge": {
      "command": "python",
      "args": ["C:/path/to/integrations/mcp_server.py"]
    }
  }
}
```

### 45 MCP Tools

| Category | Tools |
|:---------|:------|
| **Analysis** | `decompile`, `get_ctree`, `get_microcode`, `get_disassembly`, `get_function_details`, `get_local_variables` |
| **Navigation** | `get_callers`, `get_callees`, `get_call_graph`, `get_xrefs_to`, `get_xrefs_from`, `get_strings_used`, `get_basic_blocks` |
| **Search** | `search_function`, `search_bytes`, `search_text`, `list_strings`, `list_names` |
| **Types** | `list_structs`, `get_struct`, `list_types`, `get_type`, `create_type`, `create_struct` |
| **Mutations** | `rename_function`, `comment_function`, `rename_variable`, `set_variable_type`, `set_function_type`, `patch_bytes`, `batch_mutations` |
| **Debugger** | `dbg_start`, `dbg_set_breakpoint`, `dbg_continue`, `dbg_step_into`, `dbg_step_over`, `dbg_get_registers`, `dbg_read_memory`, `dbg_get_stack` |
| **Utility** | `execute_idapython`, `undo`, `redo`, `navigate_to`, `save_database` |

## Standalone AI Agent

Don't use an AI IDE? Run the agent directly with any of 5 backends:

```bash
python agent.py                              # Auto-detect backend
python agent.py --backend ollama             # Local LLM (free, private)
python agent.py --backend gemini             # Google Gemini
python agent.py --backend openai             # OpenAI GPT-4o
python agent.py --backend anthropic          # Anthropic Claude
python agent.py --backend deepseek           # DeepSeek
python agent.py --list-backends              # Show available
```

| Backend | Type | Models | Env Variable |
|:--------|:-----|:-------|:-------------|
| **Ollama** | 🏠 Local | llama3.1, qwen2.5, mistral | — (auto-detect) |
| **Gemini** | ☁️ Cloud | gemini-3.1-pro, gemini-3-flash | `GEMINI_API_KEY` |
| **OpenAI** | ☁️ Cloud | gpt-4o, o3, o4-mini | `OPENAI_API_KEY` |
| **Anthropic** | ☁️ Cloud | claude-sonnet-4, claude-opus | `ANTHROPIC_API_KEY` |
| **DeepSeek** | ☁️ Cloud | deepseek-chat, deepseek-reasoner | `DEEPSEEK_API_KEY` |

## Project Structure

```
antigravity-ida-bridge/
├── ida_plugin/
│   └── antigravity_server.py       # IDA Pro HTTP plugin (90+ endpoints)
├── core/
│   ├── client.py                   # Reusable HTTP client
│   └── schema.py                   # API schema loader
├── backends/
│   ├── base.py                     # Abstract backend + registry
│   ├── ollama_backend.py           # Local LLM
│   ├── gemini_backend.py           # Google Gemini
│   ├── openai_backend.py           # OpenAI
│   ├── anthropic_backend.py        # Anthropic Claude
│   └── deepseek_backend.py         # DeepSeek
├── integrations/
│   ├── mcp_server.py               # MCP server for AI clients
│   └── ide_extension.py            # IDE workspace config generator
├── bridge.py                       # ⭐ Single-file CLI for IDE agents
├── AGENT_SKILL.md                  # ⭐ Instructions for IDE agents
├── agent.py                        # Standalone multi-backend agent
├── bridge_cli.py                   # Full-featured terminal CLI
├── swarm_worker.py                 # Bulk AI analyzer
└── api_schema.json                 # Machine-readable API spec
```

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
| **Utility** | `batch`, `exec`, `save`, `undo`, `redo`, `navigate`, `reanalyze` |

</details>

## Security

- **Bearer Token Auth** — Auto-generated per session, stored in temp file
- **Localhost Only** — Binds to `127.0.0.1`, not exposed to network
- **Path Hardening** — Directory traversal and UNC path protection
- **CORS Headers** — Configurable cross-origin policy

## Requirements

- IDA Pro 9.x with Hex-Rays Decompiler
- Python 3.10+
- `requests` (core — only hard dependency)
- Backend-specific packages (see [Standalone AI Agent](#standalone-ai-agent))

## License

MIT
