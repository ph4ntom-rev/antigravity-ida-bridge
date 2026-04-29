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

# Try exact replacement on start_server and stop_server
# For start_server
source = source.replace("_thread.start()", "_thread.start()\n" + init_hooks)
# For stop_server
source = source.replace("_server.shutdown()", "_server.shutdown()\n" + term_hooks)

with open("ida_plugin/antigravity_server.py", "w") as f:
    f.write(source)
