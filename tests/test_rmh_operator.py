from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from rmh_operator.cli import load_coil_logs, main as cli_main, train_model
from rmh_operator.data import CoilLogDataset, generate_synthetic_coil_logs


def test_train_model_produces_metrics(tmp_path: Path):
    sources, targets = generate_synthetic_coil_logs(16, sensors=2, freq_bins=8)
    dataset = CoilLogDataset(sources, targets)
    model, metrics = train_model(dataset, sensors=2, freq_bins=8, epochs=2)
    assert "train_mae" in metrics and metrics["train_mae"] >= 0
    assert len(metrics["val_mae"].__str__()) > 0

    out_file = tmp_path / "model.pt"
    torch.save({"sources": sources, "targets": targets}, tmp_path / "logs.pt")
    metrics_cli = cli_main(["--coil-logs", str(tmp_path / "logs.pt"), "--out", str(out_file), "--sensors", "2", "--freq-bins", "8", "--epochs", "1"])
    assert out_file.exists()
    assert "phase_error" in metrics_cli
