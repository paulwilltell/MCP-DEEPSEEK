"""Runtime for coordinating MCP connectors including DeepSeek.

This module defines the :class:`HostRuntime` responsible for managing
connectors, routing tasks, and maintaining shared context for the host
application.  It is intentionally lightweight so that it can be embedded
in a variety of orchestration environments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Protocol


class ConnectorError(RuntimeError):
    """Raised when a connector experiences a recoverable failure."""


class Connector(Protocol):
    """Structural protocol describing connector behaviour."""

    name: str

    def supports(self, task: Dict[str, Any]) -> bool:
        """Return ``True`` when the connector can handle ``task``."""

    def handle(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ``task`` and return a normalised response payload."""


@dataclass
class RegisteredConnector:
    """Metadata wrapper around a connector instance."""

    connector: Connector
    routes: Iterable[str] = field(default_factory=list)


class HostRuntime:
    """Simple runtime that coordinates connectors for MCP workflows."""

    def __init__(self, *, context: Optional[Dict[str, Any]] = None) -> None:
        self.context: Dict[str, Any] = context or {}
        self._connectors: Dict[str, RegisteredConnector] = {}
        self._routing_table: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Registration & configuration
    # ------------------------------------------------------------------
    def register_connector(
        self,
        connector: Connector,
        *,
        routes: Optional[Iterable[str]] = None,
    ) -> None:
        """Register ``connector`` with optional explicit ``routes``.

        ``routes`` is an iterable of task identifiers that should always be
        dispatched to this connector.  Attempting to register two connectors
        with the same name raises :class:`ValueError` to surface
        configuration mistakes early.
        """

        if connector.name in self._connectors:
            raise ValueError(f"Connector '{connector.name}' already registered")

        registered = RegisteredConnector(connector=connector, routes=routes or [])
        self._connectors[connector.name] = registered

        for task_name in registered.routes:
            self._routing_table[task_name] = connector.name

    # ------------------------------------------------------------------
    # Task routing
    # ------------------------------------------------------------------
    def route_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route and execute a task across registered connectors.

        The routing strategy honours, in order of precedence:

        1. An explicit ``target`` value inside the task payload.
        2. Static routes defined during registration.
        3. Capability discovery via :meth:`Connector.supports`.

        The method updates the runtime context with the latest task result
        under ``last_result`` to enable chaining of subtasks.
        """

        connector = self._select_connector(task)
        if connector is None:
            raise ConnectorError(f"No connector available for task: {task!r}")

        try:
            result = connector.handle(task, self.context)
        except ConnectorError:
            raise
        except Exception as exc:  # pragma: no cover - safety net
            raise ConnectorError(str(exc)) from exc

        self.context["last_result"] = result
        return {"connector": connector.name, "result": result}

    # ------------------------------------------------------------------
    def _select_connector(self, task: Dict[str, Any]) -> Optional[Connector]:
        """Internal helper that selects the most appropriate connector."""

        target = task.get("target")
        if target:
            registered = self._connectors.get(target)
            return registered.connector if registered else None

        task_name = task.get("task")
        if task_name and task_name in self._routing_table:
            connector_name = self._routing_table[task_name]
            return self._connectors[connector_name].connector

        for registered in self._connectors.values():
            if registered.connector.supports(task):
                return registered.connector
        return None


__all__ = ["Connector", "ConnectorError", "HostRuntime"]
