"""File handler module. Base class for LocalFileHandler and RemoteFileHandler."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import pathlib
import os
import json
import textwrap

# Installed
import rich

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# RICH CONFIG ################################################### RICH CONFIG #
###############################################################################

console = rich.console.Console()

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class FileHandler:
    """Main file handler."""

    def __init__(self, user_input, local_destination):
        source, source_path_file = user_input

        # Get user specified data
        self.local_destination = local_destination
        self.data_list = list()
        if source is not None:
            self.data_list += list(source)
        if source_path_file is not None:
            source_path_file = pathlib.Path(source_path_file)
            if source_path_file.exists():
                with source_path_file.resolve().open(mode="r") as spf:
                    self.data_list += spf.read().splitlines()

        self.failed = {}

    @staticmethod
    def extract_config(configfile):
        """Extracts info from config file."""

        # Absolute path to config file
        configpath = pathlib.Path(configfile).resolve()
        if not configpath.exists():
            console.print("\n:warning: Config file does not exist. :warning:\n")
            os._exit(os.EX_OK)

        # Open config file and get contents
        try:
            original_umask = os.umask(0)
            with configpath.open(mode="r") as cfp:
                contents = json.load(cfp)
        except json.decoder.JSONDecodeError as err:
            console.print(f"\nFailed to get config file contents: {err}\n")
            os._exit(os.EX_OK)
        finally:
            os.umask(original_umask)

        return contents

    @staticmethod
    def save_errors_to_file(file: pathlib.Path, info):
        with file.open(mode="w") as errfile:
            json.dump(
                info,
                errfile,
                indent=4,
            )

    @staticmethod
    def create_summary_table(
        all_failed_data,
        get_single_files: bool = True,
        upload: bool = True,
    ):

        columns = ["File", "Error"] if upload else ["File", "Location", "Error"]
        curr_table = None
        title = "file" if get_single_files else "directory"
        up_or_down = "upload" if upload else "download"

        LOG.debug(
            "Files: %s, Upload: %s, Columns: %s", get_single_files, upload, columns
        )

        if not get_single_files:
            columns = ["Directory"] + columns

        files = [
            x
            for x in all_failed_data
            if (
                get_single_files
                and x[1]["subpath"] == "."
                or not get_single_files
                and x[1]["subpath"] != "."
            )
        ]
        if files:
            curr_table = rich.table.Table(
                title=f"Incomplete {title} {up_or_down}s",
                title_justify="left",
                show_header=True,
                header_style="bold",
            )

            for x in columns:
                curr_table.add_column(x, overflow="fold")

            if get_single_files:
                if upload:
                    _ = [
                        curr_table.add_row(
                            textwrap.fill(x[1]["path_raw"]), x[1]["message"]
                        )
                        for x in files
                    ]
                else:
                    _ = [
                        curr_table.add_row(
                            x[1]["name_in_db"], textwrap.fill(x[0]), x[1]["message"]
                        )
                        for x in files
                    ]
            else:
                subpath = ""
                if upload:
                    for x in files:
                        curr_table.add_row(
                            textwrap.fill(
                                ""
                                if subpath == x[1]["subpath"]
                                else str(pathlib.Path(x[1]["path_raw"]).parent)
                            ),
                            str(pathlib.Path(x[1]["path_raw"]).name),
                            x[1]["message"],
                        )

                        subpath = x[1]["subpath"]
                else:
                    for x in files:
                        curr_table.add_row(
                            ""
                            if subpath == x[1]["subpath"]
                            else str(pathlib.Path(x[1]["subpath"])),
                            x[1]["name_in_db"],
                            textwrap.fill(str(pathlib.Path(x[0]))),
                            x[1]["message"],
                        )

                        subpath = x[1]["subpath"]

        return curr_table
