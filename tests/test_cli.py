from typer.testing import CliRunner

from bkl_engine import __version__
from bkl_engine.cli.main import app


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"


def test_cli_prints_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "bkl-skill-engine 0.1.0" in result.stdout
