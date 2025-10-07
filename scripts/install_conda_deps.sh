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
ENV_FILE="$REPO_ROOT/environment.yml"
ENV_NAME="localai"

function usage() {
  cat <<USAGE
Usage: $SCRIPT_NAME [--mode=DRY_RUN|EXECUTE] [--env-name NAME]
Creates or updates the conda environment defined in environment.yml.
USAGE
}

function on_exit() {
  local code=$1
  local success=false
  local message="Conda dependency installation failed"
  if [[ $code -eq 0 ]]; then
    success=true
    message="Conda dependency installation completed in $MODE mode"
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
    --env-name=*)
      ENV_NAME="${1#*=}"
      ;;
    --env-name)
      ENV_NAME="$2"
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

if [[ ! -f $ENV_FILE ]]; then
  echo "environment.yml not found at $ENV_FILE" >&2
  exit 66
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "conda executable not found. Install Miniconda or Mambaforge first." >&2
  exit 69
fi

run_cmd conda info
run_cmd conda env list

if [[ $MODE == "EXECUTE" ]]; then
  run_cmd conda env update -n "$ENV_NAME" -f "$ENV_FILE" --prune
else
  echo "[DRY_RUN] conda env update -n $ENV_NAME -f $ENV_FILE --prune"
fi

if [[ $MODE == "EXECUTE" ]]; then
  run_cmd conda run -n "$ENV_NAME" python -c "import sys; print(sys.version)"
else
  echo "[DRY_RUN] conda run -n $ENV_NAME python -c 'import sys; print(sys.version)'"
fi
