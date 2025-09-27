"""Connector implementation for interacting with the DeepSeek API."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from mcp_host.runtime import Connector, ConnectorError


class AuthenticationError(ConnectorError):
    """Raised when authentication details are missing or invalid."""


@dataclass
class DeepSeekSettings:
    """Configuration for the :class:`DeepSeekConnector`."""

    api_key: str
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    default_tasks: Iterable[str] = ("generate_backend", "generate_frontend", "draft_content")
    timeout: int = 30


class DeepSeekConnector(Connector):
    """Translate MCP tasks into DeepSeek API calls."""

    name = "deepseek"

    def __init__(self, settings: DeepSeekSettings, *, http_handler=None) -> None:
        self.settings = settings
        self._http_handler = http_handler or _DefaultHTTPHandler(settings.timeout)
        self._supported_tasks = set(settings.default_tasks)

    # ------------------------------------------------------------------
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "DeepSeekConnector":
        """Create a connector from a configuration dictionary."""

        api_key = _resolve_api_key(config)
        base_url = config.get("base_url", DeepSeekSettings.base_url)
        model = config.get("model", DeepSeekSettings.model)
        tasks = config.get("routes", DeepSeekSettings.default_tasks)
        timeout = int(config.get("timeout", DeepSeekSettings.timeout))

        settings = DeepSeekSettings(
            api_key=api_key,
            base_url=base_url,
            model=model,
            default_tasks=tasks,
            timeout=timeout,
        )
        return cls(settings)

    # ------------------------------------------------------------------
    def supports(self, task: Dict[str, Any]) -> bool:
        task_name = task.get("task")
        return bool(task_name and task_name in self._supported_tasks)

    # ------------------------------------------------------------------
    def handle(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.settings.api_key:
            raise AuthenticationError("DeepSeek API key is not configured")

        payload = self._build_payload(task, context)
        response = self._http_handler.post(
            url=f"{self.settings.base_url.rstrip('/')}/tasks",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
        )
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ConnectorError("Invalid JSON response from DeepSeek") from exc
        return parsed

    # ------------------------------------------------------------------
    def _build_payload(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = task.get("prompt")
        if prompt is None:
            prompt = self._format_prompt(task, context)

        return {
            "model": self.settings.model,
            "input": {
                "prompt": prompt,
                "language": task.get("language"),
                "framework": task.get("framework"),
                "requirements": task.get("requirements", []),
            },
            "metadata": {
                "timestamp": int(time.time()),
                "task": task.get("task"),
            },
        }

    # ------------------------------------------------------------------
    def _format_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        requirements = "\n".join(f"- {item}" for item in task.get("requirements", []))
        last_result = context.get("last_result")
        last_result_text = json.dumps(last_result) if last_result else "None"

        return (
            f"You are assisting with task '{task.get('task')}'.\n"
            f"Language: {task.get('language', 'unspecified')}\n"
            f"Framework: {task.get('framework', 'unspecified')}\n"
            f"Requirements:\n{requirements or '- None provided'}\n\n"
            f"Previous result: {last_result_text}"
        )


class _DefaultHTTPHandler:
    """Minimal HTTP handler wrapper to ease testing."""

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    def post(self, *, url: str, data: bytes, headers: Dict[str, str]) -> str:
        request = urllib.request.Request(url=url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8")


def _resolve_api_key(config: Dict[str, Any]) -> str:
    """Resolve the API key from config or environment."""

    key = config.get("api_key")
    if key:
        return key

    env_var = config.get("api_key_env")
    if env_var:
        return os.getenv(env_var, "")
    return ""


__all__ = ["AuthenticationError", "DeepSeekConnector", "DeepSeekSettings"]
