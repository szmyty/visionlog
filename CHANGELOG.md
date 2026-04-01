# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
### Changed
### Fixed

## [0.1.1] - 2024-04-01

### Added

- Structured JSON logging via `structlog` and `loguru` backends.
- Ultra-fast JSON serialization using `orjson`.
- Pretty console output powered by `loguru`.
- `get_logger()` factory function for creating named loggers.
- Optional OpenTelemetry tracing integration (`visionlog[tracing]` extra).
- Optional device detection support (`visionlog[device]` extra).
- Command-line logging tool via `click`.
- `py.typed` marker file for PEP 561 compliance.
- MIT License.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` project documentation.

[Unreleased]: https://github.com/szmyty/visionlog/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/szmyty/visionlog/releases/tag/v0.1.1
