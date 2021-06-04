"""Base class for the DDS CLI. Verifies the users access to the DDS."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import inspect
import logging
import os
import pathlib
import traceback

# Installed
import getpass
import requests
import rich
import simplejson

# Own modules
import dds_cli.directory
import dds_cli.timestamp
from dds_cli import DDSEndpoint
from dds_cli import file_handler as fh
from dds_cli import s3_connector as s3
from dds_cli import user

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# RICH CONFIG ################################################### RICH CONFIG #
###############################################################################

console = rich.console.Console()

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def attempted_operation():
    """Gets the command entered by the user (e.g. put)."""

    curframe = inspect.currentframe()
    return inspect.getouterframes(curframe, 2)[3].function


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DDSBaseClass:
    """Data Delivery System base class. For common operations."""

    def __init__(
        self,
        username=None,
        password=None,
        config=None,
        project=None,
        ignore_config_project=False,
        dds_directory: pathlib.Path = None,
    ):

        # Get attempted operation e.g. put/ls/rm/get
        self.method = attempted_operation()
        LOG.debug(f"Attempted operation: {self.method}")

        # Use user defined festination if any specified
        if self.method in ["get", "put"]:
            self.dds_directory = dds_cli.directory.DDSDirectory(
                path=dds_directory
                if dds_directory
                else pathlib.Path.cwd()
                / pathlib.Path(f"DataDelivery_{dds_cli.timestamp.TimeStamp().timestamp}")
            )

        # Keyboardinterrupt
        self.stop_doing = False

        # Verify that user entered enough info
        username, password, self.project = self.__verify_input(
            username=username,
            password=password,
            config=config,
            project=project,
            ignore_config_project=ignore_config_project,
        )

        # Authenticate the user and get the token
        dds_user = user.User(username=username, password=password, project=self.project)
        self.token = dds_user.token

        LOG.debug(f"Method: {self.method}, Project: {self.project}")
        # Project access only required if trying to upload, download or list
        # files within project
        if self.method in ["put", "get"] or (
            self.method in ["ls", "rm"] and self.project is not None
        ):
            self.token = self.__verify_project_access()

            if self.method in ["put", "get"]:
                self.keys = self.__get_project_keys()

                self.status = dict()
                self.filehandler = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb, max_fileerrs: int = 40):

        # Don't clean up if we hit an exception
        if exc_type is not None:
            return False

        if self.method in ["put", "get"]:
            self.__printout_delivery_summary()

        return True

    # Private methods ############################### Private methods #
    def __verify_input(
        self,
        username=None,
        password=None,
        config=None,
        project=None,
        ignore_config_project=False,
    ):
        """Verifies that the users input is valid and fully specified."""

        LOG.debug("Verifying the user input...")

        # Get contents from file
        if config is not None:
            # Get contents from file
            contents = fh.FileHandler.extract_config(configfile=config)

            # Get user credentials and project info if not already specified
            if username is None and "username" in contents:
                username = contents["username"]
            if password is None and "password" in contents:
                password = contents["password"]
            if not ignore_config_project:
                if (
                    project is None
                    and "project" in contents
                    and self.method in ["put", "get", "ls"]
                ):
                    project = contents["project"]

        LOG.debug(f"Username: {username}, Project ID: {project}")

        # Username and project info is minimum required info
        if self.method in ["put", "get"] and project is None:
            console.print(
                "\n:warning: Data Delivery System project information is missing. :warning:\n"
            )
            os._exit(1)
        if username is None:
            console.print("\n:warning: Data Delivery System options are missing :warning:\n")
            os._exit(1)

        # Set password if missing
        if password is None:
            password = getpass.getpass()
            # password = "password"  # TODO: REMOVE - ONLY FOR DEV

        LOG.debug("User input verified.")

        return username, password, project

    def __verify_project_access(self):
        """Verifies that the user has access to the specified project."""

        LOG.debug(f"Verifying access to project {self.project}...")

        # Perform request to API
        try:
            response = requests.get(
                DDSEndpoint.AUTH_PROJ,
                params={"method": self.method},
                headers=self.token,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            LOG.warning(err)
            raise SystemExit from err

        # Problem
        if not response.ok:
            console.print(
                f"\n:no_entry_sign: Project access denied: {response.text} :no_entry_sign:\n"
            )
            os._exit(1)

        try:
            dds_access = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        # Access not granted
        if not dds_access["dds-access-granted"] or "token" not in dds_access:
            console.print("\n:no_entry_sign: Project access denied :no_entry_sign:\n")
            os._exit(1)

        LOG.debug(f"User has been granted access to project {self.project}")

        return {"x-access-token": dds_access["token"]}

    def __get_project_keys(self):
        """Get public and private project keys depending on method."""

        # Project public key required for both put and get
        public = self.__get_key()

        # Project private only required for get
        private = self.__get_key(private=True) if self.method == "get" else None

        return private, public

    def __get_key(self, private: bool = False):
        """Get public key for project."""

        key_type = "private" if private else "public"
        # Get key from API
        try:
            response = requests.get(
                DDSEndpoint.PROJ_PRIVATE if private else DDSEndpoint.PROJ_PUBLIC,
                headers=self.token,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            LOG.fatal(str(err))
            raise SystemExit from err

        if not response.ok:
            console.print(
                f"\n:no_entry_sign: Project access denied: No {key_type} key. {response.text} :no_entry_sign:\n"
            )
            os._exit(1)

        # Get key from response
        try:
            project_public = response.json()
        except simplejson.JSONDecodeError as err:
            LOG.fatal(str(err))
            raise SystemExit from err

        if key_type not in project_public:
            console.print(
                "\n:no_entry_sign: Project access denied: No {key_type} key. :no_entry_sign:\n"
            )
            os._exit(1)

        return project_public[key_type]

    def __printout_delivery_summary(self, max_fileerrs: int = 40):
        """Print out the delivery summary if any files were cancelled."""

        any_failed = self.__collect_all_failed()

        # Clear dict to not take up too much space
        self.filehandler.failed.clear()

        if any_failed:
            intro_error_message = (
                f"Errors occurred during {'upload' if self.method == 'put' else 'download'}"
            )

            # Save to file and print message if too many failed files,
            # otherwise create and print tables
            outfile = self.dds_directory.directories["LOGS"] / pathlib.Path(
                "dds_failed_delivery.txt"
            )

            fh.FileHandler.save_errors_to_file(file=outfile, info=any_failed)

            # Only print out if the number of cancelled files are below a certain thresh
            if len(any_failed) < max_fileerrs:
                console.print(f"{intro_error_message}:")

                # Cancelled files in root
                files_table, additional_info = fh.FileHandler.create_summary_table(
                    all_failed_data=any_failed, upload=bool(self.method == "put")
                )
                if files_table is not None:
                    console.print(rich.padding.Padding(files_table, 1))

                # Cancelled files in different folders
                folders_table, additional_info = fh.FileHandler.create_summary_table(
                    all_failed_data=any_failed,
                    get_single_files=False,
                    upload=bool(self.method == "put"),
                )
                if folders_table is not None:
                    console.print(rich.padding.Padding(folders_table, 1))
                if additional_info:
                    console.print(rich.padding.Padding(additional_info, 1))

            console.print(f"{intro_error_message}. See {outfile} for more information.")

            if any([y["failed_op"] in ["add_file_db"] for _, y in self.status.items()]):
                console.print(
                    rich.padding.Padding(
                        "One or more files where uploaded but may not have been added to "
                        "the db. Contact support and supply the logfile found in "
                        f"{self.dds_directory.directories['LOGS']}",
                        1,
                    )
                )

        else:
            # Printout if no cancelled/failed files
            LOG.debug(f"\n{'Upload' if self.method == 'put' else 'Download'} completed!\n")

        if self.method == "get" and len(self.filehandler.data) > len(any_failed):
            LOG.info(f"Any downloaded files are located: {self.filehandler.local_destination}.")

    def __collect_all_failed(self, sort: bool = True):
        """Put cancelled files from status in to failed dict and sort the output."""

        # Transform all items to string
        self.filehandler.data = {
            str(file): {str(x): str(y) for x, y in info.items()}
            for file, info in list(self.filehandler.data.items())
        }
        self.status = {
            str(file): {str(x): str(y) for x, y in info.items()}
            for file, info in list(self.status.items())
        }

        # Get cancelled files
        self.filehandler.failed.update(
            {
                file: {
                    **info,
                    "message": self.status[file]["message"],
                    "failed_op": self.status[file]["failed_op"],
                }
                for file, info in self.filehandler.data.items()
                if self.status[file]["cancel"] in [True, "True"]
            }
        )

        # Sort by which directory the files are in
        return (
            sorted(
                sorted(self.filehandler.failed.items(), key=lambda g: g[0]),
                key=lambda f: f[1]["subpath"],
            )
            if sort
            else self.filehandler.failed
        )

    # Public methods ################################# Public methods #
    def verify_bucket_exist(self):
        """Check that s3 connection works, and that bucket exists."""

        LOG.debug("Verifying and/or creating bucket.")

        with s3.S3Connector(project_id=self.project, token=self.token) as conn:

            if None in [conn.safespring_project, conn.keys, conn.bucketname, conn.url]:
                console.print(f"\n:warning: {conn.message} :warning:\n")
                os._exit(1)

            bucket_exists = conn.check_bucket_exists()
            LOG.debug(f"Bucket exists: {bucket_exists}")
            if not bucket_exists:
                LOG.debug("Attempting to create bucket...")
                _ = conn.create_bucket()

        LOG.debug("Bucket verified.")

        return True
