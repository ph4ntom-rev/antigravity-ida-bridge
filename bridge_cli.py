#!/usr/bin/env python3
"""
Antigravity-IDA Bridge CLI
============================
Command-line interface for interacting with the IDA Bridge server.
Used by Antigravity agent via terminal commands.

Usage:
  python bridge_cli.py info
  python bridge_cli.py functions
  python bridge_cli.py pseudocode 0x14005000
  python bridge_cli.py imports
  python bridge_cli.py strings --filter "http"
  python bridge_cli.py rename-func 0x14005000 dga_generate
  python bridge_cli.py rename-var 0x14005000 v4 is_generated
  python bridge_cli.py batch mutations.json
  python bridge_cli.py ping
"""

import sys
import json
import argparse
import requests

DEFAULT_URL = "http://127.0.0.1:13370"
TIMEOUT = 30

def _load_token():
    import tempfile, os
    token_path = os.path.join(tempfile.gettempdir(), ".antigravity_token")
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            return f.read().strip()
    return None

class BridgeCLI:
    def __init__(self, base_url=DEFAULT_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        token = _load_token()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        try:
            r = self.session.get(url, params=params, timeout=TIMEOUT)
            return r.json()
        except requests.ConnectionError:
            return {"error": f"Cannot connect to IDA Bridge at {self.base_url}. Is the plugin running?"}
        except Exception as e:
            return {"error": str(e)}

    def _post(self, path, data):
        url = f"{self.base_url}{path}"
        try:
            r = self.session.post(url, json=data, timeout=TIMEOUT)
            return r.json()
        except requests.ConnectionError:
            return {"error": f"Cannot connect to IDA Bridge at {self.base_url}. Is the plugin running?"}
        except Exception as e:
            return {"error": str(e)}

    def ping(self):
        return self._get("/api/ping")

    def info(self):
        return self._get("/api/info")

    def functions(self):
        return self._get("/api/functions")

    def pseudocode(self, ea):
        return self._get(f"/api/function/{ea}/pseudocode")

    def disasm(self, ea):
        return self._get(f"/api/function/{ea}/disasm")

    def xrefs_to(self, ea):
        return self._get(f"/api/function/{ea}/xrefs-to")

    def xrefs_from(self, ea):
        return self._get(f"/api/function/{ea}/xrefs-from")

    def strings(self, filter_regex=None):
        params = {}
        if filter_regex:
            params["filter"] = filter_regex
        return self._get("/api/strings", params)

    def imports(self):
        return self._get("/api/imports")

    def exports(self):
        return self._get("/api/exports")

    def segments(self):
        return self._get("/api/segments")

    def structs(self):
        return self._get("/api/structs")

    def struct_details(self, name):
        return self._get(f"/api/struct/{name}")

    def enums(self):
        return self._get("/api/enums")

    def enum_details(self, name):
        return self._get(f"/api/enum/{name}")

    def names(self, filter_str=None):
        params = {}
        if filter_str:
            params["filter"] = filter_str
        return self._get("/api/names", params)

    def search_func(self, name):
        return self._get(f"/api/search-func/{name}")

    def search_bytes(self, pattern):
        return self._get(f"/api/search-bytes/{pattern}")

    def read_bytes(self, ea, size):
        return self._get(f"/api/bytes/{ea}/{size}")

    def vtable(self, ea):
        return self._get(f"/api/vtable/{ea}")

    def func_details(self, ea):
        return self._get(f"/api/function/{ea}/details")

    def wait_analysis(self):
        return self._get("/api/wait-analysis")
    def call_graph(self, ea, depth=3):
        return self._get(f"/api/function/{ea}/call-graph", {"depth": depth})
    def basic_blocks(self, ea):
        return self._get(f"/api/function/{ea}/basic-blocks")
    def stack_vars(self, ea):
        return self._get(f"/api/function/{ea}/stack-vars")
    def func_args(self, ea):
        return self._get(f"/api/function/{ea}/args")
    def get_comment(self, ea):
        return self._get(f"/api/function/{ea}/comment")
    def search_text(self, text):
        return self._get(f"/api/search-text/{text}")
    def global_vars(self):
        return self._get("/api/global-vars")
    def bookmarks(self):
        return self._get("/api/bookmarks")
    def patches(self):
        return self._get("/api/patches")
    def gaps(self):
        return self._get("/api/gaps")

    # Write methods

    def ctree(self, ea): return self._get(f"/api/function/{ea}/ctree")
    def microcode(self, ea): return self._get(f"/api/function/{ea}/microcode")
    def types(self): return self._get("/api/types")
    def dbg_get_regs(self): return self._get("/api/dbg/regs")
    def dbg_get_stack(self): return self._get("/api/dbg/stack")
    def callers(self, ea): return self._get(f"/api/function/{ea}/callers")
    def callees(self, ea): return self._get(f"/api/function/{ea}/callees")
    def macro_analyze_context(self, ea): return self._get(f"/api/macro/analyze_context", {"ea": ea})
    def events(self): return self._get("/api/events")

    def rename_func(self, ea, name): return self._post(f"/api/function/{ea}/rename", {"name": name})
    def comment_func(self, ea, c): return self._post(f"/api/function/{ea}/comment", {"comment": c})
    def comment_addr(self, ea, c): return self._post(f"/api/address/{ea}/comment", {"comment": c})
    def rename_var(self, ea, old, new): return self._post(f"/api/function/{ea}/lvar-rename", {"old": old, "new": new})
    def create_struct(self, d): return self._post("/api/struct/create", {"definition": d})
    def add_struct_member(self, s, m, o, sz, t=None):
        d = {"struct": s, "member": m, "offset": o, "size": sz}
        if t: d["type"] = t
        return self._post("/api/struct/add-member", d)
    def create_enum(self, n): return self._post("/api/enum/create", {"name": n})
    def add_enum_member(self, e, m, v): return self._post("/api/enum/add-member", {"enum": e, "member": m, "value": v})
    def set_type(self, ea, t): return self._post(f"/api/function/{ea}/set-type", {"type": t})
    def set_color(self, ea, c): return self._post("/api/set-color", {"ea": ea, "color": c})
    def make_func(self, ea): return self._post("/api/make-func", {"ea": ea})
    def delete_func(self, ea): return self._post("/api/delete-func", {"ea": ea})
    def save(self): return self._post("/api/save", {})
    def decompile_batch(self, a): return self._post("/api/decompile-batch", {"addresses": a})
    def patch_bytes(self, ea, b): return self._post("/api/patch-bytes", {"ea": ea, "bytes": b})
    def make_code(self, ea): return self._post("/api/make-code", {"ea": ea})
    def make_data(self, ea, sz): return self._post("/api/make-data", {"ea": ea, "size": sz})
    def undefine(self, ea, sz): return self._post("/api/undefine", {"ea": ea, "size": sz})
    def set_name(self, ea, n): return self._post("/api/set-name", {"ea": ea, "name": n})
    def apply_struct(self, ea, s): return self._post("/api/apply-struct", {"ea": ea, "struct": s})
    def delete_struct(self, n): return self._post("/api/delete-struct", {"name": n})
    def delete_enum(self, n): return self._post("/api/delete-enum", {"name": n})
    def add_bookmark(self, ea, d): return self._post("/api/add-bookmark", {"ea": ea, "description": d})
    def delete_bookmark(self, s): return self._post("/api/delete-bookmark", {"slot": s})
    def import_header(self, p): return self._post("/api/import-header", {"path": p})
    def reanalyze(self, s, e): return self._post("/api/reanalyze", {"start": s, "end": e})
    def batch(self, mutations): return self._post("/api/batch", {"mutations": mutations})
    def exec_python(self, script): return self._post("/api/exec", {"script": script})


def format_output(data):
    """Pretty-print JSON result."""
    if isinstance(data, dict) and "error" in data and data["error"]:
        print(f"ERROR: {data['error']}", file=sys.stderr)
        if "traceback" in data:
            print(data["traceback"], file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="bridge_cli",
        description="Antigravity-IDA Bridge CLI — control IDA Pro from the terminal"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Bridge server URL (default: {DEFAULT_URL})")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # Read commands
    sub.add_parser("ping", help="Check if bridge is running")
    sub.add_parser("info", help="Get binary info")
    sub.add_parser("functions", help="List all functions")

    p = sub.add_parser("pseudocode", help="Get decompiled pseudocode")
    p.add_argument("ea", help="Function address (hex)")

    p = sub.add_parser("disasm", help="Get disassembly")
    p.add_argument("ea", help="Function address (hex)")

    p = sub.add_parser("xrefs-to", help="Get cross-references TO address")
    p.add_argument("ea", help="Address (hex)")

    p = sub.add_parser("xrefs-from", help="Get cross-references FROM function")
    p.add_argument("ea", help="Function address (hex)")

    p = sub.add_parser("strings", help="List strings")
    p.add_argument("--filter", default=None, help="Regex filter")

    sub.add_parser("imports", help="List imports")
    sub.add_parser("exports", help="List exports")
    sub.add_parser("segments", help="List segments")
    sub.add_parser("structs", help="List all structures")
    sub.add_parser("enums", help="List all enums")
    sub.add_parser("save", help="Save IDA database")
    sub.add_parser("wait-analysis", help="Wait for auto-analysis")
    sub.add_parser("global-vars", help="List global variables")
    sub.add_parser("bookmarks", help="List bookmarks")
    sub.add_parser("patches", help="List patched bytes")
    sub.add_parser("gaps", help="Find gaps between functions")

    for n, h, a in [
        ("struct-details", "Struct members with offsets", [("name",)]),
        ("enum-details", "Enum members with values", [("name",)]),
        ("search-func", "Find function by name", [("name",)]),
        ("vtable", "Read vtable", [("ea",)]),
        ("func-details", "Detailed function info", [("ea",)]),
        ("basic-blocks", "Basic blocks (CFG)", [("ea",)]),
        ("stack-vars", "Stack variables", [("ea",)]),
        ("func-args", "Function arguments", [("ea",)]),
        ("get-comment", "Read comments at address", [("ea",)]),
    ]:
        p = sub.add_parser(n, help=h)
        for arg in a: p.add_argument(*arg)

    p = sub.add_parser("names", help="Named items"); p.add_argument("--filter", default=None)
    p = sub.add_parser("search-bytes", help="Search byte pattern"); p.add_argument("pattern")
    p = sub.add_parser("search-text", help="Search in disassembly"); p.add_argument("text")
    p = sub.add_parser("bytes", help="Read raw bytes"); p.add_argument("ea"); p.add_argument("size", type=int)
    p = sub.add_parser("decompile-batch", help="Decompile multiple"); p.add_argument("addresses", nargs="+")
    p = sub.add_parser("call-graph", help="Call graph"); p.add_argument("ea"); p.add_argument("--depth", type=int, default=3)

    # Write commands
    p = sub.add_parser("rename-func", help="Rename function"); p.add_argument("ea"); p.add_argument("name")
    p = sub.add_parser("comment-func", help="Set function comment"); p.add_argument("ea"); p.add_argument("comment")
    p = sub.add_parser("comment", help="Inline comment"); p.add_argument("ea"); p.add_argument("comment_text")
    p = sub.add_parser("rename-var", help="Rename local var"); p.add_argument("ea"); p.add_argument("old"); p.add_argument("new")
    p = sub.add_parser("create-struct", help="Create C struct"); p.add_argument("definition")
    p = sub.add_parser("add-struct-member", help="Add struct member"); p.add_argument("struct_name"); p.add_argument("member_name"); p.add_argument("offset", type=lambda x: int(x,0)); p.add_argument("size", type=int)
    p = sub.add_parser("create-enum", help="Create enum"); p.add_argument("name")
    p = sub.add_parser("add-enum-member", help="Add enum member"); p.add_argument("enum_name"); p.add_argument("member_name"); p.add_argument("value", type=lambda x: int(x,0))
    p = sub.add_parser("set-type", help="Set function type"); p.add_argument("ea"); p.add_argument("type")
    p = sub.add_parser("set-color", help="Set color"); p.add_argument("ea"); p.add_argument("color")
    p = sub.add_parser("make-func", help="Create function"); p.add_argument("ea")
    p = sub.add_parser("delete-func", help="Delete function"); p.add_argument("ea")
    p = sub.add_parser("set-name", help="Set name at address"); p.add_argument("ea"); p.add_argument("name")
    p = sub.add_parser("patch-bytes", help="Patch bytes"); p.add_argument("ea"); p.add_argument("hex_bytes")
    p = sub.add_parser("make-code", help="Make code"); p.add_argument("ea")
    p = sub.add_parser("make-data", help="Make data"); p.add_argument("ea"); p.add_argument("size", type=int)
    p = sub.add_parser("undefine", help="Undefine range"); p.add_argument("ea"); p.add_argument("size", type=int)
    p = sub.add_parser("apply-struct", help="Apply struct at addr"); p.add_argument("ea"); p.add_argument("struct_name")
    p = sub.add_parser("delete-struct", help="Delete struct"); p.add_argument("name")
    p = sub.add_parser("delete-enum", help="Delete enum"); p.add_argument("name")
    p = sub.add_parser("add-bookmark", help="Add bookmark"); p.add_argument("ea"); p.add_argument("description")
    p = sub.add_parser("delete-bookmark", help="Delete bookmark"); p.add_argument("slot", type=int)
    p = sub.add_parser("import-header", help="Import C header"); p.add_argument("path")
    p = sub.add_parser("reanalyze", help="Reanalyze range"); p.add_argument("start"); p.add_argument("end")
    p = sub.add_parser("exec", help="Execute python script"); p.add_argument("file")
    p = sub.add_parser("batch", help="Batch mutations"); p.add_argument("file")


    p = sub.add_parser("ctree", help="Get AST"); p.add_argument("ea")
    p = sub.add_parser("microcode", help="Get microcode"); p.add_argument("ea")
    p = sub.add_parser("types", help="List types")
    p = sub.add_parser("debugger", help="Get debugger regs/stack"); p.add_argument("cmd", choices=["regs", "stack"])
    p = sub.add_parser("callers", help="Get function callers"); p.add_argument("ea")
    p = sub.add_parser("callees", help="Get function callees"); p.add_argument("ea")
    p = sub.add_parser("analyze_context", help="Macro analyze context"); p.add_argument("ea")
    p = sub.add_parser("events", help="Stream SSE events")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    cli = BridgeCLI(args.url)
    c = args.command
    # Dispatch
    if c == "ping": r = cli.ping()
    elif c == "info": r = cli.info()
    elif c == "functions": r = cli.functions()
    elif c == "pseudocode": r = cli.pseudocode(args.ea)
    elif c == "disasm": r = cli.disasm(args.ea)
    elif c == "xrefs-to": r = cli.xrefs_to(args.ea)
    elif c == "xrefs-from": r = cli.xrefs_from(args.ea)
    elif c == "strings": r = cli.strings(args.filter)
    elif c == "imports": r = cli.imports()
    elif c == "exports": r = cli.exports()
    elif c == "segments": r = cli.segments()
    elif c == "structs": r = cli.structs()
    elif c == "struct-details": r = cli.struct_details(args.name)
    elif c == "enums": r = cli.enums()
    elif c == "enum-details": r = cli.enum_details(args.name)
    elif c == "names": r = cli.names(args.filter)
    elif c == "search-func": r = cli.search_func(args.name)
    elif c == "search-bytes": r = cli.search_bytes(args.pattern)
    elif c == "search-text": r = cli.search_text(args.text)
    elif c == "bytes": r = cli.read_bytes(args.ea, args.size)
    elif c == "vtable": r = cli.vtable(args.ea)
    elif c == "func-details": r = cli.func_details(args.ea)
    elif c == "call-graph": r = cli.call_graph(args.ea, args.depth)
    elif c == "basic-blocks": r = cli.basic_blocks(args.ea)
    elif c == "stack-vars": r = cli.stack_vars(args.ea)
    elif c == "func-args": r = cli.func_args(args.ea)
    elif c == "get-comment": r = cli.get_comment(args.ea)
    elif c == "global-vars": r = cli.global_vars()
    elif c == "bookmarks": r = cli.bookmarks()
    elif c == "patches": r = cli.patches()
    elif c == "gaps": r = cli.gaps()
    elif c == "decompile-batch": r = cli.decompile_batch(args.addresses)
    elif c == "wait-analysis": r = cli.wait_analysis()
    elif c == "save": r = cli.save()
    elif c == "rename-func": r = cli.rename_func(args.ea, args.name)
    elif c == "comment-func": r = cli.comment_func(args.ea, args.comment)
    elif c == "comment": r = cli.comment_addr(args.ea, args.comment_text)
    elif c == "rename-var": r = cli.rename_var(args.ea, args.old, args.new)
    elif c == "create-struct": r = cli.create_struct(args.definition)
    elif c == "add-struct-member": r = cli.add_struct_member(args.struct_name, args.member_name, args.offset, args.size)
    elif c == "create-enum": r = cli.create_enum(args.name)
    elif c == "add-enum-member": r = cli.add_enum_member(args.enum_name, args.member_name, args.value)
    elif c == "set-type": r = cli.set_type(args.ea, args.type)
    elif c == "set-color": r = cli.set_color(args.ea, args.color)
    elif c == "make-func": r = cli.make_func(args.ea)
    elif c == "delete-func": r = cli.delete_func(args.ea)
    elif c == "set-name": r = cli.set_name(args.ea, args.name)
    elif c == "patch-bytes": r = cli.patch_bytes(args.ea, args.hex_bytes)
    elif c == "make-code": r = cli.make_code(args.ea)
    elif c == "make-data": r = cli.make_data(args.ea, args.size)
    elif c == "undefine": r = cli.undefine(args.ea, args.size)
    elif c == "apply-struct": r = cli.apply_struct(args.ea, args.struct_name)
    elif c == "delete-struct": r = cli.delete_struct(args.name)
    elif c == "delete-enum": r = cli.delete_enum(args.name)
    elif c == "add-bookmark": r = cli.add_bookmark(args.ea, args.description)
    elif c == "delete-bookmark": r = cli.delete_bookmark(args.slot)
    elif c == "import-header": r = cli.import_header(args.path)
    elif c == "reanalyze": r = cli.reanalyze(args.start, args.end)
    elif c == "exec":
        with open(args.file, "r", encoding="utf-8") as f:
            script_code = f.read()
        r = cli.exec_python(script_code)
    elif c == "batch":
        with open(args.file, "r", encoding="utf-8") as f:
            mutations = json.load(f)
        if isinstance(mutations, dict): mutations = mutations.get("mutations", [])
        r = cli.batch(mutations)

    elif c == "ctree": r = cli.ctree(args.ea)
    elif c == "microcode": r = cli.microcode(args.ea)
    elif c == "types": r = cli.types()
    elif c == "debugger":
        r = cli.dbg_get_regs() if args.cmd == "regs" else cli.dbg_get_stack()
    elif c == "callers": r = cli.callers(args.ea)
    elif c == "callees": r = cli.callees(args.ea)
    elif c == "analyze_context": r = cli.macro_analyze_context(args.ea)
    elif c == "events": r = cli.events()

    else:
        parser.print_help()
        return 1
    return format_output(r)

if __name__ == "__main__":
    sys.exit(main())
