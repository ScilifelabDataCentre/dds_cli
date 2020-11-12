"""Data Deliverer, used by the Data Delivery System CLI.

Handles the login of all users, performs checks on the data and handles the
upload and download of all files. Also keeps track of the delivery progress.
"""

# TODO(ina): Fix or ignore "too-many-attributes" etc pylint error

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
from pathlib import Path
import json
import logging
import os
import sys
import threading
import traceback
import requests
import pandas as pd

# Installed
import botocore.client
import prettytable

# Own modules
from cli_code import Format
from cli_code import DIRS
from cli_code import ENDPOINTS
from cli_code import crypto_ds
from cli_code import exceptions_ds
from cli_code import file_handler
from cli_code import s3_connector


###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #
###############################################################################

# TODO (ina): There may be issues with unicode and Windows - test and fix
# TODO (ina): Change dict to immutable?
# The different types of delivery statuses
# ns: not started, f: finished, e: error,
# enc: encrypting, dec: decrypting
# u: uploading, d: downloading
STATUS_DICT = {"w": "Waiting to start...",
               "f": u"\u2705        ",
               "e": u"\u274C        ",
               "enc": "Encrypting...",
               "dec": "Decrypting...",
               "u": "Uploading...",
               "d": "Dowloading...", }

# Initializes the column sizes for the progress output
FCOLSIZE = 0    # File name column
SCOLSIZE = 0    # Status column

# TODO (ina): Change string addition to list and "".join
# Initializes the progress output
TO_PRINT = ""       # Progress output
PROGRESS = None     # Progress dict containing all file statuses
# TODO (ina): Add statuses to data dict instead of own dict?

PROGRESS_DF = None


