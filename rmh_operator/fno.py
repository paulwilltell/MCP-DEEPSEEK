"""Fourier Neural Operator implementation for room transfer learning."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn


def _complex_mul_1d(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return torch.stack([
        a[..., 0] * b[..., 0] - a[..., 1] * b[..., 1],
        a[..., 0] * b[..., 1] + a[..., 1] * b[..., 0],
    ], dim=-1)


class SpectralConv1d(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, modes: int) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.modes = modes
        self.weight = nn.Parameter(torch.randn(in_channels, out_channels, modes, 2) * 0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batchsize, channels, width = x.shape
        x_ft = torch.fft.rfft(x, dim=-1)
        out_ft = torch.zeros(batchsize, self.out_channels, width // 2 + 1, device=x.device, dtype=torch.cfloat)
        modes = min(self.modes, x_ft.shape[-1])
        weight = torch.view_as_complex(self.weight[:, :, :modes])
        out_ft[:, :, :modes] = torch.einsum("bci,cio->bio", x_ft[:, :, :modes], weight)
        x = torch.fft.irfft(out_ft, n=width, dim=-1)
        return x


class FNOBlock(nn.Module):
    def __init__(self, width: int, modes: int) -> None:
        super().__init__()
        self.spectral = SpectralConv1d(width, width, modes)
        self.w = nn.Conv1d(width, width, kernel_size=1)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.spectral(x)
        x2 = self.w(x)
        return self.act(x1 + x2)


class RoomTransferFNO(nn.Module):
    """Maps source positions/frequencies to sensor field responses."""

    def __init__(self, modes: int = 16, width: int = 64, depth: int = 4, sensors: int = 8) -> None:
        super().__init__()
        self.input_proj = nn.Conv1d(3, width, kernel_size=1)
        self.blocks = nn.ModuleList([FNOBlock(width, modes) for _ in range(depth)])
        self.output_proj = nn.Conv1d(width, sensors * 3, kernel_size=1)
        self.sensors = sensors

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [batch, 3, freq_bins]
        z = self.input_proj(x)
        for block in self.blocks:
            z = block(z)
        out = self.output_proj(z)
        return out.view(out.shape[0], self.sensors, 3, -1)
