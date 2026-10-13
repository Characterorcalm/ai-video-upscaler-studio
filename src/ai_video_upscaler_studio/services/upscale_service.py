"""The upscale service — orchestrates probe -> decode -> infer -> encode.

This is the fat service. Handlers call ``run(request, progress_cb, cancel)``
and get back an ``UpscaleResult``. All heavy lifting lives here or in the
adapters it composes; handlers stay thin.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import numpy as np

from ai_video_upscaler_studio.adapters.ffmpeg_io import FfmpegReader, FfmpegWriter
from ai_video_upscaler_studio.config.settings import AppSettings
from ai_video_upscaler_studio.models.engines.onnx_engine import OnnxEngine, OnnxEngineConfig
from ai_video_upscaler_studio.models.job import (
    JobState,
    UpscaleProgress,
    UpscaleRequest,
    UpscaleResult,
)
from ai_video_upscaler_studio.services.model_registry import ModelRegistry

log = logging.getLogger(__name__)
ProgressCb = Callable[[UpscaleProgress], None]
CancelCb = Callable[[], bool]


class UpscaleService:
    def __init__(self, settings: AppSettings, registry: ModelRegistry) -> None:
        self._settings = settings
        self._registry = registry
        self._engine: OnnxEngine | None = None

    def _ensure_engine(self, model_id: str) -> OnnxEngine:
        if self._engine is not None:
            return self._engine
        entry = self._registry.get(model_id)
        cfg = OnnxEngineConfig(
            model_path=self._registry.resolve_path(model_id),
            provider=self._settings.execution.provider,
            device_id=self._settings.execution.cuda_device,
            fp16=self._settings.execution.fp16,
            tile_size=self._settings.execution.tile_size,
            tile_overlap=self._settings.execution.tile_overlap,
        )
        self._engine = OnnxEngine(cfg)
        if self._engine.scale != entry.scale:
            raise RuntimeError(f"engine scale {self._engine.scale} != manifest scale {entry.scale}")
        return self._engine

    def run(
        self,
        request: UpscaleRequest,
        progress_cb: ProgressCb | None = None,
        cancel_cb: CancelCb | None = None,
    ) -> UpscaleResult:
        job_id = uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        engine = self._ensure_engine(request.model_id)
        emit = progress_cb or (lambda _p: None)
        cancelled = cancel_cb or (lambda: False)

        with FfmpegReader(request.source) as reader, FfmpegWriter(
            request.output, reader.probe, self._settings.encode
        ) as writer:
            total = reader.probe.frame_count or 1
            emit(UpscaleProgress(job_id=job_id, state=JobState.UPSCALING, frames_total=total))
            written = 0
            for idx, frame in enumerate(reader.frames()):
                if cancelled():
                    emit(UpscaleProgress(job_id=job_id, state=JobState.CANCELLED, frames_done=written))
                    return UpscaleResult(
                        job_id=job_id, output=request.output, frames_written=written,
                        wall_time_s=time.perf_counter() - t0, mean_fps=0.0, encoder=writer.encoder_name,
                    )
                upscaled = engine.infer(frame.astype(np.float32) / 255.0) * 255.0
                writer.write(upscaled.astype(np.uint8))
                written += 1
                if idx % 8 == 0:
                    elapsed = time.perf_counter() - t0
                    emit(UpscaleProgress(
                        job_id=job_id, state=JobState.UPSCALING, frames_done=written,
                        frames_total=total, fps_effective=written / max(elapsed, 1e-6),
                        eta_s=(total - written) / max(written / max(elapsed, 1e-6), 1e-6),
                    ))
            emit(UpscaleProgress(job_id=job_id, state=JobState.DONE, frames_done=written, frames_total=total))

        wall = time.perf_counter() - t0
        return UpscaleResult(
            job_id=job_id, output=request.output, frames_written=written,
            wall_time_s=wall, mean_fps=written / max(wall, 1e-6), encoder=self._settings.encode.codec,
        )


def default_output_path(source: Path, scale: int) -> Path:
    stem = source.with_suffix("").name
    return source.with_name(f"{stem}_x{scale}_upscaled.mp4")
</｜｜DSML｜｜ parameter>
</｜｜DSML｜｜ invoke>
</｜｜DSML｜｜ calls>