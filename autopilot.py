"""
Antigravity IDA Bridge v5.0 — Autopilot
==========================================
Fully autonomous binary analysis pipeline.

Usage from terminal:
    python autopilot.py "C:\\path\\to\\binary.exe" "recover all function logic"
    python autopilot.py binary.dll "find vulnerabilities" --backend ollama
    python autopilot.py firmware.bin "map the bootloader" --ida "C:\\IDA\\ida64.exe"

Usage from Antigravity IDE (this file is callable by the IDE agent):
    User says: "analyze C:\\malware.exe and recover the logic"
    IDE agent calls: autopilot.run("C:\\malware.exe", "recover the logic")
"""

import os
import sys
import time
import json
import shutil
import subprocess
import argparse
import winreg
import tempfile
import glob

from core.client import BridgeClient
from core.schema import SchemaLoader
from backends.base import AgentBackend

# Import all backends for registration
import backends.gemini_backend      # noqa: F401
import backends.ollama_backend      # noqa: F401
import backends.openai_backend      # noqa: F401
import backends.anthropic_backend   # noqa: F401
import backends.deepseek_backend    # noqa: F401


# ═══════════════════════════════════════════════════════════════
# 1. IDA Pro Auto-Discovery
# ═══════════════════════════════════════════════════════════════

def find_ida_installation() -> dict:
    """Auto-detect IDA Pro installation on the system.
    
    Search order:
    1. IDA_DIR environment variable
    2. Windows Registry (Hex-Rays installer keys)
    3. Common installation paths
    4. PATH search
    
    Returns:
        dict with 'ida_dir', 'ida_exe', 'ida64_exe', 'version'
    """
    result = {"ida_dir": None, "ida_exe": None, "ida64_exe": None, "version": None}

    # Method 1: Environment variable
    env_dir = os.environ.get("IDA_DIR")
    if env_dir and os.path.isdir(env_dir):
        result["ida_dir"] = env_dir
        _populate_executables(result)
        if result["ida64_exe"]:
            print(f"[+] IDA found via $IDA_DIR: {env_dir}")
            return result

    # Method 2: Windows Registry
    registry_paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\Hex-Rays\IDA"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Hex-Rays\IDA"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Hex-Rays\IDA"),
    ]
    for hkey, subkey in registry_paths:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                ida_dir = winreg.QueryValueEx(key, "InstallDir")[0]
                if os.path.isdir(ida_dir):
                    result["ida_dir"] = ida_dir
                    _populate_executables(result)
                    if result["ida64_exe"]:
                        print(f"[+] IDA found via registry: {ida_dir}")
                        return result
        except (FileNotFoundError, OSError):
            continue

    # Method 3: Common paths
    common_dirs = [
        os.path.expandvars(r"%ProgramFiles%\IDA Pro*"),
        os.path.expandvars(r"%ProgramFiles(x86)%\IDA Pro*"),
        r"C:\IDA*",
        r"D:\IDA*",
        os.path.expanduser(r"~\IDA*"),
        os.path.expandvars(r"%ProgramFiles%\IDA Free*"),
        r"C:\Tools\IDA*",
        r"D:\Tools\IDA*",
        r"C:\RE\IDA*",
    ]
    for pattern in common_dirs:
        matches = sorted(glob.glob(pattern), reverse=True)  # Latest version first
        for match in matches:
            if os.path.isdir(match):
                result["ida_dir"] = match
                _populate_executables(result)
                if result["ida64_exe"]:
                    print(f"[+] IDA found at: {match}")
                    return result

    # Method 4: PATH
    ida64_path = shutil.which("ida64") or shutil.which("ida64.exe")
    if ida64_path:
        result["ida_dir"] = os.path.dirname(ida64_path)
        result["ida64_exe"] = ida64_path
        ida_path = shutil.which("ida") or shutil.which("ida.exe")
        result["ida_exe"] = ida_path
        print(f"[+] IDA found in PATH: {result['ida_dir']}")
        return result

    return result


def _populate_executables(result: dict):
    """Fill in ida_exe and ida64_exe from ida_dir."""
    d = result["ida_dir"]
    if not d:
        return

    for name in ["ida64.exe", "ida64"]:
        path = os.path.join(d, name)
        if os.path.isfile(path):
            result["ida64_exe"] = path
            break

    for name in ["ida.exe", "ida"]:
        path = os.path.join(d, name)
        if os.path.isfile(path):
            result["ida_exe"] = path
            break

    # Try to detect version from directory name
    dirname = os.path.basename(d)
    for part in dirname.split():
        if any(c.isdigit() for c in part):
            result["version"] = part
            break


