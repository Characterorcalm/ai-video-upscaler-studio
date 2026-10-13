"""Registry of available upscaler models, backed by a JSON manifest.

Reads ``models/engines/manifest.json`` (shipped with the repo) and merges with
any user-installed weights discovered under ``%LOCALAPPDATA%\\ai-video-upscaler-studio\\models\\weights``.
SHA-256 is verified against the manifest before a model is considered loadable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ai_video_upscaler_studio.config.paths import ResolvedPaths


@dataclass(slots=True, frozen=True)
class ModelEntry:
    model_id: str
    display_name: str
    scale: int
    arch: str
    filename: str
    sha256: str
    vram_estimate_mb: int


class ModelRegistry:
    def __init__(self, paths: ResolvedPaths, manifest: Path | None = None) -> None:
        self._paths = paths
        self._manifest = manifest or Path(__file__).parent.parent / "models" / "engines" / "manifest.json"
        self._entries: dict[str, ModelEntry] = {}
        self._reload()

    def _reload(self) -> None:
        raw = json.loads(self._manifest.read_text(encoding="utf-8"))
        self._entries = {e["model_id"]: ModelEntry(**e) for e in raw["models"]}

    def list(self) -> list[ModelEntry]:
        return sorted(self._entries.values(), key=lambda e: e.model_id)

    def get(self, model_id: str) -> ModelEntry:
        try:
            return self._entries[model_id]
        except KeyError as exc:
            raise KeyError(f"unknown model_id {model_id!r}; known: {sorted(self._entries)}") from exc

    def resolve_path(self, model_id: str) -> Path:
        entry = self.get(model_id)
        candidate = self._paths.weights_dir / entry.filename
        if not candidate.is_file():
            raise FileNotFoundError(f"weights missing for {model_id}: {candidate}")
        return candidate

    def verify(self, model_id: str) -> bool:
        entry = self.get(model_id)
        path = self.resolve_path(model_id)
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest() == entry.sha256