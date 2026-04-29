import ast
import re

with open("ida_plugin/antigravity_server.py", "r") as f:
    source = f.read()

tree = ast.parse(source)

routes = []

class ExtractRoutes(ast.NodeVisitor):
    def visit_ClassDef(self, node):
        if node.name == "BridgeHandler":
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name in ("do_GET", "do_POST"):
                    self.extract_routes(method)
        self.generic_visit(node)

    def extract_routes(self, method):
        target_if = None
        for n in ast.walk(method):
            if isinstance(n, ast.If):
                test = n.test
                is_path_cmp = False
                if isinstance(test, ast.Compare) and isinstance(test.ops[0], ast.Eq):
                    if isinstance(test.left, ast.Name) and test.left.id == "path":
                        is_path_cmp = True
                if isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute):
                    if getattr(test.func.value, "id", "") == "path" and test.func.attr == "startswith":
                        is_path_cmp = True

                if is_path_cmp:
                    curr = n
                    elifs = 0
                    while curr.orelse and len(curr.orelse) == 1 and isinstance(curr.orelse[0], ast.If):
                        elifs += 1
                        curr = curr.orelse[0]
                    if elifs > 5:
                        target_if = n
                        break

        if not target_if: return

        curr = target_if
        idx = 0
        while curr:
            test = curr.test
            pattern = None
            if isinstance(test, ast.Compare) and isinstance(test.ops[0], ast.Eq):
                if isinstance(test.left, ast.Name) and test.left.id == "path":
                    if isinstance(test.comparators[0], ast.Constant):
                        pattern = test.comparators[0].value
            if isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute):
                if getattr(test.func.value, "id", "") == "path" and test.func.attr == "startswith":
                    if isinstance(test.args[0], ast.Constant):
                        pattern = test.args[0].value + ".*"

            if pattern:
                func_name = f"route_{method.name.lower()}_{idx}"
                decorator = "@get_route" if method.name == "do_GET" else "@post_route"
                args = "self, match, params" if method.name == "do_GET" else "self, match, data"

                class Replacer(ast.NodeTransformer):
                    def visit_Call(self, n):
                        if isinstance(n.func, ast.Attribute) and getattr(n.func.value, "id", "") == "path" and n.func.attr == "split":
                            n.func.value.id = "match.string"
                        self.generic_visit(n)
                        return n

                    def visit_Name(self, n):
                        if isinstance(n.ctx, ast.Load) and n.id == "path":
                            n.id = "match.string"
                        return n

                import copy
                body_ast = ast.Module(body=copy.deepcopy(curr.body), type_ignores=[])
                body_ast = Replacer().visit(body_ast)

                body_code = ast.unparse(body_ast)
                body_code = "\n".join("    " + line for line in body_code.split("\n"))

                route_def = f"{decorator}(r'{pattern}')\ndef {func_name}({args}):\n{body_code}\n"
                routes.append(route_def)
                idx += 1

            if curr.orelse and len(curr.orelse) == 1 and isinstance(curr.orelse[0], ast.If):
                curr = curr.orelse[0]
            else:
                break

ExtractRoutes().visit(tree)

routes_text = "\n".join(routes)

router_prelude = """
# --- Micro Router ---
import queue
sse_queue = queue.Queue()

GET_ROUTES = []
POST_ROUTES = []

def get_route(pattern):
    def decorator(func):
        GET_ROUTES.append((re.compile('^' + pattern + '$'), func))
        return func
    return decorator

def post_route(pattern):
    def decorator(func):
        POST_ROUTES.append((re.compile('^' + pattern + '$'), func))
        return func
    return decorator

class AntigravityUIHooks(ida_kernwin.UI_Hooks):
    def screen_ea_changed(self, ea, prev_ea):
        sse_queue.put({"event": "cursor_changed", "ea": hex(ea), "prev_ea": hex(prev_ea)})
        return 0

try:
    import ida_dbg
    class AntigravityDbgHooks(ida_dbg.DbgHooks):
        def dbg_bpt(self, tid, ea):
            sse_queue.put({"event": "breakpoint_hit", "tid": tid, "ea": hex(ea)})
            return 0
    dbg_hooks = AntigravityDbgHooks()
except Exception:
    dbg_hooks = None

ui_hooks = AntigravityUIHooks()
"""