# Login endpoint - changes depending on facility or not
LOGIN_BASE = ""

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataDeliverer:
    """Handles and keeps track of all data delivery related operations.

    Instanstiates the delivery by logging the user into the Delivery System,
    checking the users access to the specified project, and uploads/downloads
    the data to the S3 storage.

    Args:
        creds (str):            Path to file with user creds and project info
        username (str):         User spec. username, None if creds used
        password (str):         User spec. password, None if creds used
        project_id (str):       User spec. project ID, None if creds used
        project_owner (str):    User spec. project owner, None if creds used
        pathfile (str):         Path to file containing file paths
        data (tuple):           All paths to be uploaded/downloaded
        break_on_fail (bool):   True if folder delivery should be cancelled on
                                file fail
        overwrite (bool):       True if deliver again - overwrite delivered
                                files

    Attributes:
        break_on_fail (bool):   Cancel delivery on fail or not
        overwrite (bool):       Overwrite already delivered files or not
        method (str):           Delivery method, put or get
        user (DSUser):          Data Delivery System user
        project_id (str):       Project ID to upload to/download from
        project_owner (str):    Owner of the current project
        data (dict):            Paths and info to files
        failed (dict):          Paths and info to failed files
        bucketname (str):       Name of S3 bucket to deliver to/from
        s3project (str):        ID of S3 project containing buckets
        public (bytes):         Project public key
        private (bytes):        Project private key, b'' if uploading
    """

    #################
    # Magic Methods #
    #################
    def __init__(self, creds=None, username=None, password=None,
                 project_id=None, project_owner=None, pathfile=None, data=None,
                 break_on_fail=True, overwrite=False):
        """Inits DataDeliverer and checks the users access to the system."""

        # Flags ------------------------------------------------------- Flags #
        self.break_on_fail = break_on_fail  # If cancel on one failure
        self.overwrite = overwrite          # If overwrite previous delivery
        # --------------------------------------------------------------------#
        # Quit delivery if none of username, password, creds are set
        if all(x is None for x in [username, password, creds]):
            sys.exit(exceptions_ds.printout_error(
                "Delivery System login credentials not specified.\n\n"
                "Enter: \n"
                "--username/-u AND --password/-pw, or --creds/-c\n"
                "--owner/-o\n\n"
                "For help: 'ds_deliver --help'."
            ))

        # Main attributes ----------------------------------- Main attributes #
        # General
        self.method = sys._getframe().f_back.f_code.co_name  # put or get
        # self.project_id = project_id        # Project ID - not S3
        # self.project_owner = project_owner  # User, not facility
        self.data_input = []        # Data that the user specified
        self.data = None            # Dictionary, keeps track of delivery
        self.failed = None          # Dictionary, saves intially failed files

        # S3 related
        self.bucketname = ""    # S3 bucket name -- to connect to S3
        self.s3project = ""   # S3 project ID - for S3 conn
        # TODO (ina): Move s3project to database somewhere

        # Cryptography related
        self.public = b""       # Public key    (project)
        self.private = b""      # Private key   (project)

        # Checks ----------------------------------------------------- Checks #
        # Check if all required info is entered and get user info
        self.user = _DSUser()
        self.user.username, self.user.password, self.project_id, \
            self.project_owner = self._check_user_input(
                creds=creds,
                username=username,
                password=password,
                project=project_id,
                owner=project_owner
            )

        # Get access to DS -- returns json format with access, user_id,
        # project_id, s3_id, error and token.
        delivery_info = self._check_ds_access()
        self.user.id = delivery_info["user_id"]
        self.token = delivery_info["token"]

        # Fail if no data specified
        if not data and not pathfile:
            sys.exit(
                exceptions_ds.printout_error(
                    "No data to be uploaded. Specify individual "
                    "files/folders using the --data/-d option one "
                    "or more times, or the --pathfile/-f. \n\n"
                    "For help: 'ds_deliver --help'")
            )

        # If everything ok, set bucket name
        self.bucketname = delivery_info["s3_id"]

        # Set public key
        self.public = bytes.fromhex(delivery_info["public_key"])
        LOG.debug("Project public key: %s", self.public)

        # Get all data to be delivered
        self.data, self.failed = self._data_to_deliver(data=data,
                                                       pathfile=pathfile)
        LOG.debug("Data to deliver: %s", self.data)

        # NOTE: Change this into ECDH key? Tried but problems with pickling
        # Get project keys
        if self.method == "put":
            self.private = b""
        elif self.method == "get":
            self.private = crypto_ds.get_project_private(
                self.project_id, self.user, self.token)

        # Start progress info printout
        if self.data:
            # cap_not_exceeded = self._check_cap()
            # if cap_not_exceeded:
            self._create_progress_output()

    def __repr__(self):

        return f"< DataDeliverer {self.user.id} - {DIRS[0]}"

    def __enter__(self):
        """Allows for implementation using "with" statement.
        Building."""

        return self

    def __exit__(self, exc_type, exc_value, tb):
        """Allows for implementation using "with" statement.
        Tear it down. Delete class.

        Prints out which files are delivered and not."""

        def textwrapp(curr_string, max_line_length=50, separator="\n",
                      sep_in_string=os.sep):
            """Creates new lines within long paths.

            Can be altered to not add os.sep --> all text wrapping.

            Args:
                curr_string:        The string to wrap
                max_line_length:    The width of the rows after wrapping
                separator:          What to separate the lines with
                sep_in_string:      String to separate words with

            Returns:
                str:    Wrapped string
            """

            curr_string = str(curr_string)
            curr_line_len = 0
            curr_line = ""
            for x in curr_string.split(sep_in_string):
                if x != "":
                    if curr_line_len + len(x) < max_line_length:
                        curr_line += (sep_in_string + x)
                        curr_line_len += len(sep_in_string + x)
                    else:
                        curr_line += (separator + sep_in_string + x)
                        curr_line_len += len(sep_in_string + x)
                        curr_line_len = len(sep_in_string + x)
            return curr_line

        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        # ------------------------------------------------------------------- #

        # Variables ############################################### Variables #
        folders = {}            # Already checked folders
        files = {"successful": {}, "failed": {}}
        # Create table to be printed out and format it
        all_info_to_log_table = prettytable.PrettyTable(
            ["File", "Delivered", "Error"]
        )
        all_info_to_log_table.padding_width = 2
        all_info_to_log_table.align["File"] = "l"
        all_info_to_log_table.align["Error"] = "l"

        # ------------------------------------------------------------------- #

        # Move failed files to failed dict
        for file, info in list(self.data.items()):
            if not info["proceed"]:
                self.failed[file] = self.data.pop(file)

        for d in self.data_input:

            # Set method specific variables
            d_path = ""
            meth = ""
            filerootloc = ""
            if self.method == "get":
                d_path = d
                meth = "downloaded"
                filerootloc = f"{DIRS[1]}."
            elif self.method == "put":
                d_path = Path(d)
                meth = "uploaded"
                filerootloc = "Root directory of the projects " + \
                    "Safespring bucket."

            if d_path in self.data:    # is delivered FILE
                files["successful"] = {
                    d: self.data[d_path]["path_in_bucket"]
                }
                self._finalize(self.data[d_path])
            elif d_path in self.failed:    # is failed FILE
                files["failed"] = {d: self.failed[d_path]["error"]}
                self._finalize(self.failed[d_path])
            else:   # is not FILE -- checking if folder
                for f, i in self.data.items():
                    # is delivered FOLDER/DIRECTORY
                    if i["in_directory"] and i["local_dir_name"] == d_path:
                        if not d in folders:
                            folders[d] = {"successful": {}, "failed": {}}

                        folders[d]["successful"].update(
                            {f: i["path_in_bucket"]})
                        self._finalize(i)

                for f, i in self.failed.items():
                    # is failed FOLDER/DIRECTORY
                    if i["in_directory"] and i["local_dir_name"] == d_path:
                        if not d in folders:
                            folders[d] = {"successful": {}, "failed": {}}

                        folders[d]["failed"].update({f: i["error"]})
                        self._finalize(i)

        # FINAL MESSAGE ####################################### FINAL MESSAGE #

        # Only print out final message if data has been specified
        if folders or files["successful"] or files["failed"]:
            sys.stdout.write(Format.HEADER + "* "*11 +
                             "DELIVERY REPORT" + " *"*11 + Format.END + "\n\n")

        # Print out failed folders and information about delivered
        if folders:
            sys.stdout.write(Format.BOLD + "\n" + "- "*13 +
                             "Folders" + " -"*13 + Format.END + "\n\n")
            for f in folders:
                total_attempted = len(folders[f]["successful"]) + \
                    len(folders[f]["failed"])
                if not folders[f]["failed"]:    # All files successful
                    print_info = (f"{Format.UNDERLINE}Folder:{Format.END} {f}\nFiles attempted: "
                                  f"{total_attempted}\t Files {meth}: "
                                  f"{len(folders[f]['successful'])}.\n\n")
                    sys.stdout.write(print_info)
                    LOG.info(print_info)
                else:
                    print_info = (f"{Format.UNDERLINE}Folder:{Format.END} {f}\nFiles attempted: "
                                  f"{total_attempted}\tFiles {meth}: "
                                  f"{len(folders[f]['successful'])}\n"
                                  "Failed files: \n")
                    sys.stdout.write(print_info)
                    LOG.info(print_info)

                    # Create table to be printed out and format it
                    folders_table = prettytable.PrettyTable(
                        ["File", "Delivered", "Error"]
                    )
                    folders_table.padding_width = 2
                    folders_table.align["File"] = "l"
                    folders_table.align["Error"] = "l"

                    # Add rows to folder table
                    for x, y in folders[f]["failed"].items():
                        folders_table.add_row(
                            [textwrapp(x), "NO",
                             textwrapp(y, sep_in_string=" ")]
                        )
                        folders_table.add_row(
                            ["", "", ""]
                        )

                    print(folders_table)
                    sys.stdout.write("\n\n")
                    LOG.info("\n%s\n\n", folders_table)

        if not files["failed"] and files["successful"]:  # All files sucessful
            print_info = (Format.BOLD + "- "*7 + "Files (not located in directory)" +
                          " -"*7 + Format.END + "\n\nFiles attempted: "
                          f"{len(files['successful'])}\tFiles {meth}: "
                          f"{len(files['successful'])}\n\n" + "- "*31 +
                          f"\n\nLocation of {meth} files:\t {filerootloc}\n")
            sys.stdout.write(print_info)
            LOG.info(print_info)
        elif files["failed"]:
            total_attempted = len(files["successful"]) + \
                len(files["failed"])

            print_info = (
                Format.BOLD + "- "*7 +
                "Files (not located in directory)" +
                " -"*7 + Format.END + "\n\n"
                f"Files attempted: {total_attempted}\t"
                f"Files {meth}: {len(files['successful'])}\n"
                "Failed files: \n"
            )
            sys.stdout.write(print_info)
            LOG.info(print_info)

            # Create table for failed files and format it
            files_table = prettytable.PrettyTable(
                ["File", "Delivered", "Error"]
            )
            files_table.align["File"] = "l"
            files_table.align["Error"] = "l"

            # Add rows
            for x, y in files["failed"].items():
                files_table.add_row(
                    [textwrapp(x), "NO", textwrapp(y, sep_in_string=" ")]
                )
                files_table.add_row(
                    ["", "", ""]
                )

                print(files_table)
                if files["successful"]:
                    print_info = (
                        "\n\n" + "- "*31 +
                        f"\n\nLocation of {meth} files:\t {filerootloc}\n\n"
                    )
                    sys.stdout.write(print_info)

                LOG.info("%s", files_table)

        # Information on file location
        if folders or files["successful"] or files["failed"]:
            sys.stdout.write(
                f"\nA detailed list of {meth} user-specified data can be "
                "found \nin the delivery log file, located in the directory:\n"
                f"{DIRS[-1]}\n\n" + "* "*31 + "\n\n"
            )

        LOG.info("DELIVERY FINISHED")
        return True

        # ------------------------------------------------------------------- #

    ###################
    # Private Methods #
    ###################

    def _check_cap(self):
        """Checks if the file size exceeds 700 GB."""

        tot_size = 0
        for x, y in self.data.items():
            tot_size += y["size"]
            # print(x, y["size"], tot_size)
            if tot_size > 700000000000:
                return False

        return True

    def _check_ds_access(self):
        """Checks the users access to the delivery system.

        Makes a request to the Delivery System REST API, which in turn
        checks the database for the user and its corresponding information.

        Returns:
            json:   Information on whether delivery can proceed and user info.
                access (bool):      True if access to DS granted\n
                s3_id (str):        ID of the S3 project (on Safespring)\n
                public_key (str):   The projects public_key\n
                error (str):        Error message if any\n
                project_id (int):   Project ID\n
        """

        global LOGIN_BASE
        args = {}

        # Get access to delivery system - check if derived pw hash valid
        # Different endpoint depending on facility or not.
        # print(self.project_owner, flush=True)
        LOGIN_BASE = ENDPOINTS["u_login"]
        args = {"username": self.user.username,
                "password": self.user.password,
                "project": self.project_id}
        if self.method == "put":
            args.update({"owner": self.project_owner,
                         "role": "facility"})
        elif self.method == "get":
            args.update({"role": "user"})

        # Request to get access
        response = requests.post(LOGIN_BASE, params=args)
        if not response.ok:
            sys.exit(
                exceptions_ds.printout_error(
                    "Something wrong. Could not access api/db during access "
                    "check. Login failed. Delivery cancelled.\n"
                    f"{response.status_code} -- {response.reason} -- {response.text}"
                )
            )

        # Get json response if request successful (does not mean access)
        json_response = response.json()

        # Quit if user not granted Delivery System access
        if not json_response["access"] and json_response["token"] == "":
            sys.exit(
                exceptions_ds.printout_error(
                    "Delivery System access denied! "
                    f"Delivery cancelled. {json_response['error']}"
                )
            )

        # Quit if project ID not matching
        if json_response["project_id"] != self.project_id:
            sys.exit(
                exceptions_ds.printout_error(
                    "Incorrect project ID. System error. "
                    "Cancelling delivery."
                )
            )

        return json_response

    def _check_user_input(self, creds, username, password, project, owner) \
            -> (str, str, int, int):
        """Checks that the correct options and credentials are entered.

        Args:
            creds:      File containing the users DP username and password,
                        and the project relating to the upload/download.
                        Can be used instead of inputing the creds separately.
            username:   Delivery System username
            password:   Delivery System password
            project:    Project ID
            owner:      Project owner

        Returns:
            tuple:  Info about user if all credentials specified
                username    (str):     Username\n
                password    (str):     Password\n
                project_id  (int):     Project ID\n
                owner_id    (int):     Owner ID\n
        """

        if not password or password is None:
            sys.exit(
                exceptions_ds.printout_error(
                    "Password not entered. Cancelling delivery."
                )
            )

        # creds file ----------- credentials in it ----------- creds file #
        if creds:
            user_creds = Path(creds).resolve()
            try:
                # Get info from credentials file
                with user_creds.open(mode="r") as crf:
                    credentials = json.load(crf)
            except OSError as ose:
                sys.exit(
                    exceptions_ds.printout_error(
                        f"""Could not open path-file {creds}: {ose}""")
                )

            # If the options have not been specified,
            # look for them in the credentials file
            if username is None and "username" in credentials:
                username = credentials["username"]
            if project is None and "project" in credentials:
                project = credentials["project"]
            if owner is None and "owner" in credentials:
                owner = credentials["owner"]

        # options ----------------------------------------------- options #
        if None in [username, password, project]:
            sys.exit(
                exceptions_ds.printout_error(
                    "Data Delivery System options missing.\n"
                    "For help: 'ds_deliver --help'."
                )
            )

        # Uploading requires a specified project owner
        # For downloading, it's currently assumed to be the user
        if self.method == "put" and owner is None:
            sys.exit(
                exceptions_ds.printout_error(
                    "Project owner not specified. Required for delivery.\n"
                    "Cancelling upload."
                )
            )
        elif self.method == "get":
            owner = username

        return username, password, project, owner

    def _create_progress_output(self) -> (str, dict):
        """Create list of files and the individual delivery progress.

        Returns:
            tuple:  Information on start status for all files

                str:    Progressinfo (all files) to print to console
                dict:   Files and their current delivery statuses

        """

        sys.stdout.write("\n")  # Space between command and any output

        # Set pandas to show all dataframe contents, no '...'
        pd.set_option("display.max_colwidth", None)

        b_u = Format.BOLD + Format.UNDERLINE
        end = Format.END
        global PROGRESS_DF  # Can edit global variable contents
        PROGRESS_DF = pd.DataFrame(
            {"File": [str(Path(x).name) for x in self.data],
             "     Status     ": [STATUS_DICT["w"] for _, y in self.data.items()],
             "Upload/Download Progress          ": ["" for x in self.data]}
        )

        sys.stdout.write(f"{PROGRESS_DF.to_string(index=False)}\n")

    def _data_to_deliver(self, data: tuple, pathfile: str) -> (dict, dict):
        """Puts all entered paths into one dictionary.

        Gathers all folders and files, checks their format etc, if they have
        been previously delivered, and puts all information into one
        dictionary.

        Args:
            data (tuple):       Tuple containing paths
            pathfile (str):   Path to file containing paths

        Returns:
            tuple:  Two dictionaries with info on user specified files.
                dict:   Info on all files to be delivered\n
                dict:   Info on files which failed initial check

        """

        # Variables ######################################### Variables #
        all_files = dict()      # Files passing initial check
        initial_fail = dict()   # Files failing initial check

        data_list = list(data)  # List with data specified by user

        # --------------------------------------------------------------#

        # Add data included in pathfile to data dict
        if pathfile is not None and Path(pathfile).exists():
            with Path(pathfile).resolve().open(mode="r") as file:
                data_list += [line.strip() for line in file]

        # Fail delivery if not a correct method
        if self.method not in ["get", "put"]:
            sys.exit(
                exceptions_ds.printout_error(
                    f"""Delivery option {self.method} not allowed.
                     \nCancelling delivery.""")
            )

        # Temporary cap
        if self.method == "put":
            self.data_input = list()
            tot_size = 0
            for x in data_list:
                filepath = Path(x).resolve()
                tot_size += filepath.stat().st_size
                # print(tot_size)
                if tot_size > 700e9:
                    sys.exit(
                        exceptions_ds.printout_error(
                            "Too much data. The upload cap is set at 700 GB."
                        )
                    )
                self.data_input.append(filepath)
        elif self.method == "get":
            # Save list of paths user chose
            self.data_input = list(x for x in data_list)

        # Get all project files in db
        # TODO: move to function?
        files_in_db = self._get_project_files()
        LOG.debug("files in the db: %s", files_in_db)

        do_fail = False
        # Gather data info ########################### Gather data info #
        # Iterate through all user specified paths
        for d in data_list:

            # Throw error if there are duplicate files
            if d in all_files or Path(d).resolve() in all_files:
                sys.exit(
                    exceptions_ds.printout_error(
                        f"The path to file {d} is listed multiple "
                        "times, please remove path dublicates.")
                )

            # Get file info ############################# Get file info #
            if self.method == "get":
                iteminfo = self._get_download_info(
                    item=d,
                    files_in_db=files_in_db,
                    do_fail=do_fail
                )

                # Save to failed dict or delivery dict
                if len(iteminfo) == 1 and d in iteminfo:    # File
                    if not iteminfo[d]["proceed"]:
                        initial_fail.update(iteminfo)
                        if self.break_on_fail:
                            do_fail = True
                        continue

                    all_files.update(iteminfo)
                else:                                       # Folder
                    for f in iteminfo:
                        if not iteminfo[f]["proceed"]:
                            initial_fail[f] = iteminfo[f]
                            if self.break_on_fail:
                                do_fail = True
                            continue

                        all_files[f] = iteminfo[f]

            elif self.method == "put":
                curr_path = Path(d).resolve()   # Full path to data

                # Get info on files within folder
                if curr_path.is_dir():
                    dir_info, dir_fail = file_handler.get_dir_info(
                        folder=curr_path,
                        do_fail=do_fail
                    )
                    initial_fail.update(dir_fail)   # Not to be delivered
                    all_files.update(dir_info)      # To be delivered
                    continue

                # Get info for individual files
                file_info = file_handler.get_file_info(
                    file=curr_path, in_dir=False, do_fail=do_fail
                )
                if not file_info["proceed"]:
                    # Don't deliver --> save error message
                    initial_fail[curr_path] = file_info
                    if self.break_on_fail:
                        do_fail = True
                        continue
                else:
                    # Deliver --> save info
                    all_files[curr_path] = file_info

        if self.method == "put":
            for file, info in list(all_files.items()):
                # Cancel if delivery tagged as failed
                if do_fail:
                    initial_fail[file] = {
                        **all_files.pop(file),
                        "error": ("Break on fail specified and one fail "
                                  "occurred. Cancelling delivery.")
                    }
                    continue

                # Check if the "bucketfilename" exists in database (name col)
                # and continue if not or if overwrite option specified
                if info["path_in_db"] in files_in_db:
                    if not self.overwrite:
                        LOG.info("'%s' already exists in database", file)
                        initial_fail[file] = {
                            **all_files.pop(file),
                            "error": "File already exists in database"
                        }
                    else:
                        LOG.info("--overwrite specified - "
                                 "performing delivery of '%s'", file)
                        continue

                    if self.break_on_fail:
                        do_fail = True
                        continue
                else:
                    with s3_connector.S3Connector(bucketname=self.bucketname,
                                                  project=self.s3project) \
                            as s3_conn:
                        # Check if file exists in bucket already
                        in_bucket, _ = s3_conn.file_exists_in_bucket(
                            info["path_in_bucket"]
                        )
                        LOG.debug("File: %s \t In bucket: %s", file, in_bucket)

                        # Error if the file exists in bucket, but not in the db
                        if in_bucket:
                            initial_fail[file] = {
                                **all_files.pop(file),
                                "error": (
                                    f"""File '{file.name}' already exists in
                                    bucket, but does NOT exist in database.
                                    Delivery cancelled, contact support."""
                                )
                            }
                            if self.break_on_fail:
                                do_fail = True

        # --------------------------------------------------------- #

        return all_files, initial_fail

    def _finalize(self, info: dict):
        """Makes sure that the file is not in bucket or db and deletes
        if it is.

        Args:
            file (Path):    Path to file
            info (dict):    Info about file --> don't use around with real dict

        """

        # Downloading ############## Delete local ############### Downloading #
        if self.method == "get":
            if "path_in_bucket" in info:
                file_handler.file_deleter(file=info["path_in_temp"])
                return

        # Uploading ########### Delete local and remote ########### Uploading #
        # Delete local encrypted
        if "encrypted_file" in info:
            if info["encrypted_file"] != Path("."):
                file_handler.file_deleter(file=info["encrypted_file"])

        # NOTE: Add check here for if actually uploaded etc?
        # Delete from S3 if uploaded but not in database
        # with s3_connector.S3Connector(bucketname=self.bucketname,
        #                               project=self.s3project) as s3_conn:
        #     if ("upload" in info and info["upload"]["finished"]
        #             and "database" in info
        #             and not info["database"]["finished"]):
        #         try:
        #             s3_conn.delete_item(key=info["path_in_bucket"])
        #         except botocore.client.ClientError as e:
        #             LOG.warning(e)

    def _get_download_info(self, item: str, files_in_db: dict, do_fail: bool) \
            -> (dict):
        """Gets info on file in database and checks if
        item exists in S3 bucket.

        Args:
            item (str):   File or folder to download

        Returns:
            dict: Information on if file can be downloaded or not

        """

        # Variables ################################# Variables #
        # General
        proceed = True      # To proceed with download or not
        in_db = False       # If item in db or not
        none_in_bucket = True   # If none of the items are in the s3 bucket
        to_download = {}    # Files to download
        error = ""          # Error message

        # Info about steps
        gen_finfo = {"download": {"in_progress": False,
                                  "finished": False},
                     "decryption": {"in_progress": False,
                                    "finished": False},
                     "database": {"in_progress": False,
                                  "finished": False}}
        # ----------------------------------------------------- #

        in_directory = False
        # If no suffixes assuming folder and adding trailing slash
        # if not Path(item).suffixes:
        #     item = os.path.join(item, "")
        #     in_directory = True

        # Check for file starting with the file/folder name
        # for file in files_in_db:
        #     print(file)
        tot_size = 0
        for file in files_in_db:
            # Get info on file
            if do_fail:
                error = "Break on fail specified and one fail occurred. " + \
                    "Cancelling delivery."
                LOG.info(error)
                return {item: {"proceed": False, "error": error,
                               "in_directory": in_directory,
                               "local_dir_name": item if in_directory else None}}

            # The user specified item is a file if it matches the name in db
            # or a folder/directory if it starts with the directory_path in db
            # print(file, item, files_in_db)
            if file == item:    # File
                # Temporary cap
                tot_size += int(files_in_db[file]["size_enc"])
                if tot_size > 700e9:
                    sys.exit(
                        exceptions_ds.printout_error(
                            "Too much data. Cap set at 700 GB."
                        )
                    )

                # print("exists")
                to_download[file] = {
                    **files_in_db[file],
                    **gen_finfo
                }
                in_db = True

                # Check if the file was uploaded as a part of a directory
                # in_directory = to_download[file]["directory_path"] != "."
                in_directory = False

                file_path = Path(file)
                full_suffixes = "".join(file_path.suffixes) + \
                    files_in_db[file]["extension"]
                path_in_temp = DIRS[1] / file_path.with_suffix(full_suffixes)

                # Save file info
                to_download[file].update({
                    "path_in_temp": path_in_temp,  # Path in tempdir
                    "path_in_bucket": file_path.with_suffix(full_suffixes),
                    "in_directory": in_directory,       # If in dir
                    "local_dir_name": None,
                    "proceed": proceed,     # If ok to proceed with deliv
                    "error": error          # Error message, "" if none
                })
            # Folder/Directory
            elif files_in_db[file]["directory_path"].startswith(item):
                to_download[file] = {
                    **files_in_db[file],
                    **gen_finfo
                }

                in_db = True

                # Check if the file was uploaded as a part of a directory
                # in_directory = to_download[file]["directory_path"] != "."
                in_directory = True

                file_path = Path(file)
                full_suffixes = "".join(file_path.suffixes) + \
                    files_in_db[file]["extension"]
                path_in_temp = DIRS[1] / file_path.with_suffix(full_suffixes)

                # Save file info
                to_download[file].update({
                    "path_in_temp": path_in_temp,
                    # Path in tempdir
                    "path_in_bucket": file_path.with_suffix(full_suffixes),
                    "in_directory": in_directory,       # If in dir
                    "local_dir_name": item,
                    "proceed": proceed,     # If ok to proceed with deliv
                    "error": error          # Error message, "" if none
                })

        # No delivery if the item doesn't exist in the database
        if not in_db:
            error = f"Item: {item} -- not in database"
            LOG.warning(error)
            return {item: {"proceed": False, "error": error,
                           "in_directory": in_directory,
                           "dir_name": item if in_directory else None}}

        # Check S3 bucket for item(s)
        with s3_connector.S3Connector(bucketname=self.bucketname,
                                      project=self.s3project) as s3_conn:

            # If folder - can contain more than one
            for file in to_download:
                in_bucket, s3error = s3_conn.file_exists_in_bucket(
                    key=str(to_download[file]["path_in_bucket"]))

                if not in_bucket:
                    error = (f"File '{file}' in database but NOT in S3 bucket."
                             f"Error in delivery system! {s3error}")
                    LOG.warning(error)
                    to_download[file].update({"proceed": False,
                                              "error": error})
                else:
                    none_in_bucket = False   # There are files in the bucket

            # Error if none of the files were in S3 bucket
            if none_in_bucket:
                error = (f"Item: {item} -- not in S3 bucket, but in database "
                         f"-- Error in delivery system!")
                LOG.warning(error)
                return {item: {"proceed": False, "error": error}}

        return to_download

    def _get_project_files(self):
        """Get all files delivered within the specified project.

        Returns:
            json: The API response contain all file information
        """

        # Perform request to ProjectFiles - list all files connected to proj
        args = {"token": self.token}
        req = ENDPOINTS["project_files"] + self.project_id + "/listfiles"
        response = requests.get(req, params=args)

        # If request error - cancel
        if not response.ok:
            sys.exit(
                exceptions_ds.printout_error(
                    f"{response.status_code} - {response.reason}:\n{req}"
                )
            )

        # Get json response if request ok
        resp_json = response.json()
        if not resp_json["access_granted"]:
            sys.exit(
                exceptions_ds.printout_error(resp_json["message"])
            )

        # Get all project files from response
        return resp_json["files"]

    ##################
    # Public Methods #
    ##################

    def finalize_delivery(self, file: str, fileinfo: dict) -> (tuple):
        """Finalizes delivery after download from s3.

        Decrypts, decompresses (if compressed in DS), and checks integrity.

        Args:
            file (str):         Path to file
            fileinfo (dict):    Information on file

        Return:
            tuple:   Info on finalized file
                bool:   True if decryption etc successful\n
                str:    Path to new, delivered and decrypted file\n
                str:    Error message, "" if none\n

        """

        # If DS noted cancelation of file -- quit and move on
        if not fileinfo["proceed"]:
            return False, ""

        # Set file processing as in progress
        self.set_progress(item=file, decryption=True, started=True)

        # Decrypt etc
        info = file_handler.reverse_processing(file=file, file_info=fileinfo,
                                               keys=(self.public, self.private))

        return info

    def prep_upload(self, path: Path, path_info: dict) -> (tuple):
        """Prepares the files for upload.

        Checks if the file should be delivered, sets the current process and
        processes the files.

        Args:
            path (Path):        Path to file
            path_info (dict):   Info on file

        Returns:
            tuple:  Info on success and info
                bool:   True if processing successful\n
                Path:   Path to processed file\n
                int:    Size of processed file\n
                bool:   True if file compressed by the delivery system\n
                bytes:  Public key needed for file decryption\n
                bytes:  Salt needed for shared key derivation\n
                str:    Error message, "" if none\n
        """

        # If DS noted cancelation of file -- quit and move on
        if not path_info["proceed"]:
            return False, Path(""), 0, False, "", b""

        # Set file processing as in progress
        self.set_progress(item=path, processing=True, started=True)

        # Begin processing incl encryption
        info = file_handler.process_file(file=path,
                                         file_info=path_info,
                                         peer_public=self.public)

        return info

    def set_progress(self, item: Path, processing: bool = False,
                     upload: bool = False, download: bool = False,
                     decryption: bool = False, db: bool = False,
                     started: bool = False, finished: bool = False):
        """Set progress of file to in progress or finished, regarding
        the file checks, processing, upload or database.

        Args:
            item (Path):        Path to file being handled
            processing (bool):  True if processing in progress or finished
            upload (bool):      True if upload in progress or finshed
            db (bool):          True if database update in progress or finished
        """
        # TODO (ina): Merge with update_progress_bar?
        # Which process to update
        to_update = ""

        if self.method == "put":
            if processing:
                to_update = "processing"
            elif upload:
                to_update = "upload"
            elif db:
                to_update = "database"
        elif self.method == "get":
            if download:
                to_update = "download"
            elif decryption:
                to_update = "decryption"
            elif db:
                to_update = "database"

        # Exit if trying to update something else
        if to_update == "":
            raise exceptions_ds.DeliverySystemException(
                "Trying to update progress on forbidden process."
            )

        # Update the progress
        if started:
            self.data[item][to_update].update({"in_progress": started,
                                               "finished": not started})
            return

        if finished:
            self.data[item][to_update].update({"in_progress": not finished,
                                               "finished": finished})
            return

        LOG.exception("Data delivery information failed to update")

    def update_delivery(self, file: Path, updinfo: dict) -> (bool):
        """Updates data delivery information dictionary.

        Updates the data dictionary with information from previous step, e.g.
        processing or upload etc.

        Args:
            file (Path):        The files info to be updated
            updinfo (dict):     The dictionary to update the info with

        Returns:
            bool:   True if to continue with delivery

        Raises:
            DeliverySystemException:  Data dictionary update failed

        """

        # Variables ############################################### Variables #
        critical_op = "upload" if self.method == "put" else "download"
        all_info = self.data[file]  # All info on file
        # ------------------------------------------------------------------- #

        # If cancelled by another file set as not proceed and add error message
        if not all_info["proceed"]:
            updinfo.update({"proceed": all_info["proceed"],
                            "error": all_info["error"]})

        # Fail file if delivery cancelled by DS update dictionary
        if not updinfo["proceed"]:
            # If failed file in directory, check if to fail all files or not
            if all_info["in_directory"]:
                local_dir_name = all_info["local_dir_name"]

                # Update current file
                self.data[file].update({"proceed": False,
                                        "error": updinfo["error"]})

                # If break-on-fail flag --> fail all files in directory
                if self.break_on_fail:
                    for path, info in self.data.items():
                        # If within shared folder and upload not in progress or
                        # finished -- set current file error and cancel
                        if path != file and info["proceed"] and \
                                info["local_dir_name"] == local_dir_name:
                            if (self.method == "get" and
                                    not all([info[critical_op]["in_progress"],
                                             info[critical_op]["finished"]])) or \
                                    (self.method == "put" and
                                     not (info[critical_op]["in_progress"] or
                                          info[critical_op]["finished"])):

                                self.data[path].update({
                                    "proceed": False,
                                    "error": ("break-on-fail chosen --"
                                            f"{updinfo['error']}")
                                })
                    return False

            # If individual file -- cancel this specific file only
            self.data[file].update({"proceed": False,
                                    "error": updinfo["error"]})
            return False

        # If file to proceed, update file info
        try:
            self.data[file].update(updinfo)
        except exceptions_ds.DeliverySystemException as dex:
            LOG.exception("Data delivery information failed to "
                          "update: %s", dex)

        return True

    ################
    # Main Methods #
    ################
    def get(self, path: str, path_info: dict) -> (bool, str):
        """Downloads specified data from S3 bucket.

        Args:
            path (str):         File to be downloaded
            path_info (dict):   Name of downloaded file

        Returns:
            tuple:  Info on download success
                bool:   True if downloaded\n
                str:    Error message, "" if none\n

        Raises:
            OSError:                        Creating directory failed
            botocore.client.ClientError:    Failed download

        """

        # Quit and move on if DS noted cancelation of file
        if not path_info["proceed"]:
            return False, ""

        # Set file processing as in progress
        self.set_progress(item=path, download=True, started=True)

        # New temporary sub directory
        new_dir = DIRS[1] / Path(path_info["directory_path"])

        # Create new temporary subdir if doesn't exist
        if not new_dir.exists():
            try:
                new_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                # If failed to create -- cancel file
                error = (f"File: {path}. Creating tempdir failed: {new_dir}. "
                         f"Error: {e}")
                LOG.exception(error)
                return False, error
        # LOG.debug(f"new_dir: {new_dir}")

        # DOWNLOAD START ##################################### DOWNLOAD START #
        with s3_connector.S3Connector(bucketname=self.bucketname,
                                      project=self.s3project) as s3_conn:

            # Download file from S3
            try:
                s3_conn.resource.meta.client.download_file(
                    Bucket=s3_conn.bucketname,
                    Key=str(path_info["path_in_bucket"]),
                    Filename=str(path_info["path_in_temp"]),
                    Callback=ProgressPercentage(
                        str(Path(path).name),
                        path_info["size_enc"],
                        get=True
                    )
                )
            except botocore.client.ClientError as e:
                # Upload failed -- return error message and move on
                error = (f"File: {path}. Download failed: {e}")
                LOG.exception(error)
                return False, error
            else:
                # Download successful
                LOG.info("File: '%s'. Download successful! File location: '%s'",
                         path, path_info["path_in_temp"])
                return True, ""
                # return False, "blablabla"

    def put(self, file: Path, fileinfo: dict) -> (bool, str):
        """Uploads specified data to the S3 bucket.

        Args:
            file (Path):       Path to original file
            fileinfo (dict):   Info on file

        Returns:
            tuple: Info on upload success
                bool:   True if upload successful\n
                str:    Error message, '' if none\n

        Raises:
            botocore.client.ClientError:  Upload failed
        """

        # Quit and move on if DS noted cancelation of file
        if not fileinfo["proceed"]:
            error = ""
            # Quit and move on if processing not performed
            if not fileinfo["processing"]["finished"]:
                error = (f"File: '{file}' -- File not processed (e.g. "
                         "encrypted). Bug in code. Moving on to next file.")
                LOG.critical(error)

            return False, error

        # Set delivery as in progress
        self.set_progress(item=file, upload=True, started=True)

        # UPLOAD START ######################################### UPLOAD START #
        with s3_connector.S3Connector(bucketname=self.bucketname,
                                      project=self.s3project) as s3_conn:

            # Upload file
            try:
                # TODO (ina): Check if use object instead?
                s3_conn.resource.meta.client.upload_file(
                    Filename=str(fileinfo["encrypted_file"]),
                    Bucket=s3_conn.bucketname,
                    Key=fileinfo["path_in_bucket"],
                    Callback=ProgressPercentage(
                        filename=str(file.name),
                        ud_file_size=float(os.path.getsize(
                            str(fileinfo["encrypted_file"])))
                    )
                )
            except botocore.client.ClientError as e:
                # Upload failed -- return error message and move on
                error = (f"File: {file}, Uploaded: "
                         f"{fileinfo['encrypted_file']} -- "
                         f"Upload failed! -- {e}")
                LOG.exception(error)
                return False, error

            return True, ""


