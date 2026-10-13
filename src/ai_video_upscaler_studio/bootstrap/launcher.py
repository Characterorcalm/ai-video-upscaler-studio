"""Qt desktop launcher for ai-video-upscaler-studio.

Single-instance via a named Windows mutex; if a second instance launches it
forwards the file path to the running instance over a local named pipe and
exits. Blocks on the Qt event loop.
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from ai_video_upscaler_studio.bootstrap.single_instance import SingleInstanceGuard
from ai_video_upscaler_studio.config.settings import AppSettings
from ai_video_upscaler_studio.handlers.qt.main_window import MainWindow
from ai_video_upscaler_studio.utils.logging import configure_logging


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="avus-studio", description="AI video upscaler studio")
    p.add_argument("media", nargs="?", help="video file to open on launch")
    p.add_argument("--cpu-only", action="store_true", help="force ONNX CPU execution provider")
    p.add_argument("--profile", default="balanced", help="upscale profile name")
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> NoReturn:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    settings = AppSettings.load(profile=args.profile, cpu_only=args.cpu_only)
    configure_logging(level=args.log_level, log_dir=settings.paths.log_dir)

    guard = SingleInstanceGuard("ai-video-upscaler-studio-v0.6")
    if not guard.acquire():
        guard.forward(args.media)
        raise SystemExit(0)

    QCoreApplication.setApplicationName("ai-video-upscaler-studio")
    QCoreApplication.setOrganizationName("avus")
    app = QApplication(sys.argv)
    window = MainWindow(settings=settings, guard=guard)
    if args.media:
        window.enqueue_media(args.media)
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()