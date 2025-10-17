"""Calibration routines for coil driving and sensor characterization."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from rmh_io.sensors import MagnetometerReading


@dataclass
class SensorCalibration:
    sensor_id: str
    offset: float
    gain: float
    orientation: List[float]


@dataclass
class CalibrationReport:
    sensors: List[SensorCalibration]
    gradiometers: List[List[str]]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def write(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")


def estimate_calibration(readings: Iterable[MagnetometerReading]) -> List[SensorCalibration]:
    grouped: Dict[str, List[Tuple[float, float, float]]] = {}
    for reading in readings:
        grouped.setdefault(reading.sensor_id, []).append(reading.magnetic_field)
    calibrations = []
    for sensor_id, samples in grouped.items():
        if not samples:
            continue
        mean_vec = [sum(component[i] for component in samples) / len(samples) for i in range(3)]
        offset = sum(mean_vec) / 3.0
        variance = sum(
            sum((component[i] - mean_vec[i]) ** 2 for i in range(3)) for component in samples
        ) / (len(samples) * 3)
        gain = (variance ** 0.5) + 1e-6
        norm = (sum(v ** 2 for v in mean_vec) ** 0.5) + 1e-6
        orientation = [v / norm for v in mean_vec]
        calibrations.append(SensorCalibration(sensor_id, offset, gain, orientation))
    return calibrations


def compute_gradiometers(calibrations: List[SensorCalibration]) -> List[List[str]]:
    pairs = []
    for i in range(0, len(calibrations), 2):
        if i + 1 < len(calibrations):
            pairs.append([calibrations[i].sensor_id, calibrations[i + 1].sensor_id])
    return pairs


def run_calibration(readings: Iterable[MagnetometerReading], output: Path) -> CalibrationReport:
    calibrations = estimate_calibration(readings)
    gradiometers = compute_gradiometers(calibrations)
    report = CalibrationReport(calibrations, gradiometers)
    report.write(output)
    return report
