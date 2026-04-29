import re

with open("ida_plugin/antigravity_server.py", "r") as f:
    source = f.read()

init_hooks = """
    ui_hooks.hook()
    if dbg_hooks:
        dbg_hooks.hook()
"""

term_hooks = """
    ui_hooks.unhook()
    if dbg_hooks:
        dbg_hooks.unhook()
"""

# Inject into start_server
source = re.sub(r"(def start_server\(.*?:.*?\n.*?_thread\.start\(\))", r"\1" + init_hooks, source, flags=re.S)

# Inject into stop_server
source = re.sub(r"(def stop_server\(\):.*?\n.*?_server\.server_close\(\))", r"\1" + term_hooks, source, flags=re.S)

with open("ida_plugin/antigravity_server.py", "w") as f:
    f.write(source)
