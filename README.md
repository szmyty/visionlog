# Visionlog 🚀

A high-performance, structured logging library for analytics tracking.

## Features

- 🚀 **Structured JSON Logging**
- 🔎 **Easy Integration with OpenTelemetry**
- 🎨 **Pretty Console Output with Loguru**
- ⚡ **Ultra-Fast JSON Serialization using orjson**
- 🛠 **Command-Line Logging Tool**

## Installation

### **Install via pip**

```sh
pip install visionlog
```

### **Install via Poetry**

```sh
poetry add visionlog
```

### **Install with OpenTelemetry tracing support**

```sh
pip install visionlog[tracing]
# or
poetry add visionlog --extras tracing
```

### **Install with device detection support**

```sh
pip install visionlog[device]
# or
poetry add visionlog --extras device
```

---

## 🚀 **Usage**

### **1. Basic Example**

```python
from visionlog import get_logger

logger = get_logger("my-app")

logger.info("User login event", user="john_doe", action="login")
logger.warning("Suspicious activity detected", ip="192.168.1.1")
logger.error("Server crashed!", error_code=500)
```

### **2. Config-Based Usage**

Group all logger options into a reusable `LoggerConfig` object and pass it to `get_logger`:

```python
from visionlog import get_logger, LoggerConfig

config = LoggerConfig(
    service_name="my-app",
    user_id="user_42",
    session_id="sess_001",
    environment="production",
)

logger = get_logger(config=config)

logger.info("User login event", action="login")
```

`LoggerConfig` supports the same options as the individual keyword arguments.  Keyword arguments are still fully supported when `config` is not provided.

### **3. CLI Usage**

You can also log messages directly from the command line:

```sh
visionlog-cli --message "Quick log example"
```

---

## 🎯 **Advanced Usage**

### **Using Visionlog with OpenTelemetry**

Install the tracing extra first:

```sh
pip install visionlog[tracing]
```

Enable tracing when creating your logger.  
Visionlog will automatically inject `trace_id` and `span_id` into every log record emitted inside an active span:

```python
from visionlog import get_logger
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

# Configure the OTel SDK (use your preferred exporter in production)
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer("my-app")

logger = get_logger("my-app", enable_tracing=True)

with tracer.start_as_current_span("http_request"):
    # trace_id and span_id are added automatically
    logger.info("Tracking request event", endpoint="/api/data", status=200)
```

When no span is active the `trace_id`/`span_id` fields are simply omitted, so the
logger works identically to the non-tracing configuration.  
The `opentelemetry-api` and `opentelemetry-sdk` packages are **optional** — if they
are not installed, `enable_tracing=True` is silently ignored.

---

## 🔐 Privacy Considerations

visionlog can enrich logs with IP, geo, and device metadata.

These may be considered **Personally Identifiable Information (PII)** under regulations
such as **GDPR**, **CCPA**, **LGPD**, and others.

By default, `privacy_mode` is **enabled** and disables all PII enrichment features
(IP lookup, geo-location lookup, and device detection).

To enable enrichment, opt out of privacy mode explicitly:

```python
from visionlog import get_logger

logger = get_logger(
    "my-app",
    ip_address=True,
    geo_info=True,
    device_info=True,
    privacy_mode=False,
)
```

> ⚠️ **Warning**: Only set `privacy_mode=False` when you have a lawful basis
> for collecting this data, have notified your users, and have reviewed your
> compliance obligations.

---

## 📡 Network Control

visionlog performs external HTTP calls for IP lookup and geo-location lookup.
This can cause issues in CI environments, air-gapped systems, or restricted networks.

Use `disable_network=True` to skip all HTTP calls and receive fallback values instead
(`None` for IP, `{}` for geo info):

```python
from visionlog import get_logger

logger = get_logger(
    "my-app",
    ip_address=True,
    geo_info=True,
    privacy_mode=False,
    disable_network=True,  # no external HTTP calls are made
)
```

`disable_network` is compatible with `privacy_mode`.  When `privacy_mode=True`
(the default) network calls are already prevented, so `disable_network` is most
useful when `privacy_mode=False` but you still need to suppress network activity.

---

## ⚡ **Why Use Visionlog?**

