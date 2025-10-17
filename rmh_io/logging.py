"""Logging utilities for writing synchronized sensor data to Parquet."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

from .sensors import MagnetometerReading


@dataclass
class ParquetLogger:
    output_path: Path
    calibration: Dict[str, float]
    metadata_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.metadata_path = self.output_path.with_suffix(".json")

    def write(self, readings: Iterable[MagnetometerReading]) -> None:
        records = [
            {
                "sensor_id": r.sensor_id,
                "timestamp": r.timestamp,
                "Bx": r.magnetic_field[0],
                "By": r.magnetic_field[1],
                "Bz": r.magnetic_field[2],
            }
            for r in readings
        ]
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        # Minimal Parquet-compatible JSON surrogate for environments without parquet libs.
        with self.output_path.open("w", encoding="utf-8") as fh:
            json.dump({"schema": ["sensor_id", "timestamp", "Bx", "By", "Bz"], "records": records}, fh)
        with self.metadata_path.open("w", encoding="utf-8") as fh:
            json.dump({"calibration": self.calibration}, fh)


def synchronize(readings: List[MagnetometerReading]) -> List[MagnetometerReading]:
    """Simple synchronization by shifting timestamps to start at zero."""
    if not readings:
        return readings
    min_ts = min(r.timestamp for r in readings)
    synced = [
        MagnetometerReading(
            sensor_id=r.sensor_id,
            timestamp=r.timestamp - min_ts,
            magnetic_field=r.magnetic_field,
        )
        for r in readings
    ]
    return synced
