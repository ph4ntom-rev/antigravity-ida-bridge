# Antigravity IDE ↔ IDA Bridge — Agent Skill
# ============================================
# This skill teaches the Antigravity IDE agent how to use the IDA Bridge
# to perform reverse engineering tasks autonomously.
#
# Place this file in your workspace so the IDE agent reads it.
#
# HOW IT WORKS:
# 1. User says: "analyze C:\malware.exe"
# 2. IDE agent reads this skill file
# 3. IDE agent uses run_command to call bridge.py
# 4. IDE agent interprets results and continues analysis
#
# The IDE agent IS the AI brain — no separate agent.py needed.

## What is the IDA Bridge?

The IDA Bridge is a REST API server running inside IDA Pro on http://127.0.0.1:13370.
It exposes 90+ endpoints that let you read and write IDA's analysis database via HTTP.

## How the IDE Agent Should Use It

The agent (you) can control IDA Pro by running Python commands via `run_command`.
The main tool is `bridge.py` — a single-file CLI that wraps all bridge operations.

### Quick Reference

```bash
# Check if bridge is online
python bridge.py ping

# Get binary info
python bridge.py info

# Decompile a function
python bridge.py decompile 0x140001000

# Search for strings
python bridge.py strings --filter "password"

# List all functions
python bridge.py functions --limit 50

# Get cross-references
python bridge.py xrefs 0x140001000

# Execute custom IDAPython script
python bridge.py exec "print(idc.get_func_name(here()))"

# Run any API endpoint directly
python bridge.py api GET /api/function/0x140001000/callers
python bridge.py api POST /api/function/0x140001000/rename --body "{\"name\": \"init_network\"}"
```

### Autonomous Workflow

When the user asks you to analyze a binary, follow this workflow:

1. **CHECK**: Run `python bridge.py ping` to see if IDA is running
2. **LAUNCH** (if needed): Run `python bridge.py launch C:\path\to\binary.exe`
   - This finds IDA Pro automatically and opens the binary
   - Wait for the bridge to come online with `python bridge.py wait`
3. **ORIENT**: Run `python bridge.py info` to understand the binary (arch, size, entry point)
4. **ANALYZE**: Use bridge.py commands to explore:
   - `python bridge.py functions` — see all functions
   - `python bridge.py strings` — find interesting strings
   - `python bridge.py decompile <addr>` — read function code
   - `python bridge.py xrefs <addr>` — follow references
5. **MUTATE**: Rename functions, add comments, set types to document findings
6. **REPORT**: Summarize your analysis to the user

### Key Endpoints You Can Call

**Reading data:**
- `/api/info` — binary metadata
- `/api/functions` — all functions list
- `/api/function/<ea>/pseudocode` — decompiled C code
- `/api/function/<ea>/callers` — who calls this function
- `/api/function/<ea>/callees` — what this function calls  
- `/api/function/<ea>/xrefs-to` — all cross-references to address
- `/api/strings` — all strings (accepts ?filter= param)
- `/api/imports` — imported functions
- `/api/exports` — exported functions
- `/api/bytes/<ea>/<size>` — raw bytes at address

**Writing data:**
- `/api/function/<ea>/rename` POST `{"name": "..."}` — rename function
- `/api/function/<ea>/comment` POST `{"comment": "..."}` — add comment
- `/api/exec` POST `{"script": "..."}` — execute any IDAPython
- `/api/undo` POST — undo last change
- `/api/save` POST — save IDA database

### Tips for the Agent

1. Always start with `ping` before any analysis
2. Use `info` to understand what you're looking at
3. Decompile entry point first to find the program's starting logic
4. Follow cross-references to trace data flow
5. Search strings for clues (API names, error messages, URLs, IPs)
6. Rename functions as you understand them — this helps you track your progress
7. If a function is too complex, break it down by looking at its callees
8. Use `exec` for anything the REST API doesn't cover
