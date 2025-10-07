# personal-local-ai

A deterministic, CPU-optimized personal AI workspace for Windows 11 hosts using WSL2 (Ubuntu 22.04) or VS Code devcontainers. The project focuses on lightweight quantized models via [llama.cpp](https://github.com/ggerganov/llama.cpp), `llama-cpp-python`, and ONNX/OpenVINO inference paths while remaining AGPL-3.0 compliant.

## Hardware & Platform Assumptions
- Host: Windows 11 Pro with WSL2 (Ubuntu 22.04) or VS Code Remote Containers.
- CPU: Intel 12th Gen i3 with Intel integrated GPU (CPU inference path expected).
- RAM: 16 GB minimum.
- Disk: Allocate at least 50 GB free on an NTFS drive mounted into WSL (e.g., `/mnt/d/ai-models`). Use bind mounts rather than copying models into the repo.
- No CUDA/NVIDIA dependencies.

## Repository Layout
```
personal-local-ai/
├─ .devcontainer/
│  ├─ devcontainer.json
│  └─ post-create.sh
├─ scripts/
│  ├─ install_conda_deps.sh
│  ├─ install_pip_deps.sh
│  ├─ download_model.sh
│  ├─ build_llama_cpp_python.sh
│  ├─ smoke_test.sh
│  └─ run_server.sh
├─ src/
│  └─ main.py
├─ tests/
│  └─ verify_installation.py
├─ Dockerfile
├─ README.md
├─ requirements.txt
├─ environment.yml
├─ .gitignore
├─ .env.example
├─ LICENSE (AGPL-3.0)
└─ models/ (ignored)
```

## Quick Start

### Windows 11 (PowerShell) using `python -m venv`
1. Install [Python 3.11](https://www.python.org/downloads/windows/) and ensure "Add python.exe to PATH" is checked.
2. Clone the repository and create an isolated virtual environment:
   ```powershell
   git clone https://github.com/paulwilltell/personal-local-ai.git
   cd personal-local-ai
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies (dry run optional):
   ```powershell
   # Optional preview
   bash scripts/install_pip_deps.sh --mode=DRY_RUN --python .\.venv\Scripts\python.exe
   # Execute installation inside the venv
   bash scripts/install_pip_deps.sh --mode=EXECUTE --python .\.venv\Scripts\python.exe
   ```
4. Place a quantized `.gguf` model under `models\` (or another folder) and set an absolute `MODEL_PATH`.
   ```powershell
   copy D:\ai-models\mistral.gguf models\
   $Env:MODEL_PATH = (Resolve-Path models\mistral.gguf)
   ```
5. Run a single prompt or launch the server:
   ```powershell
   .\.venv\Scripts\python.exe src\main.py --model-path $Env:MODEL_PATH --json
   bash scripts\run_server.sh --mode=EXECUTE --model-path $Env:MODEL_PATH
   ```

### WSL2 / Ubuntu 22.04 (Conda-first)
1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Mambaforge](https://github.com/conda-forge/miniforge/releases).
2. Clone the repository:
   ```bash
   git clone https://github.com/paulwilltell/personal-local-ai.git
   cd personal-local-ai
   ```

## Conda-First Installation
1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Mambaforge](https://github.com/conda-forge/miniforge/releases) inside WSL2.
2. Clone the repository:
   ```bash
   git clone https://github.com/paulwilltell/personal-local-ai.git
   cd personal-local-ai
   ```
3. Create the environment (dry run first):
   ```bash
   chmod +x scripts/*.sh
   bash scripts/install_conda_deps.sh --mode=DRY_RUN
   bash scripts/install_conda_deps.sh --mode=EXECUTE
   ```
4. (Optional) If conda is unavailable, fall back to pip:
   ```bash
   bash scripts/install_pip_deps.sh --mode=DRY_RUN --python python3
   bash scripts/install_pip_deps.sh --mode=EXECUTE --python python3
   ```

## Building `llama-cpp-python`
The `llama-cpp-python` wheel is compiled from source for CPU acceleration:
```bash
bash scripts/build_llama_cpp_python.sh --mode=DRY_RUN
bash scripts/build_llama_cpp_python.sh --mode=EXECUTE --force-rebuild
```
- `--force-rebuild` forces a fresh clone/rebuild of llama.cpp.
- `--no-build` installs the prebuilt wheel when compatible (not recommended on WSL CPU-only).

## Model Download Workflow
- Models are **not** bundled. Use quantized `.gguf` files optimized for CPU (e.g., 4-bit 7B models).
- Provide credentials via environment variable or `.env` file:
  ```bash
  export HF_TOKEN="<YOUR_HUGGINGFACE_TOKEN>"
  # or copy .env.example to .env and populate HF_TOKEN and MODEL_ID/MODEL_URL
  ```
- Run the download helper:
  ```bash
  bash scripts/download_model.sh --mode=DRY_RUN --model-id <HF_MODEL_ID>
  bash scripts/download_model.sh --mode=EXECUTE --model-id <HF_MODEL_ID>
  ```
- To use a direct URL instead:
  ```bash
  bash scripts/download_model.sh --mode=EXECUTE --model-url <DIRECT_URL>
  ```
- Models are saved under `./models` (git-ignored). Ensure the target filesystem has >20 GB free.
- After the download, point `MODEL_PATH` to the absolute location of the `.gguf` file (e.g., `/mnt/d/ai-models/model.gguf`).

## Smoke Test & Validation
After installing dependencies and downloading a model:
```bash
bash scripts/smoke_test.sh --mode=EXECUTE --model-path ./models/<model>.gguf
python tests/verify_installation.py
```
- `smoke_test.sh` reports latency and sample text as JSON.
- `tests/verify_installation.py` prints JSON with success flag and details. It exits with status 66 if no model is available.

### Missing Model or MODEL_PATH Errors
If the CLI or server complains that `MODEL_PATH` is missing or the file does not exist:
1. Ensure dependencies are installed (activate your environment and rerun `bash scripts/install_conda_deps.sh --mode=EXECUTE` or `bash scripts/install_pip_deps.sh --mode=EXECUTE`).
2. Download or copy a quantized `.gguf` model into `models/` (or another folder) and capture the **absolute** path to the file.
3. Set `MODEL_PATH` to that absolute path (e.g., PowerShell: `$Env:MODEL_PATH = (Resolve-Path models\mistral.gguf)` or Bash: `export MODEL_PATH="/mnt/d/ai-models/mistral.gguf"`).
4. Re-run the command, explicitly passing `--model-path` if desired, for example:
   - PowerShell: `.\.venv\Scripts\python.exe src\main.py --model-path C:\\path\\to\\model.gguf`
   - Bash: `bash scripts/run_server.sh --mode=EXECUTE --model-path /mnt/d/ai-models/model.gguf`

Both `src/main.py` and `scripts/run_server.sh` validate that the path exists before starting, so the command will continue once the file is in place.

## Running the Local API Server
```bash
bash scripts/run_server.sh --mode=EXECUTE --model-path ./models/<model>.gguf
```
- Launches a FastAPI app (see `src/main.py`) exposing `POST /generate`.
- Control worker parallelism via environment variables:
  - `OMP_NUM_THREADS` (default: number of physical cores)
  - `MAX_WORKERS` (default: 2)
- Use DRY_RUN to preview commands without execution.

## Devcontainer Usage
1. Install the VS Code Dev Containers extension.
2. Open the repository in VS Code and select **Reopen in Container**.
3. The `post-create.sh` script automatically runs `install_conda_deps.sh --mode=EXECUTE` inside the container (customizable).

## Environment Variables (.env)
- Copy `.env.example` to `.env` and set:
  - `HF_TOKEN` (never commit actual tokens).
  - `MODEL_ID` or `MODEL_URL` for preferred model.
  - `MODEL_PATH` default for server/smoke tests.
- Scripts read `.env` when present but never log secret values.

## Licensing Notice (AGPL-3.0)
This project is licensed under the [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.en.html). Operating this software as a network service may trigger AGPL obligations to provide the corresponding source code to all remote users. Consult legal counsel before deploying in production.

## Maintenance Checklist
- Keep dependencies updated with conda (`mamba env update -f environment.yml`).
- Periodically re-run `smoke_test.sh` after updates.
- Store large model files on mounted drives to conserve WSL filesystem space.

## Support
Please open issues or pull requests under the repository `paulwilltell/personal-local-ai` with detailed logs (found under `./logs`).
