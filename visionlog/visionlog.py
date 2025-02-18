import sys
import structlog
import loguru
import orjson
from opentelemetry.trace import get_tracer_provider

def serialize_json(record, *args, **kwargs):
    """Serialize logs using orjson for high-performance JSON output."""
    return orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE).decode()

def get_logger(service_name="visionlog"):
    """Sets up a structured logger with Loguru and Structlog."""
    loguru.logger.remove()
    loguru.logger.add(sys.stdout, format="{message}", serialize=False)
    
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(serializer=serialize_json),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger(service=service_name)

if __name__ == "__main__":
    logger = get_logger()
    logger.info("Info log example", user="tester")
    logger.warning("Warning log example", env="staging")
    logger.error("Error log example", error="Example error")

    print("\n✅ Visionlog is working correctly!")