def select_ida_executable(ida_info: dict, binary_path: str) -> str:
    """Select the right IDA executable (ida vs ida64) based on binary architecture."""
    # Default to ida64 — most modern binaries are 64-bit
    exe = ida_info.get("ida64_exe")
    if exe:
        return exe
    exe = ida_info.get("ida_exe")
    if exe:
        return exe
    return None


# ═══════════════════════════════════════════════════════════════
# 2. Plugin Installation Check
# ═══════════════════════════════════════════════════════════════

def ensure_plugin_installed(ida_dir: str) -> bool:
    """Make sure antigravity_server.py is in IDA's plugins folder."""
    plugins_dir = os.path.join(ida_dir, "plugins")
    target = os.path.join(plugins_dir, "antigravity_server.py")
    
    if os.path.exists(target):
        print(f"[+] Plugin already installed: {target}")
        return True

    # Find our plugin source
    source = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                          "ida_plugin", "antigravity_server.py")
    if not os.path.exists(source):
        print(f"[-] Plugin source not found: {source}")
        return False

    # Copy plugin
    try:
        os.makedirs(plugins_dir, exist_ok=True)
        shutil.copy2(source, target)
        print(f"[+] Plugin installed: {target}")
        return True
    except PermissionError:
        print(f"[-] Permission denied installing plugin to {plugins_dir}")
        print("    Run as administrator or copy manually.")
        return False


# ═══════════════════════════════════════════════════════════════
# 3. IDA Pro Launcher
# ═══════════════════════════════════════════════════════════════

def launch_ida(ida_exe: str, binary_path: str, autonomous: bool = True) -> subprocess.Popen:
    """Launch IDA Pro with the target binary.
    
    Args:
        ida_exe: Path to ida64.exe or ida.exe
        binary_path: Path to the binary to analyze
        autonomous: If True, run in autonomous mode (-A flag)
    """
    binary_path = os.path.abspath(binary_path)
    
    if not os.path.exists(binary_path):
        raise FileNotFoundError(f"Binary not found: {binary_path}")

    cmd = [ida_exe]
    if autonomous:
        # -A = autonomous mode (no dialogs)
        # -L = log file
        log_file = os.path.join(tempfile.gettempdir(), "antigravity_ida.log")
        cmd.extend(["-A", f"-L{log_file}"])
    
    cmd.append(binary_path)

    print(f"[+] Launching IDA: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[+] IDA PID: {proc.pid}")
    return proc


# ═══════════════════════════════════════════════════════════════
# 4. Bridge Connection Waiter
# ═══════════════════════════════════════════════════════════════

def wait_for_bridge(url: str = "http://127.0.0.1:13370", 
                    timeout: int = 120, 
                    poll_interval: float = 2.0) -> BridgeClient:
    """Wait for the IDA Bridge to come online.
    
    Args:
        url: Bridge URL
        timeout: Maximum seconds to wait
        poll_interval: Seconds between connection attempts
    
    Returns:
        Connected BridgeClient instance
    """
    client = BridgeClient(url=url)
    start = time.time()
    attempt = 0

    print(f"\n[*] Waiting for bridge at {url}...")
    
    while time.time() - start < timeout:
        attempt += 1
        result = client.ping()
        
        if "error" not in result:
            elapsed = time.time() - start
            print(f"[+] Bridge ONLINE after {elapsed:.1f}s (attempt #{attempt})")
            
            # Wait a bit more for IDA to finish auto-analysis
            info = client.info()
            print(f"    Binary: {info.get('file', '?')}")
            print(f"    Arch:   {info.get('proc', '?')} {info.get('bits', '?')}-bit")
            print(f"    Funcs:  {info.get('func_count', '?')}")
            return client

        # Show progress
        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        sym = spinner[attempt % len(spinner)]
        elapsed = time.time() - start
        print(f"  {sym} Waiting... ({elapsed:.0f}s / {timeout}s)", end="\r")
        
        time.sleep(poll_interval)

    raise TimeoutError(f"Bridge did not come online within {timeout}s")


