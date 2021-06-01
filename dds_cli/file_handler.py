"""File handler module. Base class for LocalFileHandler and RemoteFileHandler."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import json
import logging
import os
import pathlib
import textwrap

# Installed
import rich

# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

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
                try:
                    original_umask = os.umask(0)  # User file-creation mode mask
                    with source_path_file.resolve().open(mode="r") as spf:
                        self.data_list += spf.read().splitlines()
                except OSError as err:
                    console.print(f"Failed to get files from source-path-file option: {err}")
                    os.umask(original_umask)
                    os._exit(1)
                finally:
                    os.umask(original_umask)

        self.failed = {}

    # Static methods ############ Static methods #
    @staticmethod
    def extract_config(configfile):
        """Extracts info from config file."""

        # Absolute path to config file
        configpath = pathlib.Path(configfile).resolve()
        if not configpath.exists():
            console.print("\n:warning: Config file does not exist. :warning:\n")
            os._exit(1)

        # Open config file and get contents
        try:
            original_umask = os.umask(0)
            with configpath.open(mode="r") as cfp:
                contents = json.load(cfp)
        except json.decoder.JSONDecodeError as err:
            console.print(f"\nFailed to get config file contents: {err}\n")
            os._exit(1)
        finally:
            os.umask(original_umask)

        return contents

    @staticmethod
    def save_errors_to_file(file: pathlib.Path, info):
        try:
            original_umask = os.umask(0)  # User file-creation mode mask
            with file.open(mode="w") as errfile:
                json.dump(
                    info,
                    errfile,
                    indent=4,
                )
        except (OSError, TypeError) as err:
            LOG.warning(str(err))
        finally:
            os.umask(original_umask)

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

        LOG.debug("Files: %s, Upload: %s, Columns: %s", get_single_files, upload, columns)

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

        additional_message = (
            (
                "One or more files were not uploaded due to a issue with another file. "
                "To ignore issues with other files, remove the `--break-on-fail` "
                "flag from the call."
            )
            if any([1 for x in files if "break-on-fail" in x[1]["message"]])
            else ""
        )

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
                            textwrap.fill(x[1]["path_raw"]),
                            x[1]["message"] if "break-on-fail" not in x[1]["message"] else "",
                        )
                        for x in files
                    ]
                else:
                    _ = [
                        curr_table.add_row(
                            x[1]["name_in_db"],
                            textwrap.fill(x[0]),
                            x[1]["message"] if "break-on-fail" not in x[1]["message"] else "",
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
                            x[1]["message"] if "break-on-fail" not in x[1]["message"] else "",
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
                            x[1]["message"] if "break-on-fail" not in x[1]["message"] else "",
                        )

                        subpath = x[1]["subpath"]

        return curr_table, additional_message

    @staticmethod
    def delete_tempdir(directory: pathlib.Path):
        """Deletes the specified directory."""

        ok_to_remove = False

        # If file not ok to remove folder
        if not directory.is_dir():
            return ok_to_remove

        # Iterate through any existing subdirectories - recursive
        LOG.debug("Any in directory? %s", any(directory.iterdir()))
        for x in directory.iterdir():
            LOG.debug(x)
        if any(directory.iterdir()):
            for p in directory.iterdir():
                if p.is_dir():
                    ok_to_remove = FileHandler.delete_tempdir(directory=p)
                    if ok_to_remove:
                        directory.rmdir()
        else:
            directory.rmdir()
            ok_to_remove = True

        return ok_to_remove
