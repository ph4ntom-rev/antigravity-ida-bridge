import pytest
import json
import os
import sys
from unittest.mock import MagicMock, patch, mock_open

# Mock requests before importing bridge_cli to handle environment limitations
mock_requests = MagicMock()
class MockConnectionError(Exception):
    pass
mock_requests.ConnectionError = MockConnectionError
sys.modules["requests"] = mock_requests

from bridge_cli import BridgeCLI, format_output, _load_token

# Test format_output (Pure Function)
def test_format_output_dict():
    data = {"result": "ok"}
    result = format_output(data)
    assert json.loads(result) == data

def test_format_output_list():
    data = [{"func": "main"}, {"func": "init"}]
    result = format_output(data)
    assert json.loads(result) == data

def test_format_output_error_dict():
    data = {"error": "something went wrong"}
    result = format_output(data)
    assert json.loads(result) == data

# Test _load_token
@patch("os.path.exists")
@patch("tempfile.gettempdir")
def test_load_token_exists(mock_gettempdir, mock_exists):
    mock_gettempdir.return_value = "/tmp"
    mock_exists.return_value = True
    with patch("builtins.open", mock_open(read_data="test-token")):
        token = _load_token()
        assert token == "test-token"
    mock_exists.assert_called_once_with("/tmp/.antigravity_token")

@patch("os.path.exists")
@patch("tempfile.gettempdir")
def test_load_token_not_exists(mock_gettempdir, mock_exists):
    mock_gettempdir.return_value = "/tmp"
    mock_exists.return_value = False
    token = _load_token()
    assert token is None

# Test BridgeCLI
@pytest.fixture
def mock_session():
    # Since we mocked requests in sys.modules, requests.Session will return a MagicMock instance
    import requests
    session_instance = requests.Session.return_value
    session_instance.headers = {}
    session_instance.get = MagicMock()
    session_instance.post = MagicMock()
    return session_instance

def test_bridge_cli_init_with_token(mock_session):
    with patch("bridge_cli._load_token", return_value="my-token"):
        cli = BridgeCLI("http://localhost:1337")
        assert cli.base_url == "http://localhost:1337"
        assert mock_session.headers["Authorization"] == "Bearer my-token"

def test_bridge_cli_get_success(mock_session):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}
    mock_session.get.return_value = mock_response

    cli = BridgeCLI("http://localhost:1337")
    result = cli._get("/api/ping")

    assert result == {"status": "ok"}
    mock_session.get.assert_called_once_with("http://localhost:1337/api/ping", params=None, timeout=30)

def test_bridge_cli_get_connection_error(mock_session):
    import requests
    mock_session.get.side_effect = requests.ConnectionError()

    cli = BridgeCLI("http://localhost:1337")
    result = cli._get("/api/ping")

    assert isinstance(result, dict)
    assert "error" in result
    assert "Cannot connect to IDA Bridge" in result["error"]

def test_bridge_cli_post_success(mock_session):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "renamed"}
    mock_session.post.return_value = mock_response

    cli = BridgeCLI("http://localhost:1337")
    result = cli._post("/api/rename", {"name": "new_name"})

    assert result == {"status": "renamed"}
    mock_session.post.assert_called_once_with("http://localhost:1337/api/rename", json={"name": "new_name"}, timeout=30)

def test_bridge_cli_public_methods(mock_session):
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_session.get.return_value = mock_response
    mock_session.post.return_value = mock_response

    cli = BridgeCLI("http://localhost:1337")

    cli.ping()
    mock_session.get.assert_any_call("http://localhost:1337/api/ping", params=None, timeout=30)

    cli.info()
    mock_session.get.assert_any_call("http://localhost:1337/api/info", params=None, timeout=30)

    cli.rename_func("0x401000", "my_func")
    mock_session.post.assert_any_call("http://localhost:1337/api/function/0x401000/rename", json={"name": "my_func"}, timeout=30)
