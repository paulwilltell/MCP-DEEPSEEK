"""Synthetic dipole phantom generators for testing."""
from __future__ import annotations

from typing import Callable, Tuple

import torch


def dipole_phantom(time_steps: int, grid_points: int, sensors: int) -> Tuple[torch.Tensor, torch.Tensor, Callable[[torch.Tensor], torch.Tensor]]:
    t = torch.linspace(0, 1, time_steps)
    ecg = torch.sin(2 * torch.pi * 5 * t)
    J_true = torch.zeros(time_steps, grid_points, 3)
    center = grid_points // 2
    for i in range(time_steps):
        J_true[i, center, 0] = torch.sin(2 * torch.pi * i / time_steps)
        J_true[i, center, 1] = torch.cos(2 * torch.pi * i / time_steps)
    def H_model(J: torch.Tensor) -> torch.Tensor:
        weights = torch.linspace(0.5, 1.5, sensors, device=J.device)
        total = J.sum(dim=2)  # [batch, time, 3]
        scaled = total.unsqueeze(2) * weights.view(1, 1, -1, 1)
        return scaled

    sensors_series = H_model(J_true.unsqueeze(0)).squeeze(0)
    sensors_series = sensors_series + 0.01 * torch.randn_like(sensors_series)
    sensors_series = sensors_series.reshape(time_steps, sensors * 3)
    return sensors_series, ecg, H_model
