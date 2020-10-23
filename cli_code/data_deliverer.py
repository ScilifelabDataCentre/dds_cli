"""Data Deliverer, used by the Data Delivery System CLI.

Handled the login of all users, performs checks on the data and handles the
upload and download of all files. Also keeps track of the delivery progress.
"""

# TODO(ina): Fix or ignore "too-many-attributes" etc pylint error

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import threading
import pandas as pd
from pathlib import Path
import collections
import json
import logging
import os
import sys
import textwrap
import traceback
import requests

# Installed
import botocore.client
import prettytable

# Own modules
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
               "f": u"\u2705",
               "e": u"\u274C",
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

progress_df = None


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
        self.project_id = project_id        # Project ID - not S3
        self.project_owner = project_owner  # User, not facility
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
                password=password
            )

        # Get access to DS -- returns json format with access, user_id,
        # project_id, s3_id, and error.
        delivery_info = self._check_ds_access()
        self.user.id = delivery_info["user_id"]

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
                self.project_id, self.user)

        # Start progress info printout
        if self.data:
            global TO_PRINT
            global PROGRESS
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
        # NOTE: Remove this and just update the progress instead?
        # Also, definitely needs to be checked and simplified
        # TODO: Add check for if uploaded - single file uploaded among failed
        #       folder is not added to final printout

        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        # Tables ##################################################### Tables #
        # Folders
        folders_table = prettytable.PrettyTable(
            ["Directory", "File", "Delivered", "Error"]
        )
        folders_table.padding_width = 2
        folders_table.align["File"] = "r"
        folders_table.align["Error"] = "l"

        # Files
        files_table = prettytable.PrettyTable(
            ["File", "Delivered", "Error"]
        )
        files_table.align["File"] = "r"
        files_table.align["Error"] = "l"

        # Reduce the text width and wraps in column
        wrapper = textwrap.TextWrapper(width=80)
        # ------------------------------------------------------------------- #

        # Variables ############################################### Variables #
        folders = {}            # Already checked folders
        are_folders = False     # True if folders have been delivered/failed
        are_files = False       # True if files have been delivered/failed

        # Check if uploaded or downloaded successfully
        critical_op = "upload" if self.method == "put" else "download"
        # ------------------------------------------------------------------- #

        # Iterate through items ####################### Iterate through items #
        # Failed items - on initial check
        for file, info in self.failed.items():
            # Remove encrypted files
            self._finalize(info=info)

            if info["in_directory"] and info["dir_name"] not in folders:
                are_folders = True  # Note that folders have been delivered

                # Get all failed files in folder
                folders[info["dir_name"]] = {
                    f: val for f, val in self.failed.items()
                    if val["in_directory"] and
                    val["dir_name"] == info["dir_name"]
                }
                # Add folder name to table
                folders_table.add_row(
                    [str(info["dir_name"]) + "\n", "", "", ""]
                )
                # Add files in folder to table
                for f, v in folders[info["dir_name"]].items():
                    file_loc = \
                        (v["directory_path"] if "directory_path" in v
                         else
                         file_handler.get_root_path(
                             file=f, path_base=v["dir_name"].name)) \
                        / Path(Path(f).name)
                    folders_table.add_row(
                        ["",
                         file_loc,
                         "NO",
                         "\n".join(wrapper.wrap(v["error"])) + "\n"]
                    )

            elif not info["in_directory"]:
                are_files = True    # Note that files have been delivered
                # Add file to table
                files_table.add_row(
                    [file,
                     "NO",
                     "\n".join(wrapper.wrap(info["error"])) + "\n"]
                )

        # Items passing the initial check - successfully delivered AND failed
        for file, info in self.data.items():
            # Remove encrypted files
            self._finalize(info=info)

            # Get all files in folder
            if info["in_directory"] and info["dir_name"] not in folders:
                are_folders = True
                folders[info["dir_name"]] = {
                    f: val for f, val in self.data.items()
                    if val["in_directory"] and
                    val["dir_name"] == info["dir_name"]
                }
                # Add folder name to table
                folders_table.add_row(
                    [info["dir_name"], "", "", ""]
                )
                # Add files in folder to table
                for f, v in folders[info["dir_name"]].items():
                    folders_table.add_row(
                        ["",
                            str(v["directory_path"] / Path(Path(f).name)),
                            "YES"
                            if all([v["proceed"], v[critical_op]["finished"],
                                    v["database"]["finished"]]) else "NO",
                            "\n".join(wrapper.wrap(v["error"])) + "\n"]
                    )

            elif not info["in_directory"]:
                are_files = True
                LOG.debug(are_files)
                # Add file to table
                files_table.add_row(
                    [str(file),
                        "YES"
                        if all([info["proceed"], info[critical_op]["finished"],
                                info["database"]["finished"]]) else "NO",
                        "\n".join(wrapper.wrap(info["error"])) + "\n"])
        # ------------------------------------------------------------------- #

        # FINAL MESSAGE ####################################### FINAL MESSAGE #
        print("* * * * * * * * * * DELIVERY COMPLETED! * * * * * * * * * *")
        print(
            f"\n################### FOLDERS DELIVERED ###################"
            f"\n{folders_table}\n" if are_folders else "\n"
        )
        print(
            f"\n#################### FILES DELIVERED ####################"
            f"\n{files_table}\n" if are_files else "\n"
        )
        return True

    ###################
    # Private Methods #
    ###################

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
        if self.method == "put":
            LOGIN_BASE = ENDPOINTS["f_login"]
            args = {"username": self.user.username,
                    "password": self.user.password,
                    "project": self.project_id,
                    "owner": self.project_owner}
        elif self.method == "get":
            LOGIN_BASE = ENDPOINTS["u_login"]
            args = {"username": self.user.username,
                    "password": self.user.password,
                    "project": self.project_id}

        # Request to get access
        response = requests.post(LOGIN_BASE, params=args)
        # print(response.text)
        if not response.ok:
            sys.exit(
                exceptions_ds.printout_error(
                    """Something wrong. Could not access api/db during access
                    check. Login failed. Delivery cancelled."""
                )
            )

        json_response = response.json()
        # Quit if user not granted Delivery System access
        if not json_response["access"]:
            sys.exit(
                exceptions_ds.printout_error(
                    f"""Delivery System access denied!
                       Delivery cancelled. {json_response['error']}"""
                )
            )

        # Quit if project ID not matching
        if int(json_response["project_id"]) != self.project_id:
            sys.exit(
                exceptions_ds.printout_error(
                    """Incorrect project ID. System error.
                    Cancelling delivery."""
                )
            )

        return json_response

    def _check_user_input(self, creds, username, password) -> \
            (str, str, int, int):
        """Checks that the correct options and credentials are entered.

        Args:
            creds:      File containing the users DP username and password,
                        and the project relating to the upload/download.
                        Can be used instead of inputing the creds separately.
            username:   Delivery System username
            password:   Delivery System password

        Returns:
            tuple:  Info about user if all credentials specified
                username    (str):     Username\n
                password    (str):     Password\n
                project_id  (int):     Project ID\n
                owner_id    (int):     Owner ID\n
        """

        # No creds file -------- loose credentials -------- No creds file #
        # print(f"creds: {creds}")
        if creds is None:
            # Cancel delivery if username or password not specified
            if None in [username, password]:
                sys.exit(
                    exceptions_ds.printout_error(
                        """Delivery System login credentials not specified.
                           Enter --username/-u AND --password/-pw,
                           or --creds/-c.
                           For help: 'ds_deliver --help'."""
                    )
                )

            # Cancel delivery if project_id not specified
            if self.project_id is None:
                sys.exit(
                    exceptions_ds.printout_error(
                        """Project not specified. Enter project ID using
                           --project option or add to creds file using
                           --creds/-c option."""
                    )
                )

            # Assume current user is owner if no owner is set
            if not self.project_owner or self.project_owner is None:
                if self.method == "put":
                    sys.exit(
                        exceptions_ds.printout_error(
                            "You have not specified the project owner. \n"
                            "Cancelling delivery."
                        )
                    )
                # username, password, id, owner
                return username, password, self.project_id, username
            else:
                return username, password, self.project_id, self.project_owner

        # creds file ----------- credentials in it ----------- creds file #
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

        # Quit if not all credentials are entered
        if not all(c in credentials for c
                   in ["username", "password", "project"]):
            sys.exit(
                exceptions_ds.printout_error(
                    "The creds file does not contain all required information."
                )
            )

        # Save info from credentials file
        username = credentials["username"]
        password = credentials["password"]
        project_id = credentials["project"]

        # OK if owner specified
        if "owner" in credentials:
            return username, password, project_id, credentials["owner"]

        # Error if owner not specified and trying to put
        if (not self.project_owner or self.project_owner is None) \
                and self.method == "put":
            sys.exit(
                exceptions_ds.printout_error(
                    """Project owner not specified. Cancelling delivery."""
                )
            )

        return username, password, project_id, username

    def _create_progress_output(self) -> (str, dict):
        """Create list of files and the individual delivery progress.

        Returns:
            tuple:  Information on start status for all files

                str:    Progressinfo (all files) to print to console
                dict:   Files and their current delivery statuses

        """

        sys.stdout.write("\n")  # Space between command and any output

        # Set pandas to show all dataframe contents, no '...'
        pd.set_option("display.max_colwidth", -1)

        global progress_df  # Can edit global variable contents
        progress_df = pd.DataFrame(
            {"File": [str(Path(x).name) for x in self.data],
             "     Status     ": [STATUS_DICT["w"] for _, y in self.data.items()],
             "Upload/Download Progress          ": ["" for x in self.data]}
        )

        sys.stdout.write(f"{progress_df.to_string(index=False)}\n")

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
        all_files = dict()
        initial_fail = dict()

        data_list = list(data)

        in_db = False
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

        # Get all project files in db
        req = ENDPOINTS["project_files"] + f"/{self.project_id}"
        response = requests.get(req)
        if not response.ok:
            sys.exit(
                exceptions_ds.printout_error(
                    f"""{response.status_code} - {response.reason}:
                     \n{req}""")
            )

        # Get all project files from response
        files_in_db = response.json()
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
                    files_in_db=files_in_db["files"],
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
                file_info = file_handler.get_file_info(file=curr_path, in_dir=False,
                                                       do_fail=do_fail)
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
            # print(f"\nOverwrite? {self.overwrite}\n")
            for file, info in list(all_files.items()):
                if do_fail:
                    initial_fail[file] = {
                        **all_files.pop(file),
                        "error": ("Break on fail specified and one fail "
                                  "occurred. Cancelling delivery.")
                    }
                    continue

                if info["new_file"] in files_in_db["files"]:
                    in_db = True
                    # print(f"\nFile is in db? {in_db}\n")
                    if not self.overwrite:
                        LOG.info("'%s' already exists in database", file)
                        initial_fail[file] = {
                            **all_files.pop(file),
                            "error": "File already exists in database"
                        }
                    if self.break_on_fail:
                        do_fail = True
                        continue
                else:
                    with s3_connector.S3Connector(bucketname=self.bucketname,
                                                  project=self.s3project) \
                            as s3_conn:
                        # Check if file exists in bucket already
                        in_bucket, _ = s3_conn.file_exists_in_bucket(
                            info["new_file"]
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
            if "new_file" in info:
                file_handler.file_deleter(file=info["new_file"])
                return

        # Uploading ########### Delete local and remote ########### Uploading #
        # Delete local encrypted
        if "encrypted_file" in info:
            file_handler.file_deleter(file=info["encrypted_file"])

        # NOTE: Add check here for if actually uploaded etc?
        # Delete from S3 if uploaded but not in database
        with s3_connector.S3Connector(bucketname=self.bucketname,
                                      project=self.s3project) as s3_conn:
            if ("upload" in info and info["upload"]["finished"]
                    and "database" in info
                    and not info["database"]["finished"]):
                try:
                    s3_conn.delete_item(key=info["new_file"])
                except botocore.client.ClientError as e:
                    LOG.warning(e)

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
        if not Path(item).suffixes:
            item = os.path.join(item, "")
            in_directory = True

        # Check for file starting with the file/folder name
        for file in files_in_db:
            # Get info on file
            if do_fail:
                error = "Break on fail specified and one fail occurred. " + \
                    "Cancelling delivery."
                LOG.info(error)
                return {item: {"proceed": False, "error": error,
                               "in_directory": in_directory,
                               "dir_name": item if in_directory else None}}

            if file.startswith(item):
                to_download[file] = {
                    **files_in_db[file],
                    **gen_finfo
                }
                in_db = True

                # Check if the file was uploaded as a part of a directory
                in_directory = to_download[file]["directory_path"] != "."

                # Save file info
                to_download[file].update({
                    "new_file": DIRS[1] / Path(file),   # Path in tempdir
                    "in_directory": in_directory,       # If in dir
                    "dir_name": item if in_directory else None,
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
                in_bucket, s3error = s3_conn.file_exists_in_bucket(key=file)

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
                dir_name = all_info["dir_name"]

                # Update current file
                self.data[file].update({"proceed": False,
                                        "error": updinfo["error"]})

                # If break-on-fail flag --> fail all files in directory
                if self.break_on_fail:
                    for path, info in self.data.items():
                        # If within shared folder and upload not in progress or
                        # finished -- set current file error and cancel
                        if path != file and info["proceed"] and \
                            info["dir_name"] == dir_name \
                                and not all([info[critical_op]["in_progress"],
                                             info[critical_op]["finished"]]):

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
                    Key=path,
                    Filename=str(path_info["new_file"]),
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
                # Upload successful
                LOG.info("File: '%s'. Download successful! File location: '%s'",
                         path, path_info["new_file"])
                return True, ""

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
                s3_conn.resource.meta.client.upload_file(
                    Filename=str(fileinfo["encrypted_file"]),
                    Bucket=s3_conn.bucketname,
                    Key=fileinfo["new_file"],
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


def update_progress_bar(file, status: str, perc=0.0):
    """Update the status of the file and print out progress.

    Updates the delivery status of the current file to the options found in
    STATUS_DICT: 'Waiting to start...', 'Encrypting...', 'Decrypting...',
    'Uploading...', 'Downloading...', and two unicode symbols: A check mark,
    and a cross - symbolizing a finished delivery or a failure, respectively.

    Args:
        file:             File to update progress on
        status (str):     Which stage the delivery is on

    """

    perc_print = ""
    global progress_df
    progress_df.loc[(progress_df.File == str(file)),
                    "     Status     "] = STATUS_DICT[status]

    if perc != 0.0:
        perc_print = "%.2f%%" % (perc)
        if perc_print == "100.00%":
            progress_df.loc[(progress_df.File == str(file)),
                            "     Status     "] = ""

        if status == "dec":
            progress_df.loc[(progress_df.File == str(file)),
                            "Upload/Download Progress          "] = " "*18
        else:
            progress_df.loc[(progress_df.File == str(file)),
                            "Upload/Download Progress          "] = perc_print + " "*10

    # print(progress_df)
    sys.stdout.write("\033[F"*(len(progress_df)+1) +
                     progress_df.to_string(index=False) + "\n")
    # sys.exit()
    # file = str(file)    # For printing and len() purposes

    # # Change the status
    # PROGRESS[file]["status"] = STATUS_DICT[status]

    # # Line to update to in progress output
    # new_line = (f"{file}{int(FCOLSIZE-len(file)+1)*' '} "
    #             f"{int(SCOLSIZE/2-len(STATUS_DICT[status])/2)*' '}"
    #             f"{2*' '}{STATUS_DICT[status]}{2*' '}{perc}")

    # # If shorter line than before -> cover up previous text
    # diff = abs(len(PROGRESS[file]["line"]) - len(new_line))
    # new_line += diff*" " + "\n"

    # # Replace the printout and progress dict with the update
    # global TO_PRINT
    # TO_PRINT = TO_PRINT.replace(PROGRESS[file]["line"], new_line)
    # PROGRESS[file]["line"] = new_line

    # # Print the status
    # # sys.stdout.write("\033[F"*len(PROGRESS))   # Jump up to cover prev
    # sys.stdout.write(TO_PRINT)                 # Print new for all
