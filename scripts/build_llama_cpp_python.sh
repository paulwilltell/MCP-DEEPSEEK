#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME=$(basename "$0")
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/${SCRIPT_NAME%.sh}.log"
MODE="DRY_RUN"
CLONE_DIR="$REPO_ROOT/third_party/llama.cpp"
FORCE_REBUILD=false
NO_BUILD=false
PYTHON_BIN="python3"
LLAMA_CPP_PY_VERSION="0.2.56"

exec > >(tee -a "$LOG_PATH") 2>&1
trap 'on_exit $?' EXIT

function usage() {
  cat <<USAGE
Usage: $SCRIPT_NAME [--mode=DRY_RUN|EXECUTE] [--clone-dir PATH] [--force-rebuild] [--no-build]
Builds llama.cpp and installs llama-cpp-python with CPU optimizations.
USAGE
}

function on_exit() {
  local code=$1
  local success=false
  local message="llama-cpp-python build failed"
  if [[ $code -eq 0 ]]; then
    success=true
    message="llama-cpp-python build completed in $MODE mode"
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
    --mode=*) MODE="${1#*=}" ;;
    --mode) MODE="$2"; shift ;;
    --clone-dir=*) CLONE_DIR="${1#*=}" ;;
    --clone-dir) CLONE_DIR="$2"; shift ;;
    --force-rebuild) FORCE_REBUILD=true ;;
    --no-build) NO_BUILD=true ;;
    --python=*) PYTHON_BIN="${1#*=}" ;;
    --python) PYTHON_BIN="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 64 ;;
  esac
  shift
done

MODE=${MODE^^}
if [[ $MODE != "DRY_RUN" && $MODE != "EXECUTE" ]]; then
  echo "Invalid mode: $MODE" >&2
  exit 64
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python interpreter not found: $PYTHON_BIN" >&2
  exit 69
fi

if [[ $NO_BUILD == true ]]; then
  echo "Skipping native build; installing prebuilt wheel."
  if [[ $MODE == "EXECUTE" ]]; then
    run_cmd "$PYTHON_BIN" -m pip install --upgrade pip
    run_cmd "$PYTHON_BIN" -m pip install "llama-cpp-python==${LLAMA_CPP_PY_VERSION}"
  else
    echo "[DRY_RUN] $PYTHON_BIN -m pip install --upgrade pip"
    echo "[DRY_RUN] $PYTHON_BIN -m pip install llama-cpp-python==${LLAMA_CPP_PY_VERSION}"
  fi
  exit 0
fi

if ! command -v cmake >/dev/null 2>&1; then
  echo "cmake is required. Install via apt: sudo apt-get install cmake" >&2
  exit 67
fi

if ! command -v make >/dev/null 2>&1; then
  echo "build-essential tools missing. Install via apt: sudo apt-get install build-essential" >&2
  exit 67
fi

ABS_CLONE_DIR=$(python -c "from pathlib import Path; import sys; print(Path(sys.argv[1]).expanduser().absolute())" "$CLONE_DIR")
CLONE_DIR="$ABS_CLONE_DIR"
PARENT_DIR=$(dirname "$CLONE_DIR")
mkdir -p "$PARENT_DIR"

if [[ $FORCE_REBUILD == true && $MODE == "EXECUTE" ]]; then
  echo "Removing existing clone at $CLONE_DIR"
  run_cmd rm -rf "$CLONE_DIR"
fi

if [[ ! -d $CLONE_DIR ]]; then
  if [[ $MODE == "EXECUTE" ]]; then
    run_cmd git clone https://github.com/ggerganov/llama.cpp.git "$CLONE_DIR"
  else
    echo "[DRY_RUN] git clone https://github.com/ggerganov/llama.cpp.git $CLONE_DIR"
  fi
else
  if [[ $MODE == "EXECUTE" ]]; then
    run_cmd git -C "$CLONE_DIR" pull --ff-only
  else
    echo "[DRY_RUN] git -C $CLONE_DIR pull --ff-only"
  fi
fi

if [[ $MODE == "EXECUTE" ]]; then
  run_cmd "$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
  run_cmd cmake -S "$CLONE_DIR" -B "$CLONE_DIR/build" -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS
  run_cmd cmake --build "$CLONE_DIR/build" --config Release -j "$(nproc)"
  export CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
  export LLAMA_CPP_PYTHON_BUILD_CMAKE=1
  run_cmd "$PYTHON_BIN" -m pip install --force-reinstall --no-cache-dir --verbose "llama-cpp-python==${LLAMA_CPP_PY_VERSION}"
else
  echo "[DRY_RUN] $PYTHON_BIN -m pip install --upgrade pip setuptools wheel"
  echo "[DRY_RUN] cmake -S $CLONE_DIR -B $CLONE_DIR/build -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
  echo "[DRY_RUN] cmake --build $CLONE_DIR/build --config Release -j $(nproc)"
  echo "[DRY_RUN] CMAKE_ARGS='-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS' LLAMA_CPP_PYTHON_BUILD_CMAKE=1 $PYTHON_BIN -m pip install --force-reinstall --no-cache-dir --verbose llama-cpp-python==${LLAMA_CPP_PY_VERSION}"
fi

echo "If the build fails due to insufficient memory, reduce parallelism with: cmake --build ... -j 2"
