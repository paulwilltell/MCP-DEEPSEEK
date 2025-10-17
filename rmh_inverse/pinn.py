"""Physics-informed neural network for inverse reconstruction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import torch
import torch.nn as nn

from rmh_core.losses import data_loss, physics_loss, temporal_sparsity_loss
from rmh_core.physics import MaxwellResiduals, forward_operator, maxwell_residuals


class DropoutMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, dropout: float = 0.1) -> None:
        super().__init__()
        layers = []
        dims = [input_dim] + [hidden_dim] * 3 + [output_dim]
        for i in range(len(dims) - 2):
            layers.append(nn.Linear(dims[i], dims[i + 1]))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(dropout))
        layers.append(nn.Linear(dims[-2], dims[-1]))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class RMHInversePINN(nn.Module):
    def __init__(self, sensor_dim: int, grid_points: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.sensor_dim = sensor_dim
        self.grid_points = grid_points
        self.encoder = DropoutMLP(sensor_dim + 1, 128, grid_points * 3, dropout=dropout)
        self.field_decoder = DropoutMLP(grid_points * 3 + 1, 128, grid_points * 3, dropout=dropout)

    def forward(self, sensors: torch.Tensor, ecg: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # sensors: [batch, time, sensors*3], ecg: [batch, time]
        batch, time_steps, _ = sensors.shape
        ecg_feature = ecg.unsqueeze(-1)
        enc_in = torch.cat([sensors, ecg_feature], dim=-1)
        latent = self.encoder(enc_in)
        J = latent.view(batch, time_steps, self.grid_points, 3)
        field_in = torch.cat([latent, ecg_feature], dim=-1)
        field = self.field_decoder(field_in)
        B = field.view(batch, time_steps, self.grid_points, 3)
        return J, B


@dataclass
class PINNLosses:
    total: torch.Tensor
    data: torch.Tensor
    physics: torch.Tensor
    sparsity: torch.Tensor


def pinn_step(model: RMHInversePINN, sensors: torch.Tensor, ecg: torch.Tensor, H_model, dx: float) -> PINNLosses:
    J, B = model(sensors, ecg)
    B_sensors_pred = forward_operator(H_model, J)
    sensors_target = sensors.view(sensors.shape[0], sensors.shape[1], -1, 3)
    residuals: MaxwellResiduals = maxwell_residuals(B, J, dx)
    d_loss = data_loss(B_sensors_pred, sensors_target)
    p_loss = physics_loss(residuals.res_curl, residuals.res_div)
    s_loss = temporal_sparsity_loss(J)
    total = d_loss + p_loss + s_loss
    return PINNLosses(total=total, data=d_loss, physics=p_loss, sparsity=s_loss)


def monte_carlo_uncertainty(model: RMHInversePINN, sensors: torch.Tensor, ecg: torch.Tensor, samples: int = 5) -> torch.Tensor:
    model.train()
    estimates = []
    for _ in range(samples):
        J, _ = model(sensors, ecg)
        estimates.append(J.unsqueeze(0))
    stacked = torch.cat(estimates, dim=0)
    return stacked.var(dim=0)
