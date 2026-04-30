"""
Antigravity IDA Bridge — Unified CLI Tool
===========================================
Single-file tool designed for AI IDE agents (like Antigravity IDE).

The IDE agent calls this via run_command to control IDA Pro.
Every command outputs clean JSON for easy parsing.

Usage:
    python bridge.py ping                               # Check if IDA is online
    python bridge.py info                               # Binary metadata
    python bridge.py launch C:\\binary.exe              # Find IDA + open binary
    python bridge.py wait                               # Wait for bridge to come online
    python bridge.py decompile 0x140001000              # Decompile function
    python bridge.py functions                          # List all functions
    python bridge.py functions --limit 20               # First 20 functions
    python bridge.py strings                            # All strings
    python bridge.py strings --filter password          # Search strings
    python bridge.py xrefs 0x140001000                  # Cross-references
    python bridge.py callers 0x140001000                # Who calls this?
    python bridge.py callees 0x140001000                # What does this call?
    python bridge.py imports                            # Imported functions
    python bridge.py exports                            # Exported functions
    python bridge.py bytes 0x140001000 64               # Read 64 bytes
    python bridge.py rename 0x140001000 my_func_name    # Rename function
    python bridge.py comment 0x140001000 "does XYZ"     # Set comment
    python bridge.py exec "print(here())"               # Run IDAPython
    python bridge.py api GET /api/some/endpoint         # Raw API call
    python bridge.py api POST /api/exec --body '{}'     # Raw POST
"""

import sys
import os
import json
import time
import shutil
import glob
import subprocess
import tempfile

# Inline HTTP client — no dependencies beyond requests
try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests not installed. Run: pip install requests"}))
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════

BRIDGE_URL = os.environ.get("IDA_BRIDGE_URL", "http://127.0.0.1:13370")


def get_session():
    """Create HTTP session with auth token."""
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    token_path = os.path.join(tempfile.gettempdir(), ".antigravity_token")
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()
            if token:
                s.headers["Authorization"] = f"Bearer {token}"
    return s


def api_get(path, **params):
    """GET request, returns dict."""
    try:
        r = get_session().get(f"{BRIDGE_URL}{path}", params=params, timeout=30)
        return r.json()
    except requests.ConnectionError:
        return {"error": "Bridge offline. Is IDA Pro running with the plugin?", "online": False}
    except Exception as e:
        return {"error": str(e)}


def api_post(path, data=None):
    """POST request, returns dict."""
    try:
        r = get_session().post(f"{BRIDGE_URL}{path}", json=data or {}, timeout=30)
        return r.json()
    except requests.ConnectionError:
        return {"error": "Bridge offline. Is IDA Pro running with the plugin?", "online": False}
    except Exception as e:
        return {"error": str(e)}


