"""Core physics utilities shared across RMH packages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import torch

mu0 = 4e-7 * torch.tensor(3.141592653589793)


def _pad_for_derivative(field: torch.Tensor) -> torch.Tensor:
    """Pad spatial dimensions with replication to support finite differences."""
    pads = []
    # pad last 4 dims (X,Y,Z) with 1 on each side
    for _ in range(3):
        pads.extend([1, 1])
    return torch.nn.functional.pad(field, tuple(pads), mode="replicate")


def finite_curl(B: torch.Tensor, dx: float) -> torch.Tensor:
    """Compute the curl of a vector field using second order differences.

    Args:
        B: Tensor with shape [..., X, Y, Z, 3].
        dx: Spatial step (assumed isotropic).
    Returns:
        Tensor with shape [..., X, Y, Z, 3].
    """
    if B.shape[-1] != 3:
        raise ValueError("Expected last dimension to be 3 (vector field components)")

    padded = _pad_for_derivative(B.movedim(-1, 1))
    Bx, By, Bz = padded[:, 0], padded[:, 1], padded[:, 2]

    def diff_x(f: torch.Tensor) -> torch.Tensor:
        return (f[..., 2:, 1:-1, 1:-1] - f[..., :-2, 1:-1, 1:-1]) / (2 * dx)

    def diff_y(f: torch.Tensor) -> torch.Tensor:
        return (f[..., 1:-1, 2:, 1:-1] - f[..., 1:-1, :-2, 1:-1]) / (2 * dx)

    def diff_z(f: torch.Tensor) -> torch.Tensor:
        return (f[..., 1:-1, 1:-1, 2:] - f[..., 1:-1, 1:-1, :-2]) / (2 * dx)

    curl_x = diff_y(Bz) - diff_z(By)
    curl_y = diff_z(Bx) - diff_x(Bz)
    curl_z = diff_x(By) - diff_y(Bx)
    curl = torch.stack([curl_x, curl_y, curl_z], dim=-1)
    return curl


def finite_div(B: torch.Tensor, dx: float) -> torch.Tensor:
    """Compute the divergence of a vector field using central differences."""
    if B.shape[-1] != 3:
        raise ValueError("Expected last dimension to be 3 (vector field components)")

    padded = _pad_for_derivative(B.movedim(-1, 1))
    Bx, By, Bz = padded[:, 0], padded[:, 1], padded[:, 2]

    def diff_x(f: torch.Tensor) -> torch.Tensor:
        return (f[..., 2:, 1:-1, 1:-1] - f[..., :-2, 1:-1, 1:-1]) / (2 * dx)

    def diff_y(f: torch.Tensor) -> torch.Tensor:
        return (f[..., 1:-1, 2:, 1:-1] - f[..., 1:-1, :-2, 1:-1]) / (2 * dx)

    def diff_z(f: torch.Tensor) -> torch.Tensor:
        return (f[..., 1:-1, 1:-1, 2:] - f[..., 1:-1, 1:-1, :-2]) / (2 * dx)

    div = diff_x(Bx) + diff_y(By) + diff_z(Bz)
    return div.unsqueeze(-1)


@dataclass
class MaxwellResiduals:
    """Container for curl and divergence residuals."""

    res_curl: torch.Tensor
    res_div: torch.Tensor


def maxwell_residuals(B: torch.Tensor, J: torch.Tensor, dx: float) -> MaxwellResiduals:
    """Evaluate Maxwell's equations residuals for the predicted fields."""
    curlB = finite_curl(B, dx)
    divB = finite_div(B, dx)
    res_curl = curlB - mu0 * J
    res_div = divB
    return MaxwellResiduals(res_curl=res_curl, res_div=res_div)


def forward_operator(H, J: torch.Tensor) -> torch.Tensor:
    """Apply a learned neural operator mapping sources to sensors."""
    if not callable(H):
        raise TypeError("H must be callable")
    return H(J)
