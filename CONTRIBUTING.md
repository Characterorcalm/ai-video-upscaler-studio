# Contributing to ai-video-upscaler-studio

Thanks for wanting to help ship the tater's favourite upscaler. This project
targets **Windows 10/11 x64** with Python 3.11/3.12. The GPU path is CUDA 12.4
via `onnxruntime-gpu`; CPU path (`onnxruntime`) is supported but ~40x slower.

## Repo layout

```
src/ai_video_upscaler_studio/
  bootstrap/     entry points (CLI, Qt launcher, single-instance guard)
  core/          frame pipeline, tile scheduler, colour pipeline
  services/      business logic — upscale, encode, model registry, job queue
  handlers/      thin controllers: CLI commands, Qt slots, IPC messages
  models/        pydantic domain models + ONNX/TensorRT engine wrappers
  adapters/      platform adapters — CUDA, DirectML, CPU, ffmpeg, NVENC
  utils/         logging, paths, ffprobe parsing, timing
  config/        pydantic-settings, YAML profile loader
```

## Dev setup

```powershell
git clone https://github.com/ai-video-upscaler-studio/ai-video-upscaler-studio
cd ai-video-upscaler-studio
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m ai_video_upscaler_studio.bootstrap.launcher --cpu-only   # smoke test
```

For TensorRT engines: `pip install -e ".[tensorrt]"` and export engines
with `avus models export --engine tensorrt --model realesrgan-x4plus`.

## Style

- `ruff format` + `ruff check` must pass. Line length 110.
- Type hints mandatory on public APIs. `mypy --strict` on `services/` and `models/`.
- No blocking calls in Qt slots — push to `services.job_queue`.
- Logging via `structlog`, never `print()` outside `bootstrap/`.

## Tests

```powershell
pytest -m "not gpu and not slow"     # CI gate
pytest -m gpu                        # local, needs CUDA
```

New upscaler backends need: (1) an engine wrapper in `models/engines/`,
(2) a registration in `services/model_registry.py`, (3) a golden-frame
test in `tests/test_upscale_pipeline.py`.

## Pull requests

- One logical change per PR. Squash on merge.
- Reference the issue number. Attach a 5s before/after clip for visual changes.
- Do not commit weights, engines, or licence-restricted sample footage.

## Community

Issues and PRs are the only channels. No Discord, no DMs — keeps the audit
trail on the tracker.