def out(data):
    """Print JSON output."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ═══════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════

def cmd_ping():
    out(api_get("/api/ping"))


def cmd_info():
    out(api_get("/api/info"))


def cmd_decompile(ea):
    out(api_get(f"/api/function/{ea}/pseudocode"))


def cmd_functions(limit=None, offset=0):
    if limit:
        out(api_get("/api/functions-page", offset=offset, limit=limit))
    else:
        out(api_get("/api/functions"))


def cmd_strings(filter_str=None):
    if filter_str:
        out(api_get("/api/strings", filter=filter_str))
    else:
        out(api_get("/api/strings"))


def cmd_xrefs(ea):
    out(api_get(f"/api/function/{ea}/xrefs-to"))


def cmd_callers(ea):
    out(api_get(f"/api/function/{ea}/callers"))


def cmd_callees(ea):
    out(api_get(f"/api/function/{ea}/callees"))


def cmd_imports():
    out(api_get("/api/imports"))


def cmd_exports():
    out(api_get("/api/exports"))


def cmd_bytes(ea, size):
    out(api_get(f"/api/bytes/{ea}/{size}"))


def cmd_rename(ea, name):
    out(api_post(f"/api/function/{ea}/rename", {"name": name}))


def cmd_comment(ea, comment):
    out(api_post(f"/api/function/{ea}/comment", {"comment": comment}))


def cmd_exec(script):
    out(api_post("/api/exec", {"script": script}))


def cmd_api(method, path, body=None):
    if method.upper() == "GET":
        out(api_get(path))
    else:
        data = json.loads(body) if body else {}
        out(api_post(path, data))


def cmd_wait(timeout=120):
    """Wait for bridge to come online."""
    start = time.time()
    while time.time() - start < timeout:
        result = api_get("/api/ping")
        if "error" not in result:
            out({"online": True, "waited": round(time.time() - start, 1)})
            return
        time.sleep(2)
    out({"error": f"Bridge did not come online within {timeout}s", "online": False})


def cmd_launch(binary_path):
    """Find IDA Pro and launch it with the binary."""
    binary_path = os.path.abspath(binary_path)
    if not os.path.exists(binary_path):
        out({"error": f"File not found: {binary_path}"})
        return

    # Check if already online
    result = api_get("/api/ping")
    if "error" not in result:
        out({"status": "already_online", "info": api_get("/api/info")})
        return

    # Find IDA
    ida_exe = _find_ida()
    if not ida_exe:
        out({"error": "IDA Pro not found. Set IDA_DIR env variable or install IDA Pro."})
        return

    # Ensure plugin installed
    ida_dir = os.path.dirname(ida_exe)
    plugin_src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "ida_plugin", "antigravity_server.py")
    plugin_dst = os.path.join(ida_dir, "plugins", "antigravity_server.py")
    if not os.path.exists(plugin_dst) and os.path.exists(plugin_src):
        try:
            os.makedirs(os.path.join(ida_dir, "plugins"), exist_ok=True)
            shutil.copy2(plugin_src, plugin_dst)
        except Exception:
            pass

    # Launch
    log_file = os.path.join(tempfile.gettempdir(), "antigravity_ida.log")
    cmd = [ida_exe, "-A", f"-L{log_file}", binary_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    out({
        "status": "launched",
        "ida": ida_exe,
        "binary": binary_path,
        "pid": proc.pid,
        "next": "Run: python bridge.py wait"
    })


def _find_ida():
    """Find IDA Pro executable."""
    # Env variable
    env_dir = os.environ.get("IDA_DIR")
    if env_dir:
        for name in ["ida64.exe", "ida.exe"]:
            p = os.path.join(env_dir, name)
            if os.path.isfile(p):
                return p

    # Registry
    try:
        import winreg
        for hkey in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                with winreg.OpenKey(hkey, r"Software\Hex-Rays\IDA") as key:
                    ida_dir = winreg.QueryValueEx(key, "InstallDir")[0]
                    for name in ["ida64.exe", "ida.exe"]:
                        p = os.path.join(ida_dir, name)
                        if os.path.isfile(p):
                            return p
            except (FileNotFoundError, OSError):
                continue
    except ImportError:
        pass

    # Common paths
    patterns = [
        os.path.expandvars(r"%ProgramFiles%\IDA Pro*"),
        r"C:\IDA*", r"D:\IDA*", r"C:\Tools\IDA*", r"D:\Tools\IDA*",
    ]
    for pattern in patterns:
        for match in sorted(glob.glob(pattern), reverse=True):
            for name in ["ida64.exe", "ida.exe"]:
                p = os.path.join(match, name)
                if os.path.isfile(p):
                    return p

    # PATH
    return shutil.which("ida64") or shutil.which("ida64.exe")


# ═══════════════════════════════════════════════════════════════
# Main — parse args and dispatch
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: python bridge.py <command> [args...]")
        print("Commands: ping, info, launch, wait, decompile, functions,")
        print("          strings, xrefs, callers, callees, imports, exports,")
        print("          bytes, rename, comment, exec, api")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "ping":
        cmd_ping()
    elif cmd == "info":
        cmd_info()
    elif cmd == "launch":
        if len(sys.argv) < 3:
            out({"error": "Usage: python bridge.py launch <binary_path>"})
        else:
            cmd_launch(sys.argv[2])
    elif cmd == "wait":
        timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 120
        cmd_wait(timeout)
    elif cmd in ["decompile", "decomp", "pseudo", "pseudocode"]:
        if len(sys.argv) < 3:
            out({"error": "Usage: python bridge.py decompile <address>"})
        else:
            cmd_decompile(sys.argv[2])
    elif cmd in ["functions", "funcs"]:
        limit = None
        for i, a in enumerate(sys.argv):
            if a == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
        cmd_functions(limit=limit)
    elif cmd in ["strings", "str"]:
        filt = None
        for i, a in enumerate(sys.argv):
            if a == "--filter" and i + 1 < len(sys.argv):
                filt = sys.argv[i + 1]
        cmd_strings(filter_str=filt)
    elif cmd == "xrefs":
        cmd_xrefs(sys.argv[2])
    elif cmd == "callers":
        cmd_callers(sys.argv[2])
    elif cmd == "callees":
        cmd_callees(sys.argv[2])
    elif cmd == "imports":
        cmd_imports()
    elif cmd == "exports":
        cmd_exports()
    elif cmd == "bytes":
        cmd_bytes(sys.argv[2], sys.argv[3])
    elif cmd == "rename":
        cmd_rename(sys.argv[2], sys.argv[3])
    elif cmd == "comment":
        cmd_comment(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "exec":
        cmd_exec(" ".join(sys.argv[2:]))
    elif cmd == "api":
        method = sys.argv[2]
        path = sys.argv[3]
        body = None
        for i, a in enumerate(sys.argv):
            if a == "--body" and i + 1 < len(sys.argv):
                body = sys.argv[i + 1]
        cmd_api(method, path, body)
    else:
        out({"error": f"Unknown command: {cmd}"})


if __name__ == "__main__":
    main()
