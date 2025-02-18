import click
from .visionlog import get_logger

@click.command()
@click.option("--message", default="Hello, Visionlog!", help="Log message.")
def log(message):
    logger = get_logger()
    logger.info(message)

if __name__ == "__main__":
    log()

