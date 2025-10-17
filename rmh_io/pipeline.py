"""Orchestrates acquisition -> streaming -> logging pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from .logging import ParquetLogger, synchronize
from .sensors import MagnetometerReading, SensorArray
from .streaming import StreamDispatcher


class AcquisitionPipeline:
    def __init__(self, array: SensorArray, dispatcher: StreamDispatcher, logger: ParquetLogger) -> None:
        self.array = array
        self.dispatcher = dispatcher
        self.logger = logger
        self._buffer: List[MagnetometerReading] = []

    def _collect(self, readings: List[MagnetometerReading]) -> None:
        self._buffer.extend(readings)
        self.dispatcher.dispatch(readings)

    def run(self, duration_s: float) -> Path:
        self._buffer.clear()
        self.array.stream(duration_s=duration_s, callback=self._collect)
        synced = synchronize(self._buffer)
        self.logger.write(synced)
        return self.logger.output_path

    @property
    def collected(self) -> List[MagnetometerReading]:
        return list(self._buffer)
