"""Unit tests for the visionlog CLI."""
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from visionlog.cli import log


def test_cli_log_default_message():
    """Validates CLI invocation with the default message."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger):
        runner = CliRunner()
        result = runner.invoke(log, [])
    assert result.exit_code == 0
    mock_logger.info.assert_called_once_with("Hello, Visionlog!")


def test_cli_log_custom_message():
    """Validates CLI invocation with a custom message using CliRunner."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger):
        runner = CliRunner()
        result = runner.invoke(log, ["--message", "test log entry"])
    assert result.exit_code == 0
    mock_logger.info.assert_called_once_with("test log entry")
