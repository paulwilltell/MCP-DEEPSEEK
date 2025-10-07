#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME=$(basename "$0")
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/${SCRIPT_NAME%.sh}.log"
MODE="DRY_RUN"
MODEL_ID=""
MODEL_URL=""
MODEL_FILENAME=""
DEST_DIR="$REPO_ROOT/models"
EXPECTED_SHA=""
FORCE_TOKEN=false

exec > >(tee -a "$LOG_PATH") 2>&1
trap 'on_exit $?' EXIT

function usage() {
  cat <<USAGE
Usage: $SCRIPT_NAME [--mode=DRY_RUN|EXECUTE] [--model-id ID --filename FILE] [--model-url URL] [--sha256 HASH]
Options:
  --mode             Run mode (default DRY_RUN)
  --model-id         Hugging Face model repository id (e.g. TheBloke/Mistral-7B-Instruct-GGUF)
  --filename         File inside the model repo to download (required with --model-id)
  --model-url        Direct download URL for the model file
  --sha256           Expected SHA256 checksum for verification
  --dest             Destination directory (default ./models)
  --force-token      Allow --token argument (otherwise refused)
  --token            Explicit Hugging Face token (discouraged)
USAGE
}

function on_exit() {
  local code=$1
  local success=false
  local message="Model download failed"
  if [[ $code -eq 0 ]]; then
    success=true
    message="Model download completed in $MODE mode"
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

if [[ -f $REPO_ROOT/.env ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$REPO_ROOT/.env"
  set +a
fi

HF_TOKEN=${HF_TOKEN:-""}

while [[ $# -gt 0 ]]; do
  case $1 in
    --mode=*) MODE="${1#*=}" ;;
    --mode) MODE="$2"; shift ;;
    --model-id=*) MODEL_ID="${1#*=}" ;;
    --model-id) MODEL_ID="$2"; shift ;;
    --filename=*) MODEL_FILENAME="${1#*=}" ;;
    --filename) MODEL_FILENAME="$2"; shift ;;
    --model-url=*) MODEL_URL="${1#*=}" ;;
    --model-url) MODEL_URL="$2"; shift ;;
    --sha256=*) EXPECTED_SHA="${1#*=}" ;;
    --sha256) EXPECTED_SHA="$2"; shift ;;
    --dest=*) DEST_DIR="${1#*=}" ;;
    --dest) DEST_DIR="$2"; shift ;;
    --force-token) FORCE_TOKEN=true ;;
    --token=*)
      if [[ $FORCE_TOKEN != true ]]; then
        echo "Refusing to accept token via CLI without --force-token" >&2
        exit 63
      fi
      HF_TOKEN="${1#*=}"
      ;;
    --token)
      if [[ $FORCE_TOKEN != true ]]; then
        echo "Refusing to accept token via CLI without --force-token" >&2
        exit 63
      fi
      HF_TOKEN="$2"
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

mkdir -p "$DEST_DIR"
DEST_DIR=$(cd "$DEST_DIR" && pwd)

# Disk space check (>20GB)
AVAIL_KB=$(df -Pk "$DEST_DIR" | tail -1 | awk '{print $4}')
REQUIRED_KB=$((20 * 1024 * 1024))
if (( AVAIL_KB < REQUIRED_KB )); then
  echo "Insufficient disk space in $DEST_DIR. Require at least 20GB free." >&2
  exit 70
fi

declare -a download_cmd
TARGET_PATH=""

if [[ -n $MODEL_ID ]]; then
  if [[ -n $MODEL_URL ]]; then
    echo "Use either --model-id or --model-url, not both" >&2
    exit 64
  fi
  if [[ -z $MODEL_FILENAME ]]; then
    echo "--filename is required when using --model-id" >&2
    exit 64
  fi
  TARGET_PATH="$DEST_DIR/$MODEL_FILENAME"
  download_cmd=(huggingface-cli download "$MODEL_ID" "$MODEL_FILENAME" --local-dir "$DEST_DIR" --local-dir-use-symlinks False)
  if [[ -n $HF_TOKEN ]]; then
    download_cmd+=(--token "$HF_TOKEN")
  else
    echo "HF_TOKEN is not set. If the model requires authentication, export HF_TOKEN before running." >&2
  fi
elif [[ -n $MODEL_URL ]]; then
  TARGET_PATH="$DEST_DIR/$(basename "$MODEL_URL")"
  download_cmd=(curl -L "$MODEL_URL" -o "$TARGET_PATH")
  if [[ -n $HF_TOKEN ]]; then
    download_cmd=(curl -H "Authorization: Bearer $HF_TOKEN" -L "$MODEL_URL" -o "$TARGET_PATH")
  fi
else
  echo "Either --model-id or --model-url must be specified" >&2
  exit 64
fi

if [[ $MODE == "DRY_RUN" ]]; then
  echo "[DRY_RUN] ${download_cmd[*]}"
else
  if ! command -v "${download_cmd[0]}" >/dev/null 2>&1; then
    echo "Downloader command not found: ${download_cmd[0]}" >&2
    exit 68
  fi
  run_cmd "${download_cmd[@]}"
fi

if [[ -n $EXPECTED_SHA ]]; then
  if [[ $MODE == "DRY_RUN" ]]; then
    echo "[DRY_RUN] sha256sum $TARGET_PATH"
  else
    actual_sha=$(sha256sum "$TARGET_PATH" | awk '{print $1}')
    if [[ "$actual_sha" != "$EXPECTED_SHA" ]]; then
      echo "SHA256 mismatch: expected $EXPECTED_SHA, got $actual_sha" >&2
      exit 65
    fi
    echo "SHA256 verified: $actual_sha"
  fi
fi

echo "Model prepared at $TARGET_PATH"
