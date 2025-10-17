"""Streaming utilities for routing magnetometer readings to different buses."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, List, Protocol

from .sensors import MagnetometerReading


class BusPublisher(Protocol):
    def publish(self, topic: str, payload: bytes) -> None:  # pragma: no cover - protocol definition
        ...


@dataclass
class InMemoryBus:
    """Simple bus used in tests to emulate Kafka/ZeroMQ."""

    messages: List[tuple[str, bytes]]

    def publish(self, topic: str, payload: bytes) -> None:
        self.messages.append((topic, payload))


class JsonMessageEncoder:
    """Encodes magnetometer readings as JSON payloads."""

    @staticmethod
    def encode(readings: Iterable[MagnetometerReading]) -> bytes:
        return json.dumps(
            [
                {
                    "sensor_id": r.sensor_id,
                    "timestamp": r.timestamp,
                    "magnetic_field": list(r.magnetic_field),
                }
                for r in readings
            ]
        ).encode("utf-8")


class StreamDispatcher:
    """Dispatch readings to a bus using a topic schema."""

    def __init__(self, bus: BusPublisher, topic: str = "rmh.magnetometers") -> None:
        self.bus = bus
        self.topic = topic

    def dispatch(self, readings: List[MagnetometerReading]) -> None:
        payload = JsonMessageEncoder.encode(readings)
        self.bus.publish(self.topic, payload)
