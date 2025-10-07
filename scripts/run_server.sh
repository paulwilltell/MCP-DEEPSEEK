#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME=$(basename "$0")
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/${SCRIPT_NAME%.sh}.log"
MODE="DRY_RUN"
MODEL_PATH_ARG=""
HOST="0.0.0.0"
PORT=8000
WORKERS=${MAX_WORKERS:-2}
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
WORKERS=${WORKERS:-2}
OMP_THREADS=${OMP_NUM_THREADS:-0}

RESULT_JSON=''
EXIT_CODE=0
MESSAGE="Server not started"

function usage() {
  cat <<USAGE
Usage: $SCRIPT_NAME [--mode=DRY_RUN|EXECUTE] [--model-path PATH] [--host HOST] [--port PORT]
                    [--workers N] [--python PYTHON_BIN]
Launches the FastAPI server backed by llama-cpp-python.
USAGE
}

function on_exit() {
  local code=$?
  if [[ $code -ne 0 ]]; then
    EXIT_CODE=$code
  fi
  if [[ -z $RESULT_JSON ]]; then
    RESULT_JSON=$(printf '{"success":false,"code":%d,"message":"%s","log_path":"%s"}' "$EXIT_CODE" "$MESSAGE" "$LOG_PATH")
  fi
  printf '%s\n' "$RESULT_JSON"
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --mode=*) MODE="${1#*=}" ;;
    --mode) MODE="$2"; shift ;;
    --model-path=*) MODEL_PATH_ARG="${1#*=}" ;;
    --model-path) MODEL_PATH_ARG="$2"; shift ;;
    --host=*) HOST="${1#*=}" ;;
    --host) HOST="$2"; shift ;;
    --port=*) PORT="${1#*=}" ;;
    --port) PORT="$2"; shift ;;
    --workers=*) WORKERS="${1#*=}" ;;
    --workers) WORKERS="$2"; shift ;;
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
  MESSAGE="Model path not provided"
  EXIT_CODE=66
  RESULT_JSON=$(printf '{"success":false,"code":%d,"message":"%s","log_path":"%s","errors":["Set MODEL_PATH or pass --model-path."]}' "$EXIT_CODE" "$MESSAGE" "$LOG_PATH")
  exit 66
fi

if [[ $MODE == "DRY_RUN" ]]; then
  echo "[DRY_RUN] MODEL_PATH=$MODEL_PATH MAX_WORKERS=$WORKERS OMP_NUM_THREADS=${OMP_THREADS} $PYTHON_BIN -m uvicorn src.main:create_app --factory --host $HOST --port $PORT --workers $WORKERS"
  RESULT_JSON=$(printf '{"success":true,"code":0,"message":"Server command prepared","log_path":"%s"}' "$LOG_PATH")
  exit 0
fi

if [[ ! -f $MODEL_PATH ]]; then
  MESSAGE="Model file not found at $MODEL_PATH"
  EXIT_CODE=66
  RESULT_JSON=$(printf '{"success":false,"code":%d,"message":"%s","log_path":"%s","errors":["Download model via scripts/download_model.sh"]}' "$EXIT_CODE" "$MESSAGE" "$LOG_PATH")
  exit 66
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  MESSAGE="Python interpreter not found"
  EXIT_CODE=69
  RESULT_JSON=$(printf '{"success":false,"code":%d,"message":"%s","log_path":"%s"}' "$EXIT_CODE" "$MESSAGE" "$LOG_PATH")
  exit 69
fi

export MODEL_PATH
export OMP_NUM_THREADS=${OMP_THREADS:-0}
export MAX_WORKERS=$WORKERS

COMMAND=($PYTHON_BIN -m uvicorn src.main:create_app --factory --host "$HOST" --port "$PORT" --workers "$WORKERS")

echo "Starting server with command: ${COMMAND[*]}"
if "${COMMAND[@]}"; then
  RESULT_JSON=$(printf '{"success":true,"code":0,"message":"Server stopped cleanly","log_path":"%s"}' "$LOG_PATH")
  EXIT_CODE=0
else
  EXIT_CODE=$?
  MESSAGE="Server exited with errors"
  RESULT_JSON=$(printf '{"success":false,"code":%d,"message":"%s","log_path":"%s"}' "$EXIT_CODE" "$MESSAGE" "$LOG_PATH")
  exit $EXIT_CODE
fi
