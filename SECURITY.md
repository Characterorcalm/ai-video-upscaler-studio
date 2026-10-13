# Security Policy — ai-video-upscaler-studio

## Scope

This repo ships a Windows desktop application that runs **untrusted model
files** (`.onnx`, `.engine`, `.pth`) and **untrusted media** (arbitrary
`.mp4`/`.mkv`/`.mov`). Both are attack surface. The threat model:

- Malicious ONNX graph triggering arbitrary file read during `onnx.checker`.
- Malicious media exploiting the bundled `ffmpeg`/`libav` decoder.
- Model files planted in a shared `models/weights/` directory.
- Plugin-style "custom engine" DLLs dropped into `adapters/native/`.

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.6.x   | yes       |
| 0.5.x   | security backports only |
| ≤ 0.4   | no        |

## Reporting a vulnerability

Email `security@ai-video-upscaler-studio.dev` (PGP key `0xAVUS2026` on
keys.openpgp.org). Include: affected version, a minimal repro (media file or
ONNX graph), and the platform (`win-x64-cuda` / `win-x64-dml` / `win-x64-cpu`).

We acknowledge within 72h, patch critical issues within 14 days, and credit
reporters in `CHANGELOG.md` unless you ask otherwise.

## Hardening already in place

- ONNX models are parsed with `onnx.checker.check_model` before `InferenceSession` is created.
- `ffmpeg` is invoked with `-nostdin -hide_banner` and a fixed argument vector — no shell interpolation.
- Engine loading is allow-listed by SHA-256 in `models/engines/manifest.json`.
- The Qt launcher runs with `QT_ENABLE_HIGHDPI_SCALING=1` and never loads remote URLs.

## Out of scope

- System-wide GPU driver vulnerabilities (report to NVIDIA/AMD).
- DRM-protected media decryption — we don't do it, don't ask.
- Findings that require the user to already have local admin on their own box.