analyze_context_handler = """
def get_analyze_context(ea):
    def _inner():
        ctx = {}
        try: ctx["pseudocode"] = get_pseudocode(ea)().get("pseudocode")
        except Exception: ctx["pseudocode"] = None
        try: ctx["lvars"] = get_lvar_map(ea)().get("lvars", {})
        except Exception: ctx["lvars"] = {}
        try: ctx["callers"] = get_callers(ea)().get("callers", [])
        except Exception: ctx["callers"] = []
        try: ctx["callees"] = get_callees(ea)().get("callees", [])
        except Exception: ctx["callees"] = []
        try: ctx["strings_used"] = get_strings_used(ea)().get("strings", [])
        except Exception: ctx["strings_used"] = []
        try: ctx["xrefs_to"] = get_xrefs_to(ea)().get("xrefs", [])
        except Exception: ctx["xrefs_to"] = []
        try: ctx["basic_blocks"] = get_basic_blocks(ea)().get("blocks", [])
        except Exception: ctx["basic_blocks"] = []
        return ctx
    return safe_read(_inner)

@get_route(r'/api/macro/analyze_context')
def route_macro_analyze_context(self, match, params):
    ea = parse_ea(params.get("ea", ["0"])[0])
    self.send_json(get_analyze_context(ea)())
"""

events_handler = """
@get_route(r'/api/events')
def route_events(self, match, params):
    self.send_response(200)
    self.send_header('Content-Type', 'text/event-stream')
    self.send_header('Cache-Control', 'no-cache')
    self.send_header('Connection', 'keep-alive')
    self.send_header('Access-Control-Allow-Origin', '*')
    self.end_headers()

    while True:
        try:
            event = sse_queue.get(timeout=1.0)
            self.wfile.write(f"data: {json.dumps(event)}\\n\\n".encode('utf-8'))
            self.wfile.flush()
        except queue.Empty:
            self.wfile.write(b": ping\\n\\n")
            self.wfile.flush()
        except Exception:
            break
"""

do_get_new = """
    def do_GET(self):
        if not self._check_auth(): return
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)
        for pattern, handler in GET_ROUTES:
            m = pattern.match(path)
            if m:
                try: handler(self, m, params)
                except Exception as e: self.send_error_json(str(e))
                return
        self.send_error_json("Unknown GET endpoint: " + path, 404)
"""

do_post_new = """
    def do_POST(self):
        if not self._check_auth(): return
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        cl = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(cl).decode("utf-8") if cl > 0 else "{}"
        try: data = json.loads(body) if body else {}
        except json.JSONDecodeError: return self.send_error_json("Invalid JSON body")
        for pattern, handler in POST_ROUTES:
            m = pattern.match(path)
            if m:
                try: handler(self, m, data)
                except Exception as e: self.send_error_json(str(e))
                return
        self.send_error_json("Unknown POST endpoint: " + path, 404)
"""

class MethodFinder(ast.NodeVisitor):
    def __init__(self):
        self.do_get_bounds = None
        self.do_post_bounds = None

    def visit_ClassDef(self, node):
        if node.name == "BridgeHandler":
            for n in node.body:
                if isinstance(n, ast.FunctionDef):
                    if n.name == "do_GET":
                        self.do_get_bounds = (n.lineno, n.end_lineno)
                    elif n.name == "do_POST":
                        self.do_post_bounds = (n.lineno, n.end_lineno)
        self.generic_visit(node)

finder = MethodFinder()
finder.visit(tree)

lines = source.split("\n")
if finder.do_post_bounds:
    del lines[finder.do_post_bounds[0]-1 : finder.do_post_bounds[1]]
    lines.insert(finder.do_post_bounds[0]-1, do_post_new.strip('\n'))

if finder.do_get_bounds:
    del lines[finder.do_get_bounds[0]-1 : finder.do_get_bounds[1]]
    lines.insert(finder.do_get_bounds[0]-1, do_get_new.strip('\n'))

source = "\n".join(lines)

match = re.search(r"^class BridgeHandler\(BaseHTTPRequestHandler\):", source, re.M)
if match:
    source = source[:match.start()] + analyze_context_handler + "\n" + router_prelude + "\n" + routes_text + "\n" + events_handler + "\n\n" + source[match.start():]

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
source = re.sub(r"(def init\(self\):.*?_server_thread\.start\(\))", r"\1\n" + init_hooks, source, flags=re.S)
source = re.sub(r"(def term\(self\):.*?_server_thread\.join\(\))", r"\1\n" + term_hooks, source, flags=re.S)

old_exec = "exec(script_code, globals(), local_vars)"
new_exec = """
            if hasattr(ida_auto, "auto_mark_range"):
                try: ida_auto.auto_mark_range(0, ida_idaapi.BADADDR, ida_auto.AU_USED)
                except Exception: pass
            exec(script_code, globals(), local_vars)
"""
source = source.replace(old_exec, new_exec.strip())

with open("ida_plugin/antigravity_server.py", "w") as f:
    f.write(source)
