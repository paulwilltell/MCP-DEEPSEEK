"""Loss helpers shared across components."""
from __future__ import annotations

import torch


def physics_loss(res_curl: torch.Tensor, res_div: torch.Tensor, w_curl: float = 1.0, w_div: float = 1.0) -> torch.Tensor:
    """Weighted physics loss enforcing Maxwell residuals."""
    return w_curl * (res_curl ** 2).mean() + w_div * (res_div ** 2).mean()


def data_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Simple mean squared error loss."""
    return ((pred - target) ** 2).mean()


def temporal_sparsity_loss(signal: torch.Tensor, lam: float = 1e-3) -> torch.Tensor:
    """Encourage temporal sparsity using an L1 penalty."""
    return lam * signal.abs().mean()
