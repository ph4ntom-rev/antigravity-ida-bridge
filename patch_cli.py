import re

with open("bridge_cli.py", "r") as f:
    source = f.read()

new_methods = """
    def ctree(self, ea): return self._get(f"/api/function/{ea}/ctree")
    def microcode(self, ea): return self._get(f"/api/function/{ea}/microcode")
    def types(self): return self._get("/api/types")
    def dbg_get_regs(self): return self._get("/api/dbg/regs")
    def dbg_get_stack(self): return self._get("/api/dbg/stack")
    def callers(self, ea): return self._get(f"/api/function/{ea}/callers")
    def callees(self, ea): return self._get(f"/api/function/{ea}/callees")
    def macro_analyze_context(self, ea): return self._get(f"/api/macro/analyze_context", {"ea": ea})
    def events(self): return self._get("/api/events")
"""

if "def ctree" not in source:
    idx = source.find("def rename_func")
    source = source[:idx] + new_methods + "\n    " + source[idx:]

new_parsers = """
    p = sub.add_parser("ctree", help="Get AST"); p.add_argument("ea")
    p = sub.add_parser("microcode", help="Get microcode"); p.add_argument("ea")
    p = sub.add_parser("types", help="List types")
    p = sub.add_parser("debugger", help="Get debugger regs/stack"); p.add_argument("cmd", choices=["regs", "stack"])
    p = sub.add_parser("callers", help="Get function callers"); p.add_argument("ea")
    p = sub.add_parser("callees", help="Get function callees"); p.add_argument("ea")
    p = sub.add_parser("analyze_context", help="Macro analyze context"); p.add_argument("ea")
    p = sub.add_parser("events", help="Stream SSE events")
"""

if "add_parser(\"ctree\"" not in source:
    idx2 = source.find("    args = parser.parse_args()")
    source = source[:idx2] + new_parsers + "\n" + source[idx2:]

new_logic = """
    elif c == "ctree": r = cli.ctree(args.ea)
    elif c == "microcode": r = cli.microcode(args.ea)
    elif c == "types": r = cli.types()
    elif c == "debugger":
        r = cli.dbg_get_regs() if args.cmd == "regs" else cli.dbg_get_stack()
    elif c == "callers": r = cli.callers(args.ea)
    elif c == "callees": r = cli.callees(args.ea)
    elif c == "analyze_context": r = cli.macro_analyze_context(args.ea)
    elif c == "events": r = cli.events()
"""

if "elif c == \"ctree\":" not in source:
    idx3 = source.find("    else:\n        parser.print_help()")
    source = source[:idx3] + new_logic + "\n" + source[idx3:]

with open("bridge_cli.py", "w") as f:
    f.write(source)
