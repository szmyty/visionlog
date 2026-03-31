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
