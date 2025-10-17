"""FastAPI service for visualization and metrics."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import cos, pi, sin
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel


@dataclass
class FieldMetric:
    name: str
    value: float
    confidence: float


class FieldResponse(BaseModel):
    iso_surface: List[List[float]]
    streamlines: List[List[List[float]]]
    uncertainty: List[float]


class MetricsResponse(BaseModel):
    metrics: List[FieldMetric]


app = FastAPI(title="RMH Visualization")


def _generate_streamlines(num: int = 4) -> List[List[List[float]]]:
    streamlines = []
    theta = [2 * pi * i / 31 for i in range(32)]
    for i in range(num):
        radius = 0.1 * (i + 1)
        streamlines.append([[radius * cos(t), radius * sin(t), 0.01 * i * t] for t in theta])
    return streamlines


def _generate_iso_surface(levels: int = 10) -> List[List[float]]:
    phi = [2 * pi * i / max(1, levels - 1) for i in range(levels)]
    theta = [pi * i / max(1, levels - 1) for i in range(levels)]
    points = []
    for p in phi:
        for th in theta:
            x = 0.3 * sin(th) * cos(p)
            y = 0.2 * sin(th) * sin(p)
            z = 0.4 * cos(th)
            points.append([x, y, z])
    return points


@app.get("/field/iso", response_model=FieldResponse)
def get_iso_surface() -> FieldResponse:
    return FieldResponse(
        iso_surface=_generate_iso_surface(),
        streamlines=_generate_streamlines(),
        uncertainty=[0.1] * 10,
    )


@app.get("/field/stream", response_model=FieldResponse)
def get_streamlines() -> FieldResponse:
    return FieldResponse(
        iso_surface=_generate_iso_surface(levels=5),
        streamlines=_generate_streamlines(num=6),
        uncertainty=[0.05] * 10,
    )


@app.get("/metrics")
def get_metrics() -> dict:
    metrics = [
        FieldMetric("Field Envelope Volume", 1200.0, 0.1),
        FieldMetric("Peak |B|", 85.0, 0.05),
        FieldMetric("Heart-locked Magnetic Coherence", 0.82, 0.08),
    ]
    return {"metrics": [asdict(m) for m in metrics]}
