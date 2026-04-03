import sys

import click

from .config import LoggerConfig
from .visionlog import get_logger


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "Log a structured message using visionlog.\n\n"
        "Examples:\n\n"
        "  visionlog-cli --message 'hello world'\n\n"
        "  visionlog-cli --service-name myapp --level warning --message 'disk full'\n\n"
        "  visionlog-cli --service-name myapp --user-id u1 --session-id s1 --message 'login'\n\n"
        "  visionlog-cli --service-name myapp --no-privacy --ip --geo --message 'user event'"
    ),
)
@click.option(
    "--message",
    default="Hello, Visionlog!",
    show_default=True,
    help="The message to log.",
)
@click.option(
    "--service-name",
    default="visionlog",
    show_default=True,
    help="Service or application name to tag log records with.",
)
@click.option(
    "--level",
    default="info",
    show_default=True,
    type=click.Choice(
        ["debug", "info", "warning", "error", "critical"], case_sensitive=False
    ),
    help="Log level.",
)
@click.option(
    "--user-id",
    default=None,
    help="User identity to bind to every log record.",
)
@click.option(
    "--session-id",
    default=None,
    help="Session identifier to bind to every log record.",
)
@click.option(
    "--no-privacy",
    "no_privacy",
    is_flag=True,
    default=False,
    help="Disable privacy mode and allow PII enrichment (IP, geo, device).",
)
@click.option(
    "--ip/--no-ip",
    default=False,
    help="Auto-fetch and log the public IP address (requires --no-privacy).",
)
@click.option(
    "--geo/--no-geo",
    default=False,
    help="Fetch geo-location data for the IP address (requires --no-privacy).",
)
def log(message, service_name, level, user_id, session_id, no_privacy, ip, geo) -> None:
    try:
        config = LoggerConfig(
            service_name=service_name,
            user_id=user_id,
            session_id=session_id,
            privacy_mode=not no_privacy,
        )
        ip_address = True if ip else None
        logger = get_logger(config=config, ip_address=ip_address, geo_info=geo)
        getattr(logger, level)(message)
    except Exception as e:
        click.echo(str(e), err=True)
        sys.exit(1)


if __name__ == "__main__":
    log()

