"""
Antigravity IDA Bridge — Core HTTP Client
==========================================
Reusable HTTP client for communicating with the IDA Bridge REST API.
Used by all backends, integrations, and CLI tools.
"""

import os
import tempfile
import requests


class BridgeClient:
    """Thread-safe HTTP client for the Antigravity IDA Bridge."""

    def __init__(self, url: str = None):
        self.base_url = url or os.environ.get("IDA_BRIDGE_URL", "http://127.0.0.1:13370")
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self._load_token()

    def _load_token(self):
        """Load ephemeral Bearer token from temp directory."""
        token_path = os.path.join(tempfile.gettempdir(), ".antigravity_token")
        if os.path.exists(token_path):
            with open(token_path, "r") as f:
                token = f.read().strip()
                if token:
                    self.session.headers["Authorization"] = f"Bearer {token}"

    # ── Core HTTP Methods ────────────────────────────────────────────────

    def get(self, path: str, **params) -> dict:
        """GET request to bridge. Returns parsed JSON."""
        try:
            r = self.session.get(f"{self.base_url}{path}", params=params, timeout=30)
            return r.json()
        except requests.ConnectionError:
            return {"error": f"IDA Bridge offline at {self.base_url}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    def post(self, path: str, data: dict = None) -> dict:
        """POST request to bridge. Returns parsed JSON."""
        try:
            r = self.session.post(f"{self.base_url}{path}", json=data or {}, timeout=30)
            return r.json()
        except requests.ConnectionError:
            return {"error": f"IDA Bridge offline at {self.base_url}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    # ── Convenience Methods ──────────────────────────────────────────────

    def ping(self) -> dict:
        """Check bridge connectivity."""
        return self.get("/api/ping")

    def info(self) -> dict:
        """Get binary metadata."""
        return self.get("/api/info")

    def is_online(self) -> bool:
        """Quick connectivity check."""
        result = self.ping()
        return "error" not in result

    def decompile(self, ea: str) -> dict:
        """Decompile function at address."""
        return self.get(f"/api/function/{ea}/pseudocode")

    def exec_python(self, script: str) -> dict:
        """Execute IDAPython script."""
        return self.post("/api/exec", {"script": script})

    def call_api(self, method: str, path: str, body: dict = None) -> dict:
        """Generic API call by method string."""
        if method.upper() == "GET":
            return self.get(path)
        else:
            return self.post(path, body)
