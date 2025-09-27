"""CLI entry point for running the MCP host runtime."""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from mcp_host.runtime import HostRuntime


def _build_http_client() -> object | None:
    try:
        import requests
    except ImportError:  # pragma: no cover - requests is optional for tests
        return None

    class RequestsHTTPClient:
        def post(self, url: str, json: dict, headers: dict) -> dict:
            response = requests.post(url, json=json, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()

    return RequestsHTTPClient()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MCP host runtime.")
    parser.add_argument(
        "--config",
        default=Path("config/settings.yaml"),
        help="Path to the runtime configuration file.",
    )
    args = parser.parse_args()

    runtime = HostRuntime(args.config)
    http_client = _build_http_client()

    connectors_cfg = runtime.config.get("connectors", {})
    deepseek_cfg = connectors_cfg.get("deepseek", {})

    module_name, class_name = deepseek_cfg.get("class", "connectors.deepseek.DeepSeekConnector").rsplit(".", 1)
    module = importlib.import_module(module_name)
    connector_cls = getattr(module, class_name)
    connector = connector_cls(deepseek_cfg, http_client=http_client)
    runtime.register_connector("deepseek", connector)

    runtime.listen()


if __name__ == "__main__":
    main()
