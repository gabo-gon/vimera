"""Allow VIMERA to be executed with ``python -m vimera``."""

from vimera.cli.main import app


if __name__ == "__main__":
    app()