"""Runtime management for MCP host applications."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError:  # pragma: no cover - fallback for environments without PyYAML
    yaml = None


class UnknownConnectorError(RuntimeError):
    """Raised when a requested connector cannot be resolved."""


class HostRuntime:
    """Manage connectors, global context, and task routing for MCP hosts."""

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_config(self.config_path)
        self.context: Dict[str, Any] = {}
        self.connectors: Dict[str, Any] = {}

    @staticmethod
    def _load_config(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            raw = handle.read()

        if yaml:
            data = yaml.safe_load(raw) or {}
        else:  # Fallback to JSON parsing when PyYAML is unavailable.
            data = json.loads(raw or "{}")
        return data

    def register_connector(self, name: str, connector: Any) -> None:
        self.connectors[name] = connector

    def _resolve_connector_name(self, request: Dict[str, Any]) -> str:
        if connector_name := request.get("connector"):
            if connector_name in self.connectors:
                return connector_name
            raise UnknownConnectorError(f"Connector '{connector_name}' is not registered.")

        routing = self.config.get("routing", {})
        rules = routing.get("rules", [])
        intent = request.get("intent") or request.get("task") or ""

        for rule in rules:
            match_value = rule.get("match")
            if match_value and match_value in intent:
                connector_name = rule["connector"]
                if connector_name in self.connectors:
                    return connector_name

        default_connector = routing.get("default")
        if default_connector and default_connector in self.connectors:
            return default_connector

        raise UnknownConnectorError("Unable to resolve connector for request.")

    def route_task(self, request: Dict[str, Any]) -> Dict[str, Any]:
        connector_name = self._resolve_connector_name(request)
        connector = self.connectors[connector_name]
        response = connector.send_task(request)
        normalized = connector.normalize_response(response)
        return normalized

    def listen(self, stream: Optional[Any] = None) -> None:
        """Listen for JSON-encoded MCP requests on the provided stream."""

        stream = stream or sys.stdin
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                error = {"error": f"Invalid request payload: {exc}"}
                print(json.dumps(error), flush=True)
                continue

            try:
                response = self.route_task(request)
            except Exception as exc:  # noqa: BLE001 - propagate runtime errors to the client
                response = {"error": str(exc)}
            print(json.dumps(response), flush=True)


__all__ = ["HostRuntime", "UnknownConnectorError"]
