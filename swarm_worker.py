import sys
import os
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# Import our bridge client
import bridge_cli

# User-provided API Key and Model
API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")


def load_progress():
    if os.path.exists("progress.json"):
        with open("progress.json", "r") as f:
            return set(json.load(f))
    return set()

def save_progress(processed_eas):
    if not processed_eas: return
    prog = load_progress()
    prog.update(processed_eas)
    with open("progress.json", "w") as f:
        json.dump(list(prog), f)

class FunctionAnalysis(BaseModel):
    suggested_name: str = Field(description="A descriptive, CamelCase or snake_case name for the function based on its logic. Prefix with class name if applicable (e.g. CEntity_GetName). Do not use 'sub_'")
    comment: str = Field(description="A concise technical explanation of what the function does and what data it manipulates.")

def analyze_function_with_gemini(client, ea, pseudocode):
    prompt = f"""
Analyze the following C++ pseudocode from a Source 2 engine reverse engineering session.
Address: {ea}

Pseudocode:
```cpp
{pseudocode}
```

Based on the logic, memory accesses, strings, or constants, suggest a meaningful name for this function. If it looks like a getter, setter, initialization, or specific algorithm, name it accordingly. Also provide a short summary comment. Return the result strictly in JSON.
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FunctionAnalysis,
                temperature=0.2,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"[-] Gemini API error for {ea}: {e}")
        return None

def process_batch(functions_to_process, max_workers=5):
    bridge = bridge_cli.BridgeCLI()
    genai_client = genai.Client(api_key=API_KEY)
    
    print(f"[*] Processing {len(functions_to_process)} functions using {max_workers} threads...")
    
    mutations = []
    
    def worker(func_info):
        ea = func_info["ea"]
        name = func_info["name"]
        print(f"    -> Fetching pseudocode for {name} ({ea})...")
        
        # Thread-local bridge client just in case
        local_bridge = bridge_cli.BridgeCLI()
        
        ps_res = local_bridge.pseudocode(ea)
        if "error" in ps_res:
            print(f"[-] Failed to decompile {ea}: {ps_res['error']}")
            return None
            
        code = ps_res.get("pseudocode", "")
        if not code or len(code) < 10:
            return None
            
        print(f"    -> Analyzing {name} ({ea}) with Gemini...")
        analysis = analyze_function_with_gemini(genai_client, ea, code)
        if analysis:
            new_name = analysis.get("suggested_name", "")
            comment = analysis.get("comment", "")
            # Ensure model didn't just return 'sub_XXXX'
            if new_name and not new_name.startswith("sub_"):
                return {
                    "ea": ea,
                    "old_name": name,
                    "new_name": new_name,
                    "comment": comment
                }
        return None

    # Use ThreadPoolExecutor for concurrent Gemini requests
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, f): f for f in functions_to_process}
        for future in as_completed(futures):
            res = future.result()
            if res:
                mutations.append({"op": "rename-func", "ea": res["ea"], "name": res["new_name"]})
                mutations.append({"op": "comment-func", "ea": res["ea"], "comment": res["comment"]})
                print(f"[+] {res['old_name']} -> {res['new_name']} | {res['comment']}")
                
    if mutations:
        print(f"[*] Applying {len(mutations)} mutations to IDA...")
        res = bridge.batch(mutations)
        print(json.dumps(res, indent=2))
        bridge.wait_analysis()
        print("[+] Batch applied successfully.")
        processed = [m['ea'] for m in mutations if m['op'] == 'rename-func']
        save_progress(processed)
    else:
        print("[-] No mutations to apply.")

def main():
    parser = argparse.ArgumentParser(description="Swarm Worker for IDA Pro using Gemini 3.1 Pro")
    parser.add_argument("--limit", type=int, default=5, help="Max functions to process in this run")
    parser.add_argument("--workers", type=int, default=3, help="Max concurrent Gemini API requests")
    args = parser.parse_args()
    
    bridge = bridge_cli.BridgeCLI()
    
    print("[*] Fetching function list from IDA...")
    res = bridge.functions()
    if "error" in res:
        print(f"[-] Error connecting to bridge: {res['error']}")
        return
        
    all_funcs = res.get("functions", [])
    print(f"[*] Total functions in database: {len(all_funcs)}")
    

    # Filter only unnamed functions
    unnamed = [f for f in all_funcs if f["name"].startswith("sub_")]

    # Check progress
    processed = load_progress()
    unnamed = [f for f in unnamed if f["ea"] not in processed]

    print(f"[*] Unnamed functions: {len(unnamed)}")
    
    if not unnamed:
        print("[+] No unnamed functions left to process!")
        return
        
    to_process = unnamed[:args.limit]
    process_batch(to_process, max_workers=args.workers)

if __name__ == "__main__":
    main()
