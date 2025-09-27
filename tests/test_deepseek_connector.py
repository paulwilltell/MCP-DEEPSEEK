import json

import pytest

from connectors.deepseek import AuthenticationError, DeepSeekConnector


class StubHTTPHandler:
    def __init__(self):
        self.requests = []

    def post(self, *, url, data, headers):
        self.requests.append({"url": url, "data": data, "headers": headers})
        return json.dumps({"status": "queued"})


def test_from_config_uses_environment(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")

    connector = DeepSeekConnector.from_config(
        {
            "api_key_env": "DEEPSEEK_API_KEY",
            "routes": ["generate_backend"],
            "base_url": "https://example.test",
            "model": "custom-model",
        }
    )

    assert connector.supports({"task": "generate_backend"})
    assert not connector.supports({"task": "unknown"})


def test_handle_builds_expected_payload(monkeypatch):
    handler = StubHTTPHandler()
    connector = DeepSeekConnector.from_config({"api_key": "abc", "routes": ["generate_backend"]})
    connector._http_handler = handler

    task = {
        "task": "generate_backend",
        "language": "python",
        "framework": "fastapi",
        "requirements": ["CRUD"],
    }

    result = connector.handle(task, context={"last_result": {"status": "ok"}})

    assert result == {"status": "queued"}
    assert handler.requests
    request = handler.requests[0]
    assert request["headers"]["Authorization"] == "Bearer abc"
    payload = json.loads(request["data"].decode("utf-8"))
    assert payload["model"] == connector.settings.model
    assert payload["input"]["language"] == "python"
    assert payload["input"]["framework"] == "fastapi"
    assert payload["input"]["requirements"] == ["CRUD"]


def test_handle_without_api_key_raises():
    connector = DeepSeekConnector.from_config({"routes": ["generate_backend"]})

    with pytest.raises(AuthenticationError):
        connector.handle({"task": "generate_backend"}, context={})
