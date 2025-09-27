import pytest

from connectors.deepseek import AuthenticationError, DeepSeekConnector


class DummyHTTPClient:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response or {"choices": [{"message": {"role": "assistant", "content": "hi"}}]}
        self.error = error
        self.calls = []

    def post(self, url, json, headers):  # noqa: D401 - testing stub
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.error:
            raise self.error
        return self.response


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)


def test_authentication_from_environment(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    connector = DeepSeekConnector(
        {"credentials": {"api_key_env": "DEEPSEEK_API_KEY"}},
        http_client=DummyHTTPClient(),
    )
    response = connector.send_task({"prompt": "Hello"})
    normalized = connector.normalize_response(response)
    assert normalized["content"] == "hi"


def test_missing_credentials_raises():
    with pytest.raises(AuthenticationError):
        DeepSeekConnector({"credentials": {}}, http_client=DummyHTTPClient())


def test_failure_recovery_returns_retryable(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    client = DummyHTTPClient(error=TimeoutError("timeout"))
    connector = DeepSeekConnector(
        {"credentials": {"api_key_env": "DEEPSEEK_API_KEY"}},
        http_client=client,
    )
    response = connector.send_task({"prompt": "Hi"})
    assert response["error"] == "timeout"
    assert response["retryable"] is True
