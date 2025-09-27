import json
from pathlib import Path

import pytest

from mcp_host.runtime import HostRuntime


class StubConnector:
    def __init__(self) -> None:
        self.requests = []

    def send_task(self, request):
        self.requests.append(request)
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}

    @staticmethod
    def normalize_response(response):
        message = response["choices"][0]["message"]
        return {"role": message["role"], "content": message["content"]}


@pytest.fixture()
def runtime(tmp_path: Path) -> HostRuntime:
    config = {
        "connectors": {"deepseek": {"class": "connectors.deepseek.DeepSeekConnector"}},
        "routing": {
            "default": "deepseek",
            "rules": [{"match": "generate", "connector": "deepseek"}],
        },
    }
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    host_runtime = HostRuntime(config_path)
    stub = StubConnector()
    host_runtime.register_connector("deepseek", stub)
    host_runtime.stub = stub
    return host_runtime


def test_route_task_uses_matching_rule(runtime: HostRuntime):
    response = runtime.route_task({"intent": "generate summary", "prompt": "Hello"})
    assert response == {"role": "assistant", "content": "ok"}
    assert runtime.stub.requests[0]["prompt"] == "Hello"


def test_route_task_unknown_connector(runtime: HostRuntime):
    with pytest.raises(Exception):
        runtime.route_task({"connector": "missing", "intent": "generate"})
