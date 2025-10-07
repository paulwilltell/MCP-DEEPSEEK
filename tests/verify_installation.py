"""Verification script for personal-local-ai.

Returns JSON with success flag, errors, and details about the environment.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

RESULT: Dict[str, Any] = {
    "success": False,
    "errors": [],
    "details": {},
}

CONDA_ENV = os.environ.get("CONDA_DEFAULT_ENV")
PY_EXEC = sys.executable
RESULT["details"]["python_executable"] = PY_EXEC
RESULT["details"]["conda_env"] = CONDA_ENV

try:
    import importlib.metadata as metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore


def fail(code: int, message: str, *, errors: List[str] | None = None) -> None:
    RESULT["success"] = False
    if errors:
        RESULT["errors"].extend(errors)
    else:
        RESULT["errors"].append(message)
    RESULT["details"]["message"] = message
    print(json.dumps(RESULT, indent=2))
    raise SystemExit(code)


def detect_model_path() -> Path | None:
    env_path = os.environ.get("MODEL_PATH")
    if env_path:
        path = Path(env_path).expanduser()
        if path.exists():
            return path
    models_dir = Path(__file__).resolve().parents[1] / "models"
    candidates = sorted(models_dir.glob("*.gguf"))
    if candidates:
        return candidates[0]
    return None


def check_dependency(pkg: str) -> None:
    try:
        metadata.version(pkg)
        RESULT["details"].setdefault("packages", {})[pkg] = metadata.version(pkg)
    except metadata.PackageNotFoundError:
        RESULT["errors"].append(f"Package missing: {pkg}")


check_dependency("fastapi")
check_dependency("llama-cpp-python")

try:
    from llama_cpp import Llama
except ModuleNotFoundError as exc:  # pragma: no cover
    fail(70, "llama-cpp-python is not installed", errors=[str(exc)])

model_path = detect_model_path()
if model_path is None:
    fail(
        66,
        "No GGUF model found",
        errors=[
            "Place a quantized GGUF model under ./models or set MODEL_PATH (use an absolute path)",
            "Use scripts/download_model.sh with HF_TOKEN or MODEL_URL",
        ],
    )

RESULT["details"]["model_path"] = str(model_path)

try:
    llama = Llama(model_path=str(model_path), n_threads=int(os.getenv("OMP_NUM_THREADS", "0")) or None, n_batch=256, verbose=False)
except Exception as exc:  # noqa: BLE001
    fail(70, "Failed to initialize llama-cpp-python", errors=[str(exc)])

prompt = "Hello! Please reply with a short friendly greeting."
start = time.perf_counter()
try:
    response = llama(prompt, max_tokens=64, temperature=0.2, stop=["\n###"])
except Exception as exc:  # noqa: BLE001
    fail(70, "Model generation failed", errors=[str(exc)])
latency_ms = (time.perf_counter() - start) * 1000
text = response["choices"][0]["text"].strip()

if not text:
    fail(70, "Model returned empty response", errors=["Unexpected empty generation output"])

RESULT["success"] = True
RESULT["details"].update(
    {
        "latency_ms": round(latency_ms, 2),
        "sample_output": text,
        "avg_latency_threshold_ms": 20000,
    }
)

print(json.dumps(RESULT, indent=2))
