"""Windows-aware path resolution for cache, weights, logs, and temp frames."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel


class ResolvedPaths(BaseModel):
    model_config = {"frozen": True}

    root: Path
    weights_dir: Path
    cache_dir: Path
    log_dir: Path
    frames_tmp: Path
    render_out: Path


def resolve_paths() -> ResolvedPaths:
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    root = Path(os.environ.get("AVUS_HOME", local / "ai-video-upscaler-studio"))
    return ResolvedPaths(
        root=root,
        weights_dir=root / "models" / "weights",
        cache_dir=root / "cache",
        log_dir=root / "logs",
        frames_tmp=root / "temp" / "frames",
        render_out=root / "render_out",
    )


def ensure_dirs(paths: ResolvedPaths) -> None:
    for p in (paths.weights_dir, paths.cache_dir, paths.log_dir, paths.frames_tmp, paths.render_out):
        p.mkdir(parents=True, exist_ok=True)