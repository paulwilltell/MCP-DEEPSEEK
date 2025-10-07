"""Entry point for the personal-local-ai FastAPI service and helper utilities."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ModuleNotFoundError as exc:  # pragma: no cover - FastAPI optional for tests
    raise RuntimeError(
        "FastAPI and Pydantic must be installed. Run install_conda_deps.sh or install_pip_deps.sh"
    ) from exc

try:
    from llama_cpp import Llama
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError(
        "llama-cpp-python is required. Build it via scripts/build_llama_cpp_python.sh"
    ) from exc


DEFAULT_PROMPT = "Hello! Please introduce yourself in one friendly sentence."


@dataclass
class Settings:
    model_path: Path
    max_tokens: int = 64
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> "Settings":
        if load_dotenv is not None:
            load_dotenv()
        model_env = os.getenv("MODEL_PATH")
        if not model_env:
            raise RuntimeError(
                "MODEL_PATH is not set. Provide --model-path argument or set MODEL_PATH in the environment/.env"
            )
        model_path = Path(model_env).expanduser().resolve()
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {model_path}. Use an absolute path and ensure the GGUF file exists."
            )
        max_tokens = int(os.getenv("MAX_NEW_TOKENS", "128"))
        temperature = float(os.getenv("MODEL_TEMPERATURE", "0.2"))
        return cls(model_path=model_path, max_tokens=max_tokens, temperature=temperature)


class PromptRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class LlamaRunner:
    """Thin wrapper around llama-cpp-python for deterministic usage."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._llama: Optional[Llama] = None

    def _ensure_model(self) -> Llama:
        if self._llama is None:
            self._llama = Llama(
                model_path=str(self.settings.model_path),
                n_threads=int(os.getenv("OMP_NUM_THREADS", "0")) or None,
                n_batch=512,
                logits_all=False,
                use_mlock=False,
                verbose=False,
            )
        return self._llama

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        llama = self._ensure_model()
        start = time.perf_counter()
        output = llama(
            prompt,
            max_tokens=max_tokens or self.settings.max_tokens,
            temperature=temperature if temperature is not None else self.settings.temperature,
            stop=["\n###"],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        text = output["choices"][0]["text"].strip()
        return {
            "latency_ms": round(latency_ms, 2),
            "text": text,
            "raw": output,
        }


def build_app(runner: LlamaRunner) -> FastAPI:
    app = FastAPI(title="personal-local-ai", version="0.1.0")

    @app.post("/generate")
    def generate(req: PromptRequest) -> Dict[str, Any]:
        if not req.prompt:
            raise HTTPException(status_code=400, detail="Prompt must not be empty")
        result = runner.generate(
            req.prompt,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        return {
            "success": True,
            "latency_ms": result["latency_ms"],
            "output": result["text"],
        }

    return app


def create_app() -> FastAPI:
    settings = Settings.from_env()
    runner = LlamaRunner(settings)
    return build_app(runner)


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run a deterministic prompt using llama-cpp-python")
    parser.add_argument("--model-path", type=Path, default=None, help="Path to GGUF model file")
    parser.add_argument("--prompt", type=str, default=DEFAULT_PROMPT)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args(argv)

    if args.model_path is not None:
        model_path = args.model_path.expanduser().resolve()
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. Confirm the GGUF file exists and pass an absolute path."
            )
        settings = Settings(model_path=model_path, max_tokens=args.max_tokens, temperature=args.temperature)
    else:
        settings = Settings.from_env()

    runner = LlamaRunner(settings)
    result = runner.generate(args.prompt, max_tokens=args.max_tokens, temperature=args.temperature)
    payload = {
        "success": True,
        "latency_ms": result["latency_ms"],
        "text": result["text"],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Latency: {payload['latency_ms']} ms\nOutput: {payload['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
