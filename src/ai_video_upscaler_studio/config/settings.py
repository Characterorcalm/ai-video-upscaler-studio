"""Application settings loaded from defaults, YAML profile, and env vars.

Env vars are prefixed ``AVUS_`` (e.g. ``AVUS_CUDA_DEVICE=1``). Profiles live
under ``config/profiles/*.yaml`` and override defaults; env vars override
profiles. ``--cpu-only`` collapses the whole thing to the CPU execution
provider regardless of YAML.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ai_video_upscaler_studio.config.paths import ResolvedPaths, resolve_paths


class ExecutionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AVUS_", extra="ignore")

    provider: Literal["cuda", "tensorrt", "directml", "cpu"] = "cuda"
    cuda_device: int = 0
    tile_size: int = Field(default=512, ge=64, le=2048)
    tile_overlap: int = Field(default=32, ge=0, le=128)
    fp16: bool = True
    max_vram_fraction: float = Field(default=0.85, gt=0.0, le=1.0)


class EncodeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AVUS_", extra="ignore")

    codec: Literal["h264_nvenc", "hevc_nvenc", "libx264", "libx265"] = "hevc_nvenc"
    crf: int = Field(default=17, ge=0, le=51)
    preset: str = "p5"
    audio: Literal["copy", "aac", "none"] = "copy"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AVUS_", extra="ignore")

    profile: str = "balanced"
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)
    encode: EncodeSettings = Field(default_factory=EncodeSettings)
    scale: Literal[2, 3, 4] = 4
    model_id: str = "realesrgan-x4plus"
    paths: ResolvedPaths = Field(default_factory=resolve_paths)

    @classmethod
    def load(cls, profile: str = "balanced", cpu_only: bool = False) -> "AppSettings":
        yaml_path = Path(__file__).parent / "profiles" / f"{profile}.yaml"
        base = cls(profile=profile)
        if yaml_path.is_file():
            base = _merge_yaml(base, yaml_path)
        if cpu_only:
            base.execution.provider = "cpu"
            base.execution.fp16 = False
        return base


def _merge_yaml(settings: "AppSettings", path: Path) -> "AppSettings":
    import yaml  # local import keeps yaml optional at runtime

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    merged = settings.model_dump()
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return AppSettings.model_validate(merged)