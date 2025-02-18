from visionlog import get_logger

logger = get_logger("example-app")

logger.info("User login event", user="john_doe", action="login")
logger.warning("Suspicious activity detected", ip="192.168.1.1")
logger.error("Server crashed!", error_code=500)

