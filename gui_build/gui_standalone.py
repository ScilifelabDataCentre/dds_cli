"""
This file is used to run the DDS GUI standalone for the executable.
"""

from dds_cli.dds_gui.app import DDSApp


if __name__ == "__main__":
    token_path = pathlib.Path("custom") / "token" / "path"
    app = DDSApp(token_path=str(token_path))
    app.run()
