#!/usr/bin/env python3
"""Command line entry-point for the MCP host runtime."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml

from mcp_host import HostRuntime


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def instantiate_connector(entry: Dict[str, Any]):
    module = importlib.import_module(entry["module"])
    cls = getattr(module, entry["class"])
    if hasattr(cls, "from_config"):
        return cls.from_config(entry)
    return cls(entry)


def register_connectors(runtime: HostRuntime, connectors: Iterable[Dict[str, Any]]) -> None:
    for entry in connectors:
        connector = instantiate_connector(entry)
        runtime.register_connector(connector, routes=entry.get("routes"))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the MCP host runtime")
    parser.add_argument("--config", type=Path, default=Path("config/settings.yaml"))
    parser.add_argument("--task", type=Path, help="JSON file describing a single task")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enter an interactive loop for processing JSON tasks",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    config = load_config(args.config)
    runtime = HostRuntime(context=config.get("context"))
    register_connectors(runtime, config.get("connectors", []))

    if args.task:
        task_payload = json.loads(args.task.read_text(encoding="utf-8"))
        result = runtime.route_task(task_payload)
        print(json.dumps(result, indent=2))
        return 0

    if not args.interactive:
        parser.error("Either --task or --interactive must be specified")

    print("MCP host ready. Enter JSON payloads (Ctrl-D to exit).", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        task_payload = json.loads(line)
        result = runtime.route_task(task_payload)
        print(json.dumps(result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