✅ **Super fast JSON serialization** using `orjson`  
✅ **Structured, formatted logs** for analytics  
✅ **Extensible** with OpenTelemetry for tracing  
✅ **Command-line logging** for quick debugging  

---

## 🧰 Development Tasks

This project uses [Taskfile](https://taskfile.dev) for development workflows.

Install Task:

**macOS / Linux (Homebrew):**
```bash
brew install go-task/tap/go-task
```

**Windows (Chocolatey):**
```bash
choco install go-task
```

**Windows (Scoop):**
```bash
scoop install task
```

**Linux (snap):**
```bash
snap install task --classic
```

Or download a binary directly from the [Taskfile releases page](https://github.com/go-task/task/releases).

List available tasks:

```bash
task --list
```

---

## 🛠 **Development & Contribution**

1. Clone the repository:

   ```sh
   git clone https://github.com/szmyty/visionlog.git
   cd visionlog
   ```

2. Install dependencies:

   ```sh
   poetry install
   ```

3. Run the example:

   ```sh
   python examples/basic_usage.py
   ```

---

## 📐 **API Stability & Versioning Policy**

### Public API

The public API of Visionlog consists of everything exported in `__all__` from the top-level `visionlog` package:

| Symbol | Kind | Description |
|---|---|---|
| `get_logger` | Function | Creates and returns a configured logger instance |
| `configure_visionlog` | Function | Configures the global structlog pipeline |
| `LoggerConfig` | Dataclass | Structured configuration object for `get_logger` |
| `Enricher` | Protocol | Interface for custom log enrichers |
| `Processor` | Protocol | Interface for custom structlog processors |
| `NetworkEnricher` | Class | Built-in IP/geo enrichment |
| `DeviceEnricher` | Class | Built-in device-detection enrichment |
| `get_public_ip` | Function | Utility — fetches the public IP address |
| `get_geo_info` | Function | Utility — fetches geo-location data for an IP |
| `get_device_info` | Function | Utility — parses a User-Agent string |
| `serialize_json` | Function | Utility — serialises a value to JSON bytes via `orjson` |
| `add_common_fields` | Function | Built-in structlog processor — adds common metadata fields |
| `add_otel_context` | Function | Built-in structlog processor — injects OpenTelemetry trace context |

Any symbol **not** listed above (e.g. internal helpers inside sub-modules) is considered **private** and may change without notice.

### Stability guarantees

> ⚠️ **Visionlog is currently in Alpha** (`0.x.y`).  
> The public API is stabilising but **breaking changes may still occur in minor version bumps** while the project is pre-1.0.

| Phase | Guarantee |
|---|---|
| **0.x.y — Alpha/Beta** | The public API surface above is defined and intentional, but signatures and behaviour may change in any `0.x` release. Migration notes are always included in [CHANGELOG.md](CHANGELOG.md). |
| **1.0.0 — Stable** | Full semantic versioning guarantees apply (see below). No breaking changes without a major version bump. |

### Semantic versioning

Visionlog follows [Semantic Versioning 2.0.0](https://semver.org/) (`MAJOR.MINOR.PATCH`):

| Version component | When it is incremented |
|---|---|
| **MAJOR** (`X.y.z`) | Backwards-incompatible changes to the public API (e.g. removing or renaming exported symbols, changing function signatures in a breaking way). |
| **MINOR** (`x.Y.z`) | New backwards-compatible functionality added to the public API (e.g. new exported symbols, new optional parameters with default values). |
| **PATCH** (`x.y.Z`) | Backwards-compatible bug fixes that do not alter the public API contract. |

Version numbers are managed automatically by [Commitizen](https://commitizen-tools.github.io/commitizen/) using [Conventional Commits](https://www.conventionalcommits.org/):

- `fix:` commits trigger a **patch** bump.
- `feat:` commits trigger a **minor** bump.
- Commits with a `BREAKING CHANGE:` footer, or a `!` suffix (e.g. `feat!:`), trigger a **major** bump.

Releases are tagged as `vMAJOR.MINOR.PATCH` (e.g. `v1.0.0`) and every release is accompanied by an entry in [CHANGELOG.md](CHANGELOG.md).

---

## 📜 **License**

Visionlog is released under the **MIT License**.