class ProgressPercentage(object):

    def __init__(self, filename, ud_file_size, get=False):
        self._filename = filename
        self._size = ud_file_size
        self._seen_so_far = 0
        self._download = get
        self._lock = threading.Lock()
        # print(f"\n\n\n\n\n{self._filename}\n\n\n\n\n")

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            update_progress_bar(file=self._filename,
                                status="d" if self._download else "u",
                                perc=percentage)

# EXCEPTIONS ##################################################### EXCEPTIONS #


class DeliverySystemException(Exception):
    """Errors regarding Delivery Portal access etc"""


# DSUSER ############################################################## DSUER #


# TODO (ina): Remove DSuser or use in better way
class _DSUser:
    """
    A Data Delivery System user.

    Args:
        username (str):   Delivery System username
        password (str):   Delivery System password

    Attributes:
        username (str): Delivery System username
        password (str): Delivery System password
        id (str):       User ID
        role (str):     Facility or researcher
    """
    # NOTE: Remove user class?

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.id = None
        self.role = None


def save_failed(file: Path, file_info: dict):
    """Saves file information to file in logs folder.

    Args:
        file:       Path to file (source)
        file_info:  Info which failed to be saved/used
    """

    filename = DIRS[-1] / Path("important_give_to_DC.json")
    for x in file_info:
        if isinstance(file_info[x], Path):
            file_info[x] = str(file_info[x])

    try:
        with filename.open(mode="a+") as outfile:
            json.dump({str(file): file_info}, outfile)
    except IOError as e:
        sys.exit(exceptions_ds.printout_error(str(e)))


