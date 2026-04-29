import sys
import os
import json
from google import genai
from google.genai import types

import bridge_cli

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")

cli = bridge_cli.BridgeCLI()

def load_schema():
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_schema.json")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def execute_idapython(script_code: str) -> str:
    """Execute arbitrary Python script dynamically within IDA Pro and return the result.
    
    The script has full access to IDA APIs like idc, idaapi, idautils, ida_funcs, etc.
    To return specific structured data, place it in the global 'result' dictionary (e.g., result['my_key'] = 123).
    Standard output (print statements) is captured and returned as well.
    
    Args:
        script_code: A valid Python script string to execute in IDA.
    """
    print("\n[+] Agent is executing IDAPython script:")
    print("--------------------------------------------------")
    print(script_code.strip())
    print("--------------------------------------------------")
    
    try:
        response = cli.exec_python(script_code)
        if "error" in response and response.get("success") is False:
            print("[-] Script execution returned an error.")
        else:
            print(f"[+] Script executed successfully. Keys returned: {list(response.get('result', {}).keys())}")
        return json.dumps(response, indent=2)
    except Exception as e:
        err_msg = f"Failed to connect or execute script: {e}"
        print(f"[-] {err_msg}")
        return json.dumps({"success": False, "error": err_msg})

def call_bridge_api(method: str, path: str, body: str = "{}") -> str:
    """Call any Antigravity IDA Bridge REST endpoint directly.
    
    Use this for structured API calls instead of writing IDAPython scripts.
    See the api_schema for all available endpoints.
    
    Args:
        method: HTTP method - 'GET' or 'POST'
        path: API path, e.g. '/api/function/0x140001000/pseudocode'
        body: JSON string body for POST requests (optional for GET)
    """
    print(f"\n[+] Agent calling bridge: {method} {path}")
    try:
        if method.upper() == "GET":
            r = cli.session.get(f"{cli.base_url}{path}", timeout=30)
        else:
            data = json.loads(body) if body else {}
            r = cli.session.post(f"{cli.base_url}{path}", json=data, timeout=30)
        result = r.json()
        # Truncate large responses for display
        result_str = json.dumps(result, indent=2)
        if len(result_str) > 2000:
            print(f"[+] Response received ({len(result_str)} chars, truncated in display)")
        else:
            print(f"[+] Response: {result_str[:500]}")
        return result_str
    except Exception as e:
        err = f"Bridge API error: {e}"
        print(f"[-] {err}")
        return json.dumps({"error": err})

def main():
    if not API_KEY:
        print("[-] ERROR: Set GEMINI_API_KEY environment variable.")
        print("    Example: set GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    print("==================================================")
    print("    Antigravity IDA Bridge v4.0 — AI Orchestrator")
    print("==================================================")
    
    ping = cli.ping()
    if "error" in ping:
        print(f"[-] Warning: Bridge seems offline ({ping['error']}).")
    else:
        print(f"[+] Bridge is ONLINE (v{ping.get('version', '?')}).")

    # Load API schema for system instruction
    schema = load_schema()
    
    if schema:
        system_instruction = schema.get("system_prompt", "") + "\n\n"
        system_instruction += "## Available API Endpoints\n\n"
        system_instruction += json.dumps(schema.get("endpoints", {}), indent=1) + "\n\n"
        system_instruction += "## Workflows\n\n"
        system_instruction += json.dumps(schema.get("workflows", []), indent=1) + "\n\n"
        system_instruction += "## Tips\n\n"
        system_instruction += json.dumps(schema.get("tips", []), indent=1) + "\n\n"
        system_instruction += (
            "You have two tools:\n"
            "1. `call_bridge_api(method, path, body)` - For structured REST calls to any endpoint listed above.\n"
            "2. `execute_idapython(script_code)` - For arbitrary IDAPython when no endpoint covers your need.\n"
            "Prefer `call_bridge_api` when a dedicated endpoint exists. Use `execute_idapython` for complex custom logic.\n"
        )
        print(f"[+] Loaded api_schema.json ({len(schema.get('endpoints',{}).get('read',[]))} read + {len(schema.get('endpoints',{}).get('write',[]))} write endpoints)")
    else:
        print("[-] api_schema.json not found, using minimal system prompt.")
        system_instruction = (
            "You are an expert reverse engineering AI agent connected to IDA Pro via Bridge API. "
            "Use execute_idapython() to run scripts and call_bridge_api() for REST calls."
        )
    
    client = genai.Client(api_key=API_KEY)
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[execute_idapython, call_bridge_api],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
        temperature=0.2,
    )
    
    chat = client.chats.create(model=MODEL_NAME, config=config)
    
    print(f"\n[+] Agent ready (model: {MODEL_NAME}). Type 'exit' to quit.")
    
    while True:
        try:
            user_input = input("\n[User]> ")
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input.strip():
                continue
                
            print("\n[Agent is thinking...]")
            response = chat.send_message(user_input)
            
            print(f"\n[Agent]> {response.text}")
            
        except KeyboardInterrupt:
            print("\n[+] Exiting...")
            break
        except Exception as e:
            print(f"\n[-] Error: {e}")

if __name__ == "__main__":
    main()
