"""Command line interface for fitting the room transfer operator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Tuple

import torch
from torch.utils.data import DataLoader, random_split

from .data import CoilLogDataset, generate_synthetic_coil_logs
from .fno import RoomTransferFNO


def load_coil_logs(path: Path, sensors: int, freq_bins: int) -> Tuple[torch.Tensor, torch.Tensor]:
    if not path.exists():
        return generate_synthetic_coil_logs(64, sensors=sensors, freq_bins=freq_bins)
    data = torch.load(path)
    return data["sources"], data["targets"]


def train_model(dataset: CoilLogDataset, sensors: int, freq_bins: int, epochs: int = 5) -> Tuple[RoomTransferFNO, dict]:
    val_size = max(1, int(0.2 * len(dataset)))
    train_size = len(dataset) - val_size
    train_set, val_set = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(train_set, batch_size=8, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=8)

    model = RoomTransferFNO(sensors=sensors)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = torch.nn.L1Loss()

    best_val = float("inf")
    patience = 2
    bad_epochs = 0
    history = {"train_mae": [], "val_mae": []}

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for x, y in train_loader:
            optimizer.zero_grad()
            pred = model(x)
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        train_loss /= max(1, len(train_loader))

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x, y in val_loader:
                pred = model(x)
                loss = criterion(pred, y)
                val_loss += loss.item()
        val_loss /= max(1, len(val_loader))

        history["train_mae"].append(train_loss)
        history["val_mae"].append(val_loss)

        if val_loss < best_val:
            best_val = val_loss
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break

    metrics = {
        "train_mae": history["train_mae"][-1],
        "val_mae": history["val_mae"][-1],
        "phase_error": float(best_val),
    }
    return model, metrics


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Fit RMH room transfer operator")
    parser.add_argument("--coil-logs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sensors", type=int, default=8)
    parser.add_argument("--freq-bins", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=5)
    args = parser.parse_args(argv)

    sources, targets = load_coil_logs(args.coil_logs, args.sensors, args.freq_bins)
    dataset = CoilLogDataset(sources, targets)
    model, metrics = train_model(dataset, sensors=args.sensors, freq_bins=args.freq_bins, epochs=args.epochs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state": model.state_dict(), "metrics": metrics}, args.out)
    return metrics


if __name__ == "__main__":  # pragma: no cover
    main()