# ═══════════════════════════════════════════════════════════════
# 5. Autonomous Analysis Engine
# ═══════════════════════════════════════════════════════════════

def run_analysis(client: BridgeClient, task: str, backend_name: str = "auto", 
                 model: str = None, output_file: str = None) -> str:
    """Run autonomous analysis with the specified AI backend.
    
    Args:
        client: Connected BridgeClient
        task: Natural language task description
        backend_name: Backend to use (auto, ollama, gemini, etc.)
        model: Optional model override
        output_file: Optional file to save results
    
    Returns:
        Analysis result as string
    """
    schema = SchemaLoader()

    # Select backend
    if backend_name == "auto":
        backend_name = AgentBackend.auto_select()
        if not backend_name:
            raise RuntimeError(
                "No AI backend available. Set GEMINI_API_KEY, OPENAI_API_KEY, "
                "ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, or install Ollama."
            )

    backend_cls = AgentBackend.get_backend(backend_name)
    if not backend_cls:
        raise ValueError(f"Unknown backend: {backend_name}")

    backend = backend_cls(client=client, schema=schema, model=model)

    if not backend.is_available():
        raise RuntimeError(f"Backend '{backend_name}' is not configured.")

    print(f"\n[+] AI Backend: {backend.name} ({backend.model})")
    print(f"[+] Task: {task}")
    print(f"\n{'='*58}")
    print("  AUTONOMOUS ANALYSIS STARTED")
    print(f"{'='*58}\n")

    # Get binary context first
    info = client.info()
    context = (
        f"You are analyzing: {info.get('file', 'unknown binary')}\n"
        f"Architecture: {info.get('proc', '?')} {info.get('bits', '?')}-bit\n"
        f"Total functions: {info.get('func_count', '?')}\n"
        f"Entry point: {info.get('entry_point', '?')}\n\n"
        f"USER TASK: {task}\n\n"
        f"Perform a thorough analysis. Use call_bridge_api to explore the binary "
        f"and execute_idapython for custom scripts. Be systematic and comprehensive."
    )

    result = backend.chat(context)

    print(f"\n{'='*58}")
    print("  ANALYSIS COMPLETE")
    print(f"{'='*58}\n")
    print(result)

    # Save results
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Antigravity Analysis Report\n\n")
            f.write(f"**Binary:** {info.get('file', '?')}\n")
            f.write(f"**Architecture:** {info.get('proc', '?')} {info.get('bits', '?')}-bit\n")
            f.write(f"**Task:** {task}\n")
            f.write(f"**Backend:** {backend.name} ({backend.model})\n\n")
            f.write(f"---\n\n{result}\n")
        print(f"\n[+] Report saved: {output_file}")

    return result


# ═══════════════════════════════════════════════════════════════
# 6. Public API (for IDE / programmatic use)
# ═══════════════════════════════════════════════════════════════

def run(binary_path: str, task: str, 
        backend: str = "auto", model: str = None,
        ida_path: str = None, output: str = None,
        bridge_url: str = "http://127.0.0.1:13370",
        timeout: int = 120, skip_launch: bool = False) -> str:
    """
    Fully autonomous binary analysis — single function call.
    
    This is the main entry point for IDE integration.
    
    Args:
        binary_path: Path to the target binary
        task: Natural language description of what to analyze
        backend: AI backend (auto, ollama, gemini, openai, anthropic, deepseek)
        model: Optional model override
        ida_path: Optional explicit path to IDA executable
        output: Optional output file for the report
        bridge_url: IDA Bridge URL
        timeout: Max seconds to wait for IDA/bridge
        skip_launch: If True, assume IDA is already running
        
    Returns:
        Analysis result string
    
    Example:
        >>> from autopilot import run
        >>> result = run("C:/samples/malware.exe", "find all C2 communication logic")
    """
    print("=" * 58)
    print("  Antigravity Autopilot v5.0")
    print("=" * 58)
    print(f"\n[+] Target: {binary_path}")
    print(f"[+] Task:   {task}")

    ida_proc = None

    try:
        if not skip_launch:
            # Step 1: Find IDA
            if ida_path:
                ida_exe = ida_path
                ida_dir = os.path.dirname(ida_path)
                print(f"[+] Using specified IDA: {ida_path}")
            else:
                ida_info = find_ida_installation()
                if not ida_info["ida64_exe"] and not ida_info["ida_exe"]:
                    raise FileNotFoundError(
                        "IDA Pro not found! Install IDA or set IDA_DIR environment variable.\n"
                        "Or specify path: python autopilot.py binary.exe task --ida /path/to/ida64.exe"
                    )
                ida_exe = select_ida_executable(ida_info, binary_path)
                ida_dir = ida_info["ida_dir"]

            # Step 2: Ensure plugin is installed
            ensure_plugin_installed(ida_dir)

            # Step 3: Check if bridge is already online (IDA might be running)
            client = BridgeClient(url=bridge_url)
            if client.is_online():
                print("[+] Bridge already online — skipping IDA launch")
            else:
                # Step 4: Launch IDA
                ida_proc = launch_ida(ida_exe, binary_path)

            # Step 5: Wait for bridge
            client = wait_for_bridge(url=bridge_url, timeout=timeout)
        else:
            # Skip launch — connect to existing bridge
            client = wait_for_bridge(url=bridge_url, timeout=30)

        # Step 6: Run analysis
        result = run_analysis(
            client=client,
            task=task,
            backend_name=backend,
            model=model,
            output_file=output,
        )

        return result

    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
        return ""
    except Exception as e:
        print(f"\n[-] Autopilot error: {e}")
        raise


