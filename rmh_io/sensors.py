"""Sensor abstraction and synthetic drivers for tri-axial magnetometers."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from random import gauss
from typing import Callable, Iterable, List, Tuple


@dataclass
class MagnetometerReading:
    sensor_id: str
    timestamp: float
    magnetic_field: Tuple[float, float, float]


class BaseMagnetometer:
    """Abstract magnetometer interface."""

    sensor_id: str

    def __init__(self, sensor_id: str) -> None:
        self.sensor_id = sensor_id

    def read(self) -> MagnetometerReading:
        raise NotImplementedError


class SyntheticMagnetometer(BaseMagnetometer):
    """Synthetic driver emitting sinusoidal magnetic signatures."""

    def __init__(self, sensor_id: str, frequency: float, noise_std: float = 0.01) -> None:
        super().__init__(sensor_id)
        self.frequency = frequency
        self.noise_std = noise_std
        self._start = time.time()

    def _signal(self, t: float) -> Tuple[float, float, float]:
        phase = 2 * math.pi * self.frequency * t
        base = (
            math.sin(phase),
            math.cos(phase),
            math.sin(phase * 0.5 + math.pi / 4),
        )
        noise = tuple(gauss(0.0, self.noise_std) for _ in range(3))
        return tuple(b + n for b, n in zip(base, noise))

    def read(self) -> MagnetometerReading:
        t = time.time() - self._start
        return MagnetometerReading(sensor_id=self.sensor_id, timestamp=t, magnetic_field=self._signal(t))


class SensorArray:
    """Manage a collection of magnetometers sampled at a fixed rate."""

    def __init__(self, sensors: Iterable[BaseMagnetometer], sample_rate_hz: float) -> None:
        self.sensors = list(sensors)
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        self.sample_rate_hz = sample_rate_hz

    def sample_once(self) -> List[MagnetometerReading]:
        return [sensor.read() for sensor in self.sensors]

    def stream(self, duration_s: float, callback: Callable[[List[MagnetometerReading]], None]) -> None:
        interval = 1.0 / self.sample_rate_hz
        end_time = time.time() + duration_s
        while time.time() < end_time:
            readings = self.sample_once()
            callback(readings)
            time.sleep(interval)


def build_synthetic_array(num_sensors: int, base_freq: float = 5.0) -> SensorArray:
    sensors = [SyntheticMagnetometer(f"sensor_{i}", frequency=base_freq + i) for i in range(num_sensors)]
    return SensorArray(sensors, sample_rate_hz=200.0)
