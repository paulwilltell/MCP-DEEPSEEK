#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME=$(basename "$0")
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/${SCRIPT_NAME%.sh}.log"
MODE="DRY_RUN"
MODEL_PATH_ARG=""
PROMPT="Hello!"
MAX_TOKENS=64
PYTHON_BIN="python3"

exec > >(tee -a "$LOG_PATH") 2>&1
trap 'on_exit $?' EXIT

if [[ -f $REPO_ROOT/.env ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$REPO_ROOT/.env"
  set +a
fi
ENV_MODEL_PATH="${MODEL_PATH:-}"

RESULT_JSON=''
EXIT_CODE=0
MESSAGE="Smoke test not executed"

function usage() {
  cat <<USAGE
Usage: $SCRIPT_NAME [--mode=DRY_RUN|EXECUTE] [--model-path PATH] [--prompt PROMPT]
                      [--max-tokens N] [--python PYTHON_BIN]
Runs a deterministic llama-cpp-python inference for validation.
USAGE
}

function on_exit() {
  local code=$?
  if [[ $code -ne 0 ]]; then
    EXIT_CODE=$code
  fi
  if [[ -z $RESULT_JSON ]]; then
    RESULT_JSON=$(printf '{"success":false,"code":%d,"message":"%s","latency_ms":0,"sample_output":"","errors":["Smoke test did not run"],"log_path":"%s"}' "$EXIT_CODE" "$MESSAGE" "$LOG_PATH")
  fi
  printf '%s\n' "$RESULT_JSON"
}

function set_result() {
  local success=$1
  local code=$2
  local message=$3
  local latency=$4
  local output_json=$5
  local errors_json=$6
  RESULT_JSON=$(printf '{"success":%s,"code":%d,"message":"%s","latency_ms":%s,"sample_output":%s,"errors":%s,"log_path":"%s"}' \
    "$success" "$code" "$message" "$latency" "$output_json" "$errors_json" "$LOG_PATH")
  EXIT_CODE=$code
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --mode=*) MODE="${1#*=}" ;;
    --mode) MODE="$2"; shift ;;
    --model-path=*) MODEL_PATH_ARG="${1#*=}" ;;
    --model-path) MODEL_PATH_ARG="$2"; shift ;;
    --prompt=*) PROMPT="${1#*=}" ;;
    --prompt) PROMPT="$2"; shift ;;
    --max-tokens=*) MAX_TOKENS="${1#*=}" ;;
    --max-tokens) MAX_TOKENS="$2"; shift ;;
    --python=*) PYTHON_BIN="${1#*=}" ;;
    --python) PYTHON_BIN="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) MESSAGE="Invalid argument"; EXIT_CODE=64; exit 64 ;;
  esac
  shift
done

MODE=${MODE^^}
if [[ $MODE != "DRY_RUN" && $MODE != "EXECUTE" ]]; then
  MESSAGE="Invalid mode: $MODE"
  EXIT_CODE=64
  exit 64
fi

MODEL_PATH=${MODEL_PATH_ARG:-$ENV_MODEL_PATH}

if [[ -z $MODEL_PATH ]]; then
  set_result false 66 "Model path not provided" 0 '""' '["Set MODEL_PATH in the environment or pass --model-path. Use scripts/download_model.sh to fetch a model."]'
  exit 66
fi

if [[ $MODE == "DRY_RUN" ]]; then
  if [[ ! -f $MODEL_PATH ]]; then
    set_result false 66 "Model file missing" 0 '""' "[\"Model not found at $MODEL_PATH\"]"
  else
    set_result true 0 "Smoke test commands prepared" 0 '""' '[]'
  fi
  exit $EXIT_CODE
fi

if [[ ! -f $MODEL_PATH ]]; then
  set_result false 66 "Model file not found" 0 '""' "[\"Model missing at $MODEL_PATH\"]"
  exit 66
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  set_result false 69 "Python interpreter not found" 0 '""' '["Install python3 or specify --python"]'
  exit 69
fi

RESULT=$($PYTHON_BIN - "$MODEL_PATH" "$PROMPT" "$MAX_TOKENS" <<'PY'
import json
import os
import sys
import time
from pathlib import Path

try:
    from llama_cpp import Llama
except ModuleNotFoundError as exc:  # pragma: no cover
    payload = {
        "success": False,
        "code": 69,
        "message": "llama-cpp-python is not installed",
        "latency_ms": 0,
        "sample_output": "",
        "errors": [str(exc)],
    }
    print(json.dumps(payload))
    raise

model_path = Path(sys.argv[1]).expanduser().resolve()
prompt = sys.argv[2]
max_tokens = int(sys.argv[3])
threads = int(os.getenv("OMP_NUM_THREADS", "0")) or None

if not model_path.exists():
    payload = {
        "success": False,
        "code": 66,
        "message": f"Model not found at {model_path}",
        "latency_ms": 0,
        "sample_output": "",
        "errors": ["Download the model using scripts/download_model.sh"],
    }
    print(json.dumps(payload))
    raise SystemExit(66)

try:
    llama = Llama(model_path=str(model_path), n_threads=threads, n_batch=256, logits_all=False, verbose=False)
except Exception as exc:  # noqa: BLE001
    payload = {
        "success": False,
        "code": 70,
        "message": "Failed to initialize llama-cpp-python",
        "latency_ms": 0,
        "sample_output": "",
        "errors": [str(exc)],
    }
    print(json.dumps(payload))
    raise

start = time.perf_counter()
try:
    result = llama(prompt, max_tokens=max_tokens, temperature=0.2, stop=["\n###"])
except Exception as exc:  # noqa: BLE001
    payload = {
        "success": False,
        "code": 70,
        "message": "Generation failed",
        "latency_ms": 0,
        "sample_output": "",
        "errors": [str(exc)],
    }
    print(json.dumps(payload))
    raise

latency_ms = (time.perf_counter() - start) * 1000
text = result["choices"][0]["text"].strip()
payload = {
    "success": True,
    "code": 0,
    "message": "Smoke test succeeded",
    "latency_ms": round(latency_ms, 2),
    "sample_output": text,
    "errors": [],
}
print(json.dumps(payload))
PY
)
PY_EXIT=$?

if [[ $PY_EXIT -ne 0 ]]; then
  RESULT_JSON=$(python - <<'PY'
import json
import sys
payload = json.loads(sys.stdin.read())
payload.setdefault("success", False)
payload.setdefault("code", 70)
payload.setdefault("message", "Smoke test failure")
payload.setdefault("latency_ms", 0)
payload.setdefault("sample_output", "")
payload.setdefault("errors", [])
payload["log_path"] = sys.argv[1]
print(json.dumps(payload))
PY
"$LOG_PATH" <<<"$RESULT")
  EXIT_CODE=$PY_EXIT
  exit $PY_EXIT
fi

RESULT_JSON=$(python - <<'PY'
import json
import sys
payload = json.loads(sys.stdin.read())
payload["log_path"] = sys.argv[1]
print(json.dumps(payload))
PY
"$LOG_PATH" <<<"$RESULT")
EXIT_CODE=0
