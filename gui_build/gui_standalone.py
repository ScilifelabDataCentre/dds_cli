"""
This file is used to run the DDS GUI standalone for the executable.
"""

import pathlib

from dds_cli.dds_gui.app import DDSApp

if __name__ == "__main__":
    app = DDSApp(token_path=pathlib.Path.home() / ".dds_cli_token")
    app.run()
