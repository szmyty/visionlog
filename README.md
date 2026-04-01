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

### **2. CLI Usage**

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

## 📜 **License**

Visionlog is released under the **MIT License**.
