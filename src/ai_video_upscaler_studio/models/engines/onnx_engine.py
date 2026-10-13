"""ONNX Runtime engine wrapper (CUDA / DirectML / CPU execution providers).

Loads a validated ONNX graph, exposes a tiled ``infer(batch) -> batch`` call,
and enforces a VRAM budget via a sliding window so 4K frames on 8GB cards
don't OOM. Thread-affine: one instance per GPU worker thread.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort

log = logging.getLogger(__name__)
_VALID_PROVIDERS = {"cuda": "CUDAExecutionProvider", "directml": "DmlExecutionProvider", "cpu": "CPUExecutionProvider"}


@dataclass(slots=True)
class OnnxEngineConfig:
    model_path: Path
    provider: str = "cuda"
    device_id: int = 0
    fp16: bool = True
    tile_size: int = 512
    tile_overlap: int = 32


class OnnxEngine:
    """Tiled super-resolution engine over an ONNX graph.

    Inputs:  NCHW float32 in [0,1], shape (N, 3, H, W).
    Outputs: NCHW float32 in [0,1], shape (N, 3, H*scale, W*scale).
    Raises ``ValueError`` on shape mismatch, ``RuntimeError`` on provider failure.
    """

    def __init__(self, cfg: OnnxEngineConfig) -> None:
        if cfg.provider not in _VALID_PROVIDERS:
            raise ValueError(f"unknown provider {cfg.provider!r}")
        onnx.checker.check_model(str(cfg.model_path))  # untrusted-file gate
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = 1  # one thread per worker; we scale out, not up
        self._session = ort.InferenceSession(
            str(cfg.model_path),
            sess_options=opts,
            providers=[(_VALID_PROVIDERS[cfg.provider], {"device_id": cfg.device_id})],
        )
        self._input_name = self._session.get_inputs()[0].name
        self._scale = _infer_scale(self._session)
        self._cfg = cfg
        log.info("onnx.engine.ready", extra={"model": cfg.model_path.name, "scale": self._scale})

    @property
    def scale(self) -> int:
        return self._scale

    def infer(self, frame: np.ndarray) -> np.ndarray:
        """Upscale a single HWC float32 frame in [0,1]. Tiles internally."""
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(f"expected HWC RGB, got {frame.shape}")
        h, w, _ = frame.shape
        out = np.empty((h * self._scale, w * self._scale, 3), dtype=np.float32)
        step = self._cfg.tile_size - self._cfg.tile_overlap
        for y in range(0, h, step):
            for x in range(0, w, step):
                tile = frame[y : y + self._cfg.tile_size, x : x + self._cfg.tile_size]
                nchw = tile.transpose(2, 0, 1)[None, ...]
                res = self._session.run(None, {self._input_name: nchw})[0][0]
                up = res.transpose(1, 2, 0)
                oy, ox = y * self._scale, x * self._scale
                out[oy : oy + up.shape[0], ox : ox + up.shape[1]] = up
        return np.clip(out, 0.0, 1.0)


def _infer_scale(session: ort.InferenceSession) -> int:
    shape = session.get_outputs()[0].shape
    try:
        return int(shape[-1]) // int(session.get_inputs()[0].shape[-1])
    except (TypeError, ZeroDivisionError):
        return 4  # dynamic axes — assume x4