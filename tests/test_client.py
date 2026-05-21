from unittest.mock import patch

# Robustly mock requests and urllib3 before importing project modules
import requests

class MockResponse:
    def __init__(self, json_data, status_code, text=""):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text

    def json(self):
        if not self.text:
            raise requests.exceptions.JSONDecodeError("Expecting value", "", 0)
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error")

@patch('requests.Session')
def test_bridge_client_ping(mock_session):
    mock_instance = mock_session.return_value
    mock_response = MockResponse({"success": True, "version": "1.0"}, 200, text='{"success": true, "version": "1.0"}')
    mock_instance.request.return_value = mock_response

    from core.client import BridgeClient
    client = BridgeClient()
    result = client.ping()

    assert result == {"success": True, "version": "1.0"}
