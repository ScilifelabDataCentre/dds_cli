"""
This file is used to run the DDS GUI standalone for the executable.
"""

from pathlib import Path

from dds_cli.dds_gui.app import DDSApp

if __name__ == "__main__":
    app = DDSApp(token_path=str(Path.home() / ".dds_cli_token"))
    app.run()
