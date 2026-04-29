# Antigravity IDA Bridge 🌉

> **The autonomous reverse engineering platform** — Give it a binary, get back the logic.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://python.org)
[![IDA Pro 9.x](https://img.shields.io/badge/IDA_Pro-9.x-blueviolet?style=flat-square)](https://hex-rays.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![Endpoints](https://img.shields.io/badge/endpoints-90+-orange?style=flat-square)](#api-coverage)
[![MCP](https://img.shields.io/badge/MCP-Compatible-00ff41?style=flat-square)](#mcp-server)
[![Backends](https://img.shields.io/badge/backends-5-ff6b6b?style=flat-square)](#ai-backends)

---

## One Command. Full Analysis.

```bash
python autopilot.py malware.exe "recover all C2 communication logic"
```

That's it. Autopilot will:
1. 🔍 **Find** IDA Pro on your system (registry, PATH, common dirs)
2. 📦 **Install** the bridge plugin if needed
3. 🚀 **Launch** IDA with your binary
4. ⏳ **Wait** for analysis to complete
5. 🤖 **Run** your AI agent against the binary
6. 📄 **Save** a comprehensive report

```
┌─────────────────────────────────────────────────────────────────┐
│                        AUTOPILOT                                │
│  python autopilot.py binary.exe "find vulnerabilities"          │
│                          │                                      │
│              ┌───────────┴───────────┐                          │
│              ▼                       ▼                          │
│     ┌─────────────┐        ┌─────────────────┐                 │
│     │ Find IDA Pro │        │ Select Backend  │                 │
│     │ (auto-scan)  │        │ (auto-detect)   │                 │
│     └──────┬──────┘        └────────┬────────┘                 │
│            ▼                        │                           │
│     ┌─────────────┐                │                           │
│     │ Launch IDA   │                │                           │
│     │ + Plugin     │                │                           │
│     └──────┬──────┘                │                           │
│            ▼                        │                           │
│     ┌─────────────┐                │                           │
│     │ Wait for     │                │                           │
│     │ Bridge       │◄───────────────┘                           │
│     └──────┬──────┘                                            │
│            ▼                                                    │
│     ┌─────────────┐                                            │
│     │ AI Analysis  │──── report.md                              │
│     └─────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture

```
antigravity-ida-bridge/
├── ida_plugin/
│   └── antigravity_server.py       # IDA Pro HTTP plugin (90+ endpoints)
├── core/
│   ├── client.py                   # Reusable HTTP client
│   └── schema.py                   # API schema loader & prompt generator
├── backends/
│   ├── base.py                     # Abstract backend + registry
│   ├── ollama_backend.py           # 🏠 Local LLM (free, private)
│   ├── gemini_backend.py           # ☁️  Google Gemini
│   ├── openai_backend.py           # ☁️  OpenAI GPT-4o / o3
│   ├── anthropic_backend.py        # ☁️  Anthropic Claude
│   └── deepseek_backend.py         # ☁️  DeepSeek V3/R1
├── integrations/
│   ├── mcp_server.py               # MCP — Claude Desktop, Cursor, Cline
│   └── ide_extension.py            # Antigravity IDE / VS Code bridge
├── autopilot.py                    # 🚀 One-command autonomous analysis
├── agent.py                        # Interactive multi-backend agent
├── bridge_cli.py                   # Terminal CLI client
├── swarm_worker.py                 # Bulk AI analyzer
└── api_schema.json                 # Machine-readable API spec
```

## AI Backends

| Backend | Type | Models | Env Variable | Function Calling |
|:--------|:-----|:-------|:-------------|:-----------------|
| **Ollama** | 🏠 Local | llama3.1, qwen2.5, mistral, codestral | — (auto-detect) | ✅ Native |
| **Gemini** | ☁️ Cloud | gemini-3.1-pro, gemini-3-flash | `GEMINI_API_KEY` | ✅ Native |
| **OpenAI** | ☁️ Cloud | gpt-4o, o3, o4-mini | `OPENAI_API_KEY` | ✅ Native |
| **Anthropic** | ☁️ Cloud | claude-sonnet-4, claude-opus | `ANTHROPIC_API_KEY` | ✅ Native |
| **DeepSeek** | ☁️ Cloud | deepseek-chat, deepseek-reasoner | `DEEPSEEK_API_KEY` | ✅ Native |

### Auto-Detection

```bash
python agent.py                    # Auto-selects best available backend
python agent.py --list-backends    # Show what's available
python agent.py --backend ollama --model qwen2.5:72b
```

Priority: Ollama (free) → Gemini → OpenAI → Anthropic → DeepSeek

## Quick Start

### 1. Install Plugin

```bash
# Copy to IDA plugins folder (or let autopilot do it automatically)
cp ida_plugin/antigravity_server.py "C:\Program Files\IDA Pro 9.0\plugins\"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

# Or install only what you need:
pip install requests                    # Core (required)
pip install ollama                      # Local LLM
pip install google-genai                # Gemini
pip install openai                      # OpenAI / DeepSeek
pip install anthropic                   # Claude
pip install fastmcp                     # MCP Server
```

### 3. Autonomous Analysis (Autopilot)

```bash
# Full autopilot — finds IDA, launches, analyzes
python autopilot.py malware.exe "find all C2 communication and encryption routines"

# With specific backend
python autopilot.py firmware.bin "map bootloader entry" --backend ollama

# Save report
python autopilot.py sample.dll "document all exports" -o report.md

# IDA already running
python autopilot.py --skip-launch "explain the main function"

# Just find IDA installation
python autopilot.py --find-ida
```

### 4. Interactive Agent

```bash
python agent.py --backend gemini

[User]> Find all functions that reference "CreateRemoteThread"
[Agent is thinking...]
[+] [Gemini] Bridge call: GET /api/strings?filter=CreateRemoteThread
[Agent]> I found 3 functions referencing CreateRemoteThread...

[User]> switch ollama
[+] Switched to Ollama (Local) (llama3.1)
```

### 5. Terminal CLI

```bash
python bridge_cli.py ping
python bridge_cli.py info
python bridge_cli.py pseudocode 0x140001000
python bridge_cli.py strings --filter "password"
```

### 6. Bulk AI Analysis (Swarm)

```bash
set GEMINI_API_KEY=your_key
python swarm_worker.py --limit 200 --workers 5
```

## MCP Server

Universal AI client interface — works with **Claude Desktop**, **Cursor**, **Cline**, **Windsurf**, and any MCP-compatible client.

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

## IDE Integration

### Antigravity IDE / VS Code

```bash
# Generate workspace config files
python integrations/ide_extension.py init .

# Creates:
#   .antigravity/config.json    — Bridge settings
#   .vscode/settings.json       — VS Code/Antigravity settings
#   .cursor/mcp.json            — Cursor MCP config
```

### Programmatic Use

```python
from autopilot import run

# One function call — full autonomous analysis
result = run("C:/samples/malware.exe", "find all C2 communication logic")

# With options
result = run(
    "firmware.bin",
    "map the bootloader",
    backend="ollama",
    model="qwen2.5:72b",
    output="report.md"
)
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
- `requests` (core)
- Backend-specific packages (see [AI Backends](#ai-backends))

## License

MIT
