import sys
from unittest.mock import MagicMock
import py_compile

def run_tests():
    sys.modules['requests'] = MagicMock()
    sys.modules['requests.adapters'] = MagicMock()
    sys.modules['requests.exceptions'] = MagicMock()
    sys.modules['urllib3'] = MagicMock()
    sys.modules['urllib3.util.retry'] = MagicMock()

    # We want to just make sure things compile mostly because tests are not here.
    try:
        py_compile.compile('agent.py', doraise=True)
        py_compile.compile('cli.py', doraise=True)
        py_compile.compile('mcp_server.py', doraise=True)
        py_compile.compile('server.py', doraise=True)
        py_compile.compile('swarm_worker.py', doraise=True)
        py_compile.compile('core/__init__.py', doraise=True)
        py_compile.compile('core/client.py', doraise=True)
        py_compile.compile('core/schema.py', doraise=True)
        py_compile.compile('ida_plugin/antigravity_server.py', doraise=True)
        py_compile.compile('integrations/ide_extension.py', doraise=True)
        print("All files compiled successfully.")
    except Exception as e:
        print(f"Compilation error: {e}")

if __name__ == '__main__':
    run_tests()
