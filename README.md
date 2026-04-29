# Antigravity IDA Bridge 🌉

> **AI-powered IDA Pro REST API** — Turn IDA Pro into a programmable, AI-driven reverse engineering engine.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://python.org)
[![IDA Pro 9.x](https://img.shields.io/badge/IDA_Pro-9.x-blueviolet?style=flat-square)](https://hex-rays.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![Endpoints](https://img.shields.io/badge/endpoints-90+-orange?style=flat-square)](#api-coverage)

---

## What is this?

A lightweight HTTP server plugin for **IDA Pro 9.x** that exposes **90+ REST endpoints** covering the entire IDA SDK — decompilation, cross-references, type system, debugger, microcode IR, and more. Paired with an AI agent powered by Google Gemini, it enables **fully autonomous reverse engineering**.

```
┌─────────────────────────────────────────────────┐
│                 IDA Pro 9.x                     │
│  ┌───────────────────────────────────────────┐  │
│  │  antigravity_server.py (HTTP Plugin)      │  │
│  │  ThreadingHTTPServer on 127.0.0.1:13370   │  │
│  │  Bearer token authentication              │  │
│  │  90+ REST endpoints (GET/POST)            │  │
│  └──────────────────┬────────────────────────┘  │
└─────────────────────┼───────────────────────────┘
                      │ JSON/HTTP
        ┌─────────────┼──────────────┐
        ▼             ▼              ▼
   bridge_cli    orchestrator    swarm_worker
   (Terminal)    (AI Agent)      (Bulk AI)
                      │              │
                      ▼              ▼
                 Gemini 3.1 Pro API
```

## Features

- **90+ REST Endpoints** — Decompilation, ctree AST, microcode IR, xrefs, types, structs, enums, debugger, patching
- **Turing-Complete `/api/exec`** — Execute arbitrary IDAPython scripts over HTTP
- **Thread-Safe** — All IDA SDK calls dispatched via `execute_sync()`, server uses `ThreadingHTTPServer`
- **Authenticated** — Auto-generated Bearer token prevents CSRF/localhost attacks
- **AI Swarm Worker** — Multi-threaded bulk function analysis with Gemini Pro
- **Autonomous Agent** — ReAct-loop orchestrator with function calling and full API schema
- **Self-Documenting** — `/api/schema` endpoint serves the complete API specification
- **Batch Mutations** — Atomic operations with rollback support

## Quick Start

### 1. Install the IDA Plugin

Copy `ida_plugin/antigravity_server.py` → your IDA `plugins/` folder.

Or load manually: **File → Script File → antigravity_server.py**

You'll see in IDA's output:
```
[Antigravity] ✅ Bridge server started on http://127.0.0.1:13370
[Antigravity] 🔑 Auth token: a1b2c3d4e5f6...
[Antigravity] 🔑 Token file: C:\Users\...\Temp\.antigravity_token
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Use from Terminal

```bash
python bridge_cli.py ping
python bridge_cli.py info
python bridge_cli.py pseudocode 0x140001000
python bridge_cli.py strings --filter "password"
python bridge_cli.py exec my_script.py
```

### 4. Launch AI Agent

```bash
set GEMINI_API_KEY=your_key_here
python agent_orchestrator.py
```

```
[User]> Find all functions that reference "CreateRemoteThread" and explain what they do
[Agent is thinking...]
[+] Agent calling bridge: GET /api/strings?filter=CreateRemoteThread
[+] Agent calling bridge: GET /api/function/0x140005A00/pseudocode
[Agent]> I found 3 functions referencing CreateRemoteThread...
```

### 5. Bulk AI Analysis (Swarm)

```bash
set GEMINI_API_KEY=your_key_here
python swarm_worker.py --limit 200 --workers 5
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

## Architecture

| File | Purpose |
|:-----|:--------|
| `ida_plugin/antigravity_server.py` | IDA Pro HTTP plugin (2000+ lines, all-in-one) |
| `bridge_cli.py` | Python client library + CLI |
| `agent_orchestrator.py` | Autonomous AI agent with Gemini function calling |
| `swarm_worker.py` | Multi-threaded bulk AI analyzer |
| `api_schema.json` | Machine-readable API spec (used as AI system prompt) |

## Security

- **Bearer Token Auth** — Auto-generated on each IDA session, stored in temp file
- **Localhost Only** — Binds to `127.0.0.1`, not exposed to network
- **CORS Headers** — Configurable cross-origin policy
- **Ping/Schema exempt** — Only discovery endpoints work without auth

## Requirements

- IDA Pro 9.x with Hex-Rays Decompiler
- Python 3.10+
- `requests` (for CLI/agent)
- `google-genai` (for AI features)

## License

MIT
