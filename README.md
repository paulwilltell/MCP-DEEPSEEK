# MCP-DEEPSEEK

This repository provides a reference implementation for the RMH stack, including:

- **rmh_io** – sensor data plane with synthetic drivers, streaming, and Parquet logging.
- **rmh_operator** – Fourier Neural Operator training utilities and CLI (`rmh_fit`).
- **rmh_inverse** – Physics-informed inverse solver with Maxwell constraints and MC-dropout uncertainty.
- **rmh_viz** – FastAPI backend plus a React/Three.js front-end scaffold for 3D overlays.
- **rmh_cal** – Calibration routines producing reports consumed by the stack.
- **rmh_core** – Shared physics and loss utilities.

Run the unit tests with:

```bash
pytest
```
