from visionlog import get_logger, LoggerConfig

# --- Config-based usage (new) ---
config = LoggerConfig(
    service_name="example-app",
    user_id="john_doe",
    environment="production",
)
logger = get_logger(config=config)

logger.info("User login event", action="login")
logger.warning("Suspicious activity detected", ip="192.168.1.1")
logger.error("Server crashed!", error_code=500)

# --- Keyword-argument usage (still supported) ---
logger2 = get_logger(service_name="example-app", user_id="jane_doe")
logger2.info("Another login event", action="login")

