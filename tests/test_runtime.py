import pytest

from mcp_host import ConnectorError, HostRuntime


class DummyConnector:
    name = "dummy"

    def __init__(self, *, supported_tasks=None, response=None):
        self.supported_tasks = supported_tasks or {"default"}
        self.response = response or {"status": "ok"}
        self.calls = []

    def supports(self, task):
        return task.get("task") in self.supported_tasks

    def handle(self, task, context):
        self.calls.append({"task": task, "context": context.copy()})
        return self.response


def test_route_with_explicit_target():
    runtime = HostRuntime()
    connector = DummyConnector()
    runtime.register_connector(connector)

    result = runtime.route_task({"task": "ignored", "target": "dummy"})

    assert result["connector"] == "dummy"
    assert connector.calls


def test_route_with_registered_routes():
    runtime = HostRuntime()
    connector = DummyConnector(supported_tasks={"other"})
    runtime.register_connector(connector, routes=["preferred"])

    result = runtime.route_task({"task": "preferred"})

    assert result["connector"] == "dummy"
    assert runtime.context["last_result"] == connector.response


def test_route_without_connector_raises():
    runtime = HostRuntime()

    with pytest.raises(ConnectorError):
        runtime.route_task({"task": "unknown"})
