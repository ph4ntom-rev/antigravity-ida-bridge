"""
Antigravity IDA Bridge v5.1 — Unified AI Agent
================================================
Single entry point for all AI backends.

Usage:
    python agent.py                          # Auto-detect best backend
    python agent.py --backend ollama         # Use local Ollama
    python agent.py --backend gemini         # Use Google Gemini
    python agent.py --backend openai         # Use OpenAI GPT-4o
    python agent.py --backend anthropic      # Use Anthropic Claude
    python agent.py --backend deepseek       # Use DeepSeek
    python agent.py --list-backends          # Show available backends
    python agent.py --backend ollama --model qwen2.5:72b
"""

import sys
import argparse

from core.client import BridgeClient
from core.schema import SchemaLoader
from backends.base import AgentBackend

# Import all backends to trigger registration
import backends.gemini_backend      # noqa: F401
import backends.ollama_backend      # noqa: F401
import backends.openai_backend      # noqa: F401
import backends.anthropic_backend   # noqa: F401
import backends.deepseek_backend    # noqa: F401


def print_banner():
    print("=" * 58)
    print("  Antigravity IDA Bridge v5.1 — Multi-Backend AI Agent")
    print("=" * 58)


def list_backends():
    """Print available backends and their status."""
    print_banner()
    print("\nAvailable Backends:\n")
    backends = AgentBackend.list_backends()
    
    for key, info in backends.items():
        status = "[OK] READY" if info.get("available") else "[--] NOT CONFIGURED"
        model = info.get("model", "?")
        name = info.get("name", key)
        print(f"  {key:12s}  {name:20s}  model: {model:30s}  {status}")

    print("\nUsage:")
    print("  python agent.py --backend <name>")
    print("  python agent.py --backend <name> --model <model_id>")


def main():
    parser = argparse.ArgumentParser(description="Antigravity IDA Bridge — AI Agent")
    parser.add_argument("--backend", "-b", default="auto",
                        help="Backend to use: ollama, gemini, openai, anthropic, deepseek, auto")
    parser.add_argument("--model", "-m", default=None,
                        help="Override model name (e.g., llama3.1, gpt-4o, claude-sonnet-4)")
    parser.add_argument("--list-backends", "-l", action="store_true",
                        help="List available backends and exit")
    parser.add_argument("--url", default=None,
                        help="IDA Bridge URL (default: http://127.0.0.1:13370)")
    args = parser.parse_args()

    if args.list_backends:
        list_backends()
        sys.exit(0)

    print_banner()

    # Initialize core
    client = BridgeClient(url=args.url)
    schema = SchemaLoader()

    # Check bridge connectivity
    ping = client.ping()
    if "error" in ping:
        print(f"\n[!] Bridge offline: {ping['error']}")
        print("    Make sure antigravity_server.py is loaded in IDA Pro.")
    else:
        print(f"\n[+] Bridge ONLINE (v{ping.get('version', '?')})")
        info = client.info()
        if "error" not in info:
            print(f"    Binary: {info.get('file', '?')}")
            print(f"    Arch: {info.get('proc', '?')} {info.get('bits', '?')}-bit")

    # Schema info
    if schema.is_loaded:
        r, w = schema.endpoint_count
        print(f"[+] Schema loaded ({r} read + {w} write endpoints)")
    else:
        print("[!] api_schema.json not found — using minimal prompt")

    # Select backend
    backend_name = args.backend
    if backend_name == "auto":
        backend_name = AgentBackend.auto_select()
        if not backend_name:
            print("\n[-] No backend available!")
            print("    Set one of: GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY")
            print("    Or install Ollama: https://ollama.com")
            print("\n    Run: python agent.py --list-backends")
            sys.exit(1)
        print(f"[+] Auto-selected backend: {backend_name}")

    backend_cls = AgentBackend.get_backend(backend_name)
    if not backend_cls:
        print(f"\n[-] Unknown backend: {backend_name}")
        print("    Available: ollama, gemini, openai, anthropic, deepseek")
        sys.exit(1)

    backend = backend_cls(client=client, schema=schema, model=args.model)

    if not backend.is_available():
        print(f"\n[-] Backend '{backend_name}' is not configured.")
        if backend_name == "ollama":
            print("    Make sure Ollama is running: https://ollama.com")
        else:
            env_var = getattr(backend, "api_key_env", f"{backend_name.upper()}_API_KEY")
            print(f"    Set environment variable: {env_var}")
        sys.exit(1)

    print(f"\n[+] Agent ready | Backend: {backend.name} | Model: {backend.model}")
    print("    Type 'exit' to quit, 'switch <backend>' to change backend\n")

    # Chat loop
    while True:
        try:
            user_input = input("[User]> ")
            if not user_input.strip():
                continue
            if user_input.lower() in ["exit", "quit"]:
                break
            if user_input.lower().startswith("switch "):
                new_backend = user_input.split(" ", 1)[1].strip()
                new_cls = AgentBackend.get_backend(new_backend)
                if new_cls:
                    backend = new_cls(client=client, schema=schema)
                    print(f"[+] Switched to {backend.name} ({backend.model})")
                else:
                    print(f"[-] Unknown backend: {new_backend}")
                continue

            print("\n[Agent is thinking...]\n")
            response = backend.chat(user_input)
            print(f"\n[Agent]> {response}\n")

        except KeyboardInterrupt:
            print("\n[+] Exiting...")
            break
        except Exception as e:
            print(f"\n[-] Error: {e}\n")


if __name__ == "__main__":
    main()
