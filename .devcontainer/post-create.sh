#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

chmod +x "$REPO_ROOT"/scripts/*.sh

bash "$REPO_ROOT/scripts/install_conda_deps.sh" --mode=${MODE:-EXECUTE} || {
  echo "Conda installation failed inside devcontainer" >&2
  exit 1
}
