"""Run the DDS GUI standalone executable."""

from pathlib import Path

from dds_cli.dds_gui.app import DDSApp


if __name__ == "__main__":
    token_path = Path("custom") / "token" / "path"
    app = DDSApp(token_path=str(token_path))
    app.run()
