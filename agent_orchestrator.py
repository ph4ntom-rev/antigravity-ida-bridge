"""
DEPRECATED — Use agent.py instead.

This file is kept for backward compatibility.
It simply launches agent.py with --backend gemini.
"""

import warnings
warnings.warn(
    "agent_orchestrator.py is deprecated. Use: python agent.py --backend gemini",
    DeprecationWarning,
    stacklevel=2,
)

# Preserve original behavior
import subprocess
import sys

sys.exit(subprocess.call([sys.executable, "agent.py", "--backend", "gemini"] + sys.argv[1:]))