# ═══════════════════════════════════════════════════════════════
# 7. CLI Entry Point
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Antigravity Autopilot — Fully autonomous binary analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python autopilot.py malware.exe "recover all function logic and find C2 servers"
  python autopilot.py firmware.bin "map the bootloader entry and peripherals" --backend ollama
  python autopilot.py game.dll "find anti-cheat hooks" --ida "C:\\IDA\\ida64.exe"
  python autopilot.py sample.sys "analyze the driver dispatch routines" -o report.md
  python autopilot.py --skip-launch "explain the main function" (IDA already running)
        """
    )
    parser.add_argument("binary", nargs="?", help="Path to target binary")
    parser.add_argument("task", nargs="?", default="Perform comprehensive analysis: identify main logic, find strings, map function call graph, and document key functions.",
                        help="Analysis task description")
    parser.add_argument("--backend", "-b", default="auto",
                        help="AI backend: auto, ollama, gemini, openai, anthropic, deepseek")
    parser.add_argument("--model", "-m", default=None, help="Model override")
    parser.add_argument("--ida", default=None, help="Path to IDA executable")
    parser.add_argument("--output", "-o", default=None, help="Save report to file")
    parser.add_argument("--url", default="http://127.0.0.1:13370", help="Bridge URL")
    parser.add_argument("--timeout", "-t", type=int, default=120, help="Max wait time for IDA")
    parser.add_argument("--skip-launch", "-s", action="store_true",
                        help="Skip IDA launch (assume already running)")
    parser.add_argument("--find-ida", action="store_true",
                        help="Just find IDA installation and exit")

    args = parser.parse_args()

    # Just find IDA mode
    if args.find_ida:
        info = find_ida_installation()
        if info["ida_dir"]:
            print(f"\nIDA Directory: {info['ida_dir']}")
            print(f"IDA (32-bit):  {info['ida_exe'] or 'not found'}")
            print(f"IDA (64-bit):  {info['ida64_exe'] or 'not found'}")
            print(f"Version:       {info['version'] or 'unknown'}")
        else:
            print("\n[-] IDA Pro not found on this system.")
            print("    Set IDA_DIR environment variable or install IDA Pro.")
        sys.exit(0)

    # Skip-launch mode (no binary needed)
    if args.skip_launch:
        task = args.task
        if args.binary:
            task = args.binary  # First positional arg becomes task when no binary
        run(
            binary_path="(already loaded)",
            task=task,
            backend=args.backend,
            model=args.model,
            output=args.output,
            bridge_url=args.url,
            timeout=args.timeout,
            skip_launch=True,
        )
        sys.exit(0)

    if not args.binary:
        parser.print_help()
        print("\n[-] Specify a binary to analyze!")
        sys.exit(1)

    run(
        binary_path=args.binary,
        task=args.task,
        backend=args.backend,
        model=args.model,
        ida_path=args.ida,
        output=args.output,
        bridge_url=args.url,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
