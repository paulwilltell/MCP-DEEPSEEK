"""Synthetic dataset utilities for rmh_operator training."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

import torch
from torch.utils.data import Dataset


def generate_synthetic_coil_logs(num_samples: int, sensors: int, freq_bins: int) -> Tuple[torch.Tensor, torch.Tensor]:
    sources = torch.rand(num_samples, 3, freq_bins)
    transfer = torch.rand(3, sensors, 3) * 0.1
    responses = torch.einsum("bif,ijc->bjcf", sources, transfer)
    return sources, responses


class CoilLogDataset(Dataset):
    def __init__(self, sources: torch.Tensor, targets: torch.Tensor) -> None:
        self.sources = sources
        self.targets = targets

    def __len__(self) -> int:
        return self.sources.shape[0]

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.sources[idx], self.targets[idx]
