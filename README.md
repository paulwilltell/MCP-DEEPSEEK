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
   bash scripts/install_pip_deps.sh --mode=DRY_RUN
   bash scripts/install_pip_deps.sh --mode=EXECUTE
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

## Smoke Test & Validation
After installing dependencies and downloading a model:
```bash
bash scripts/smoke_test.sh --mode=EXECUTE --model-path ./models/<model>.gguf
python tests/verify_installation.py
```
- `smoke_test.sh` reports latency and sample text as JSON.
- `tests/verify_installation.py` prints JSON with success flag and details. It exits with status 66 if no model is available.

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