def update_progress_bar(file, status: str, perc=0.0):
    """Update the status of the file and print out progress.

    Updates the delivery status of the current file to the options found in
    STATUS_DICT: 'Waiting to start...', 'Encrypting...', 'Decrypting...',
    'Uploading...', 'Downloading...', and two unicode symbols: A check mark,
    and a cross - symbolizing a finished delivery or a failure, respectively.

    Args:
        file:             File to update progress on
        status (str):     Which stage the delivery is on
        perc:             Upload/Download percentage, 0.0 if not upl/dwnld

    """

    # Percentage string to print
    perc_print = ""

    global PROGRESS_DF  # Make variable editable
    # print(f"\n\n\n\n\n\n\n{file}\n\n\n\n\n\n\n")
    PROGRESS_DF.loc[
        (PROGRESS_DF.File == Path(file).name), "     Status     "
    ] = STATUS_DICT[status]

    # Change the status/progress fields if the upload/download has begun
    if perc != 0.0:
        perc_print = "%.2f%%" % (perc)

        if perc_print == "100.00%":     # Empty status if finished
            PROGRESS_DF.loc[
                (PROGRESS_DF.File == str(file)), "     Status     "
            ] = ""

        if status == "dec":     # Cover up previous text with empty if decrypt
            PROGRESS_DF.loc[
                (PROGRESS_DF.File == str(file)),
                "Upload/Download Progress          "
            ] = " "*18
        else:                   # Update progress percentages if upl/dwnld
            PROGRESS_DF.loc[
                (PROGRESS_DF.File == str(file)),
                "Upload/Download Progress          "
            ] = perc_print + " "*10

    sys.stdout.write(
        "\033[F"*(len(PROGRESS_DF)+1) +
        PROGRESS_DF.to_string(index=False) +
        "\n"
    )
