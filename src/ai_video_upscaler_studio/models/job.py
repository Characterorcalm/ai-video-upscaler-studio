"""Domain models for upscale jobs: source media, target, progress, result."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class JobState(str, Enum):
    QUEUED = "queued"
    PROBING = "probing"
    UPSCALING = "upscaling"
    ENCODING = "encoding"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaProbe(BaseModel):
    path: Path
    width: int
    height: int
    fps: float
    duration_s: float
    frame_count: int
    pix_fmt: str
    video_codec: str
    has_audio: bool


class UpscaleRequest(BaseModel):
    source: Path
    output: Path
    model_id: str = "realesrgan-x4plus"
    scale: int = Field(default=4, ge=2, le=4)
    tile_size: int = Field(default=512, ge=64, le=2048)
    tile_overlap: int = Field(default=32, ge=0, le=128)
    fp16: bool = True


class UpscaleProgress(BaseModel):
    job_id: str
    state: JobState = JobState.QUEUED
    frames_done: int = 0
    frames_total: int = 0
    fps_effective: float = 0.0
    eta_s: float = 0.0
    message: str = ""

    @property
    def percent(self) -> float:
        if self.frames_total <= 0:
            return 0.0
        return 100.0 * self.frames_done / self.frames_total


class UpscaleResult(BaseModel):
    job_id: str
    output: Path
    frames_written: int
    wall_time_s: float
    mean_fps: float
    encoder: str