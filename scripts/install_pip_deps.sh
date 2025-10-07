#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME=$(basename "$0")
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/${SCRIPT_NAME%.sh}.log"

exec > >(tee -a "$LOG_PATH") 2>&1
trap 'on_exit $?' EXIT

MODE="DRY_RUN"
REQUIREMENTS_FILE="$REPO_ROOT/requirements.txt"
PYTHON_BIN="python3"

function usage() {
  cat <<USAGE
Usage: $SCRIPT_NAME [--mode=DRY_RUN|EXECUTE] [--python PYTHON_BIN]
Installs pip dependencies as a fallback when conda is unavailable.
USAGE
}

function on_exit() {
  local code=$1
  local success=false
  local message="Pip dependency installation failed"
  if [[ $code -eq 0 ]]; then
    success=true
    message="Pip dependency installation completed in $MODE mode"
  fi
  printf '{"success":%s,"code":%d,"message":"%s","log_path":"%s"}\n' \
    "$success" "$code" "$message" "$LOG_PATH"
}

function run_cmd() {
  local cmd=("$@")
  if [[ $MODE == "DRY_RUN" ]]; then
    echo "[DRY_RUN] ${cmd[*]}"
  else
    "${cmd[@]}"
  fi
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --mode=*)
      MODE="${1#*=}"
      ;;
    --mode)
      MODE="$2"
      shift
      ;;
    --python=*)
      PYTHON_BIN="${1#*=}"
      ;;
    --python)
      PYTHON_BIN="$2"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 64
      ;;
  esac
  shift
done

MODE=${MODE^^}
if [[ $MODE != "DRY_RUN" && $MODE != "EXECUTE" ]]; then
  echo "Invalid mode: $MODE" >&2
  exit 64
fi

if [[ ! -f $REQUIREMENTS_FILE ]]; then
  echo "requirements.txt not found at $REQUIREMENTS_FILE" >&2
  exit 66
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python interpreter not found: $PYTHON_BIN" >&2
  exit 69
fi

if command -v conda >/dev/null 2>&1; then
  echo "[WARN] Conda detected. Prefer scripts/install_conda_deps.sh when possible." >&2
fi

echo "Using python executable: $PYTHON_BIN"

IN_VENV=$("$PYTHON_BIN" - <<'PY'
import sys
print(int(sys.prefix != getattr(sys, "base_prefix", sys.prefix)))
PY
)

if [[ "$IN_VENV" != "1" ]]; then
  echo "[WARN] The selected Python interpreter is not in a virtual environment."
  echo "       Run 'python -m venv .venv' and rerun with --python ./.venv/bin/python (or Windows equivalent)."
fi

if [[ $MODE == "EXECUTE" ]]; then
  run_cmd "$PYTHON_BIN" -m pip install --upgrade pip
  run_cmd "$PYTHON_BIN" -m pip install --upgrade setuptools wheel
  run_cmd "$PYTHON_BIN" -m pip install -r "$REQUIREMENTS_FILE"
else
  echo "[DRY_RUN] $PYTHON_BIN -m pip install --upgrade pip"
  echo "[DRY_RUN] $PYTHON_BIN -m pip install --upgrade setuptools wheel"
  echo "[DRY_RUN] $PYTHON_BIN -m pip install -r $REQUIREMENTS_FILE"
fi

echo "Verify llama-cpp-python build compatibility if compilation fails."
