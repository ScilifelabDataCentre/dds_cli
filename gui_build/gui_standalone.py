"""Run the DDS GUI standalone executable."""

import pathlib

import pathlib

from dds_cli.dds_gui.app import DDSApp


if __name__ == "__main__":
    token_path = pathlib.Path("custom") / "token" / "path"
    app = DDSApp(token_path=str(token_path))
    app.run()
