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


def test_cli_service_name():
    """Validates --service-name is forwarded to LoggerConfig."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger) as mock_get:
        runner = CliRunner()
        result = runner.invoke(log, ["--service-name", "my-service", "--message", "hi"])
    assert result.exit_code == 0
    config = mock_get.call_args.kwargs["config"]
    assert config.service_name == "my-service"


def test_cli_default_service_name():
    """Validates service_name defaults to 'visionlog'."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger) as mock_get:
        runner = CliRunner()
        result = runner.invoke(log, [])
    assert result.exit_code == 0
    config = mock_get.call_args.kwargs["config"]
    assert config.service_name == "visionlog"


def test_cli_log_level_warning():
    """Validates --level warning calls logger.warning()."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger):
        runner = CliRunner()
        result = runner.invoke(log, ["--level", "warning", "--message", "warn message"])
    assert result.exit_code == 0
    mock_logger.warning.assert_called_once_with("warn message")


def test_cli_log_level_error():
    """Validates --level error calls logger.error()."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger):
        runner = CliRunner()
        result = runner.invoke(log, ["--level", "error", "--message", "error message"])
    assert result.exit_code == 0
    mock_logger.error.assert_called_once_with("error message")


def test_cli_log_level_debug():
    """Validates --level debug calls logger.debug()."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger):
        runner = CliRunner()
        result = runner.invoke(log, ["--level", "debug", "--message", "debug message"])
    assert result.exit_code == 0
    mock_logger.debug.assert_called_once_with("debug message")


def test_cli_user_id_and_session_id():
    """Validates --user-id and --session-id are forwarded to LoggerConfig."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger) as mock_get:
        runner = CliRunner()
        result = runner.invoke(
            log,
            [
                "--user-id",
                "u123",
                "--session-id",
                "s456",
                "--message",
                "event",
            ],
        )
    assert result.exit_code == 0
    config = mock_get.call_args.kwargs["config"]
    assert config.user_id == "u123"
    assert config.session_id == "s456"


def test_cli_no_privacy_disables_privacy_mode():
    """Validates --no-privacy sets privacy_mode=False in LoggerConfig."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger) as mock_get:
        runner = CliRunner()
        result = runner.invoke(log, ["--no-privacy", "--message", "event"])
    assert result.exit_code == 0
    config = mock_get.call_args.kwargs["config"]
    assert config.privacy_mode is False


def test_cli_default_privacy_mode_is_true():
    """Validates privacy_mode defaults to True when --no-privacy is not given."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger) as mock_get:
        runner = CliRunner()
        result = runner.invoke(log, ["--message", "event"])
    assert result.exit_code == 0
    config = mock_get.call_args.kwargs["config"]
    assert config.privacy_mode is True


def test_cli_ip_flag():
    """Validates --ip passes ip_address=True to get_logger."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger) as mock_get:
        runner = CliRunner()
        result = runner.invoke(log, ["--no-privacy", "--ip", "--message", "event"])
    assert result.exit_code == 0
    assert mock_get.call_args.kwargs["ip_address"] is True


def test_cli_no_ip_flag():
    """Validates --no-ip passes ip_address=None to get_logger."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger) as mock_get:
        runner = CliRunner()
        result = runner.invoke(log, ["--no-ip", "--message", "event"])
    assert result.exit_code == 0
    assert mock_get.call_args.kwargs["ip_address"] is None


def test_cli_geo_flag():
    """Validates --geo passes geo_info=True to get_logger."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger) as mock_get:
        runner = CliRunner()
        result = runner.invoke(log, ["--no-privacy", "--geo", "--message", "event"])
    assert result.exit_code == 0
    assert mock_get.call_args.kwargs["geo_info"] is True


def test_cli_no_geo_flag():
    """Validates --no-geo passes geo_info=False to get_logger."""
    mock_logger = MagicMock()
    with patch("visionlog.cli.get_logger", return_value=mock_logger) as mock_get:
        runner = CliRunner()
        result = runner.invoke(log, ["--no-geo", "--message", "event"])
    assert result.exit_code == 0
    assert mock_get.call_args.kwargs["geo_info"] is False


def test_cli_error_handling():
    """Validates exceptions are written to stderr and exit code is 1."""
    with patch(
        "visionlog.cli.get_logger", side_effect=RuntimeError("something went wrong")
    ):
        runner = CliRunner(mix_stderr=True)
        result = runner.invoke(log, ["--message", "event"])
    assert result.exit_code == 1
    assert "something went wrong" in result.output


def test_cli_invalid_level():
    """Validates that an invalid log level is rejected by Click."""
    runner = CliRunner()
    result = runner.invoke(log, ["--level", "trace"])
    assert result.exit_code != 0


def test_cli_help():
    """Validates that --help displays usage information for all options."""
    runner = CliRunner()
    result = runner.invoke(log, ["--help"])
    assert result.exit_code == 0
    assert "--message" in result.output
    assert "--service-name" in result.output
    assert "--level" in result.output
    assert "--user-id" in result.output
    assert "--session-id" in result.output
    assert "--no-privacy" in result.output
    assert "--ip" in result.output
    assert "--geo" in result.output
