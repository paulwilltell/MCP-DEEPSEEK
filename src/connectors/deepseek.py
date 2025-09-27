"""DeepSeek connector for MCP host runtime."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Protocol


class HTTPClient(Protocol):
    """Protocol for HTTP clients used by the connector."""

    def post(self, url: str, json: Dict[str, Any], headers: Dict[str, str]) -> Any:
        """Send a POST request."""


class AuthenticationError(RuntimeError):
    """Raised when authentication credentials are missing."""


class DeepSeekConnector:
    """Connector that wraps DeepSeek completion APIs for MCP tasks."""

    def __init__(self, config: Dict[str, Any], http_client: Optional[HTTPClient] = None) -> None:
        self.config = config or {}
        self.http_client = http_client
        self.api_key = self._load_api_key()
        self.endpoint = self.config.get("endpoint", "https://api.deepseek.com/v1/chat/completions")

    def _load_api_key(self) -> str:
        credentials = self.config.get("credentials", {})
        api_key = credentials.get("api_key")
        env_var = credentials.get("api_key_env")

        if not api_key and env_var:
            api_key = os.getenv(env_var)

        if not api_key:
            raise AuthenticationError("DeepSeek API key is not configured.")

        return api_key

    def _build_payload(self, request: Dict[str, Any]) -> Dict[str, Any]:
        messages = request.get("messages")
        if not messages:
            prompt = request.get("prompt") or request.get("task") or ""
            messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.config.get("model", "deepseek-chat"),
            "messages": messages,
            "temperature": request.get("temperature", self.config.get("temperature", 0.7)),
        }
        return payload

    def _call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.http_client:
            raise RuntimeError("No HTTP client configured for DeepSeekConnector.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = self.http_client.post(self.endpoint, json=payload, headers=headers)
        return response

    def send_task(self, request: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._build_payload(request)
        try:
            response = self._call_api(payload)
        except AuthenticationError:
            raise
        except Exception as exc:  # noqa: BLE001 - propagate unexpected errors downstream
            return {
                "error": str(exc),
                "retryable": isinstance(exc, (TimeoutError, ConnectionError)),
            }
        return response

    def normalize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        if "error" in response:
            return response

        choices = response.get("choices")
        if choices:
            message = choices[0].get("message", {})
            return {
                "role": message.get("role", "assistant"),
                "content": message.get("content", ""),
                "raw": response,
            }

        # Fallback to pass-through of unknown structures.
        return {"raw": response}


__all__ = ["DeepSeekConnector", "AuthenticationError"]
