import re
import os

with open("swarm_worker.py", "r") as f:
    source = f.read()

patch = """
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
"""

if "def load_progress()" not in source:
    idx = source.find("class FunctionAnalysis")
    source = source[:idx] + patch + "\n" + source[idx:]

batch_success_regex = r"(print\(\"\[\+\] Batch applied successfully\.\"\))"
source = re.sub(batch_success_regex, r"\1\n        processed = [m['ea'] for m in mutations if m['op'] == 'rename-func']\n        save_progress(processed)", source)

main_filter = """
    # Filter only unnamed functions
    unnamed = [f for f in all_funcs if f["name"].startswith("sub_")]

    # Check progress
    processed = load_progress()
    unnamed = [f for f in unnamed if f["ea"] not in processed]
"""
source = re.sub(r"    # Filter only unnamed functions.*?unnamed = \[f for f in all_funcs if f\[\"name\"\].startswith\(\"sub_\"\)]", main_filter, source, flags=re.S)

with open("swarm_worker.py", "w") as f:
    f.write(source)
