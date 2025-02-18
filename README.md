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

```python
from visionlog import get_logger
from opentelemetry import trace

tracer = trace.get_tracer("visionlog-tracer")
logger = get_logger("my-app")

with tracer.start_as_current_span("http_request"):
    logger.info("Tracking request event", endpoint="/api/data", status=200)
```

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
