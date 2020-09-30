"""
Main class - Data Deliverer

Handles login of user, keeps track of data, uploads/downloads etc
"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import collections
import json
import logging
import os
import sys
import textwrap
import traceback
from pathlib import Path
import requests

# Installed
from prettytable import PrettyTable
from botocore.client import ClientError

# Own modules
from cli_code import DIRS, API_BASE
from cli_code.crypto_ds import (get_project_private)
from cli_code.database_connector import DatabaseConnector
from cli_code.exceptions_ds import (CouchDBException, DataException,
                                    DeliverySystemException, printout_error)
from cli_code.file_handler import (file_deleter, get_root_path,
                                   is_compressed, MAGIC_DICT,
                                   process_file, reverse_processing)
from cli_code.s3_connector import S3Connector

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #
###############################################################################

# NOTE: There may be issues with unicode and Windows - test and fix
# ns: not started, f: finished, e: error,
# enc: encrypting, dec: decrypting
# u: uploading, d: downloading
STATUS_DICT = {'w': "Waiting to start...", 'f': u'\u2705', 'e': u'\u274C',
               'enc': "Encrypting...", 'dec': "Decrypting...",
               'u': 'Uploading...', 'd': "Dowloading...", }

FCOLSIZE = 0
SCOLSIZE = 0

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DataDeliverer():
    '''
    Instanstiates the delivery by logging the user into the Delivery System,
    checking the users access to the specified project, and uploads/downloads
    the data to the S3 storage.

    Args:
        config (str):           Path to file with user creds and project info
        username (str):         User spec. username, None if config used
        password (str):         User spec. password, None if config used
        project_id (str):       User spec. project ID, None if config used
        project_owner (str):    User spec. project owner, None if config used
        pathfile (str):         Path to file containing file paths
        data (tuple):           All paths to be uploaded/downloaded
        break_on_fail (bool):   True if folder delivery should be cancelled on
                                file fail
        overwrite (bool):       True if deliver again - overwrite delivered
                                files

    Attributes:
        break_on_fail (bool):   Cancel delivery on fail or not
        overwrite (bool):       Overwrite already delivered files or not
        logfile (str):          Path to log file
        LOGGER (Logger):        Logger - keeps track of bugs, info, errors etc
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
        TO_PRINT (str):         Progress printout
        PROGRESS (dict):        Progress info on files  # NOTE: put in data??

    Raises:
        DeliverySystemException:    Required info not found or access denied
        OSError:                    Temporary directory failure

    '''

    #################
    # Magic Methods #
    #################
    def __init__(self, config=None, username=None, password=None,
                 project_id=None, project_owner=None,
                 pathfile=None, data=None, break_on_fail=True,
                 overwrite=False, encrypt=True):
        # NOTE: Restructure __init__?
        # NOTE: Change to args/kwargs?

        # Flags ------------------------------------------------------- Flags #
        self.break_on_fail = break_on_fail
        self.overwrite = overwrite
        self.encrypt = encrypt

        # --------------------------------------------------------------------#

        # Quit execution if none of username, password, config are set
        if all(x is None for x in [username, password, config]):
            sys.exit(printout_error(
                "Delivery System login credentials not specified.\n\n"
                "Enter: \n"
                "--username/-u AND --password/-pw, or --config/-c\n"
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
        self.s3project = "intra1.scilifelab.se"     # S3 project ID -- to connect to S3

        # Cryptography related
        self.public = b''
        self.private = b''

        # Progress related
        self.TO_PRINT = ""
        self.PROGRESS = None

        # Checks ----------------------------------------------------- Checks #
        # Check if all required info is entered and get user info
        self.user = _DSUser()
        self.user.username, self.user.password, self.project_id, \
            self.project_owner = self._check_user_input(
                config=config,
                username=username,
                password=password
            )

        # Get access to DS -- returns json format with access, user_id,
        # project_id, s3_id, and error.
        delivery_info = self._check_ds_access()
        self.user.id = delivery_info['user_id']

        # Fail if no data specified
        if not data and not pathfile:
            sys.exit(
                printout_error("No data to be uploaded. Specify individual "
                               "files/folders using the --data/-d option one "
                               "or more times, or the --pathfile/-f. \n\n"
                               "For help: 'ds_deliver --help'")
            )

        # If everything ok, set bucket name
        self.bucketname = delivery_info['s3_id']
        self.public = bytes.fromhex(delivery_info['public_key'])

        # Get all data to be delivered
        self.data, self.failed = self._data_to_deliver(data=data,
                                                       pathfile=pathfile)

        # NOTE: Change this into ECDH key? Tried but problems with pickling
        # Get project keys
        # self.public = get_project_public(self.project_id)   # Always
        self.private = b'' if self.method == 'put' else \
            get_project_private(self.project_id, self.user)

        # Start progress info printout
        if self.data:
            self.TO_PRINT, self.PROGRESS = self._create_progress_output()

    def __enter__(self):
        '''Allows for implementation using "with" statement.
        Building.'''

        return self

    def __exit__(self, exc_type, exc_value, tb):
        '''Allows for implementation using "with" statement.
        Tear it down. Delete class.

        Prints out which files are delivered and not.'''
        # NOTE: Remove this and just update the progress instead?
        # Also, definitely needs to be checked and simplified
        # TODO: Add check for if uploaded - single file uploaded among failed
        #       folder is not added to final printout

        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        # Tables ##################################################### Tables #
        # Folders
        folders_table = PrettyTable(
            ['Directory', 'File', 'Delivered', 'Error']
        )
        folders_table.padding_width = 2
        folders_table.align['File'] = "r"
        folders_table.align['Error'] = "l"

        # Files
        files_table = PrettyTable(
            ['File', 'Delivered', 'Error']
        )
        files_table.align['File'] = "r"
        files_table.align['Error'] = "l"

        # Reduce the text width and wraps in column
        wrapper = textwrap.TextWrapper(width=80)
        # ------------------------------------------------------------------- #

        # Variables ############################################### Variables #
        folders = {}            # Already checked folders
        are_folders = False     # True if folders have been delivered/failed
        are_files = False       # True if files have been delivered/failed

        # Check if uploaded or downloaded successfully
        critical_op = 'upload' if self.method == "put" else 'download'
        # ------------------------------------------------------------------- #

        # Iterate through items ####################### Iterate through items #
        # Failed items - on initial check
        for file, info in self.failed.items():
            # Remove encrypted files
            self._finalize(file=file, info=info)

            if info['in_directory'] and info['dir_name'] not in folders:
                are_folders = True  # Note that folders have been delivered

                # Get all failed files in folder
                folders[info['dir_name']] = {
                    f: val for f, val in self.failed.items()
                    if val['in_directory'] and
                    val['dir_name'] == info['dir_name']
                }
                # Add folder name to table
                folders_table.add_row(
                    [str(info['dir_name']) + "\n", "", "", ""]
                )
                # Add files in folder to table
                for f, v in folders[info['dir_name']].items():
                    file_loc = \
                        (v['directory_path'] if 'directory_path' in v else
                         get_root_path(file=f, path_base=v['dir_name'].name)) \
                        / Path(Path(f).name)
                    folders_table.add_row(
                        ["",
                         file_loc,
                         "NO",
                         '\n'.join(wrapper.wrap(v["error"])) + '\n']
                    )

            elif not info['in_directory']:
                are_files = True    # Note that files have been delivered
                # Add file to table
                files_table.add_row(
                    [file,
                     "NO",
                     '\n'.join(wrapper.wrap(info["error"])) + '\n']
                )

        # Items passing the initial check - successfully delivered AND failed
        for file, info in self.data.items():
            # Remove encrypted files
            self._finalize(file=file, info=info)

            # Get all files in folder
            if info['in_directory'] and info['dir_name'] not in folders:
                are_folders = True
                folders[info['dir_name']] = {
                    f: val for f, val in self.data.items()
                    if val['in_directory'] and
                    val['dir_name'] == info['dir_name']
                }
                # Add folder name to table
                folders_table.add_row(
                    [info['dir_name'], "", "", ""]
                )
                # Add files in folder to table
                for f, v in folders[info['dir_name']].items():
                    folders_table.add_row(
                        ["",
                            str(v['directory_path'] / Path(Path(f).name)),
                            "YES"
                            if all([v['proceed'], v[critical_op]['finished'],
                                    v['database']['finished']]) else "NO",
                            '\n'.join(wrapper.wrap(v["error"])) + '\n']
                    )

            elif not info['in_directory']:
                are_files = True
                LOG.debug(are_files)
                # Add file to table
                files_table.add_row(
                    [str(file),
                        "YES"
                        if all([info['proceed'], info[critical_op]['finished'],
                                info['database']['finished']]) else "NO",
                        '\n'.join(wrapper.wrap(info["error"])) + '\n'])
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

    ###################
    # Private Methods #
    ###################

    # NOTE: CouchDB -> MariaDB and optimize
    def _check_ds_access(self) -> (bool):
        '''Checks the users access to the delivery system

        Returns:
            bool:   True if user login successful

        Sets:
            self.user.id (str):    User ID

        '''

        LOGIN_BASE = ""
        args = {}
        if self.method == 'put':
            # Get access to delivery system - check if derived pw hash valid
            LOGIN_BASE = API_BASE + "/fac/login"
            args = {'username': self.user.username,
                    'password': self.user.password,
                    'project': self.project_id,
                    'owner': self.project_owner}
        elif self.method == 'get':
            # Get access to delivery system - check if derived pw hash valid
            LOGIN_BASE = API_BASE + "/user/login"
            args = {'username': self.user.username,
                    'password': self.user.password,
                    'project': self.project_id}

        # Request to get access
        response = requests.post(LOGIN_BASE, params=args)
        if not response.ok:
            sys.exit(
                printout_error(
                    """Something wrong. Login failed. Delivery cancelled."""
                )
            )

        json_response = response.json()
        # Quit if user not granted Delivery System access
        if not json_response['access']:
            sys.exit(
                printout_error(
                    f"""Delivery System access denied!
                       Delivery cancelled. {json_response['error']}"""
                )
            )

        # Quit if project ID not matching
        if int(json_response['project_id']) != self.project_id:
            sys.exit(
                printout_error(
                    """Incorrect project ID. System error.
                    Cancelling delivery."""
                )
            )

        return json_response

    def _check_user_input(self, config, username, password):
        '''Checks that the correct options and credentials are entered.

        Args:
            config:     File containing the users DP username and password,
                        and the project relating to the upload/download.
                        Can be used instead of inputing the creds separately.

        '''

        # No config file -------- loose credentials -------- No config file #
        if config is None:
            # Cancel delivery if username or password not specified
            if None in [username, password]:
                sys.exit(
                    printout_error(
                        """Delivery System login credentials not specified.
                           Enter --username/-u AND --password/-pw,
                           or --config/-c.
                           For help: 'ds_deliver --help'."""
                    )
                )

            # Cancel delivery if project_id not specified
            if self.project_id is None:
                sys.exit(
                    printout_error(
                        """Project not specified. Enter project ID using
                           --project option or add to config file using
                           --config/-c option."""
                    )
                )

            # Assume current user is owner if no owner is set
            if self.project_owner is None:
                # username, password, owner
                return username, password, self.project_id, username

        # Config file ----------- credentials in it ----------- Config file #
        user_config = Path(config).resolve()
        try:
            # Get info from credentials file
            with user_config.open(mode='r') as cf:
                credentials = json.load(cf)
        except OSError as ose:
            sys.exit(
                printout_error(f"""Could not open path-file {config}: {ose}""")
            )

        # Quit if not all credentials are entered
        if not all(c in credentials for c
                   in ['username', 'password', 'project']):
            sys.exit(
                printout_error(
                    """The config file does not contain all required
                       information."""
                )
            )

        # Save info from credentials file
        username = credentials['username']
        password = credentials['password']
        project_id = credentials['project']

        # OK if owner specified
        if 'owner' in credentials:
            return username, password, project_id, credentials['owner']

        # Error if owner not specified and trying to put
        if self.project_owner is None and self.method == 'put':
            sys.exit(
                printout_error(
                    """Project owner not specified. Cancelling delivery."""
                )
            )

        return username, password, project_id, username

    def _create_progress_output(self) -> (str, dict):
        '''Create list of files and the individual delivery progress.

        Returns:
            tuple:  Information on start status for all files

                str:    Progressinfo (all files) to print to console
                dict:   Files and their current delivery statuses

        '''

        sys.stdout.write("\n")  # Space between command and any output

        # Variables ############################################### Variables #
        global SCOLSIZE, FCOLSIZE   # -- can edit their value

        # Find appropriate size of progress table
        # Max length of status info
        max_status = max(list(len(y) for x, y in STATUS_DICT.items()))
        # Width of status "column"
        SCOLSIZE = max_status if (max_status % 2 == 0) else max_status + 1

        # Width of file "column"
        FCOLSIZE = max(list(len(str(x)) for x in self.data))

        # To return
        TO_PRINT = ""
        PROGRESS_DICT = collections.OrderedDict()
        # ------------------------------------------------------------------- #

        # Header of progress info, eg:
        # -------------- File -------------- ------ Status ------
        sys.stdout.write(f"{int((FCOLSIZE/2)-len('File')/2)*'-'}"
                         " File "
                         f"{int((FCOLSIZE/2)-len('File')/2)*'-'}"
                         " "
                         f"{int(SCOLSIZE/2-len('Progress')/2)*'-'}"
                         " Progress "
                         f"{int(SCOLSIZE/2-len('Progress')/2)*'-'}\n")

        # Set initial status for all files to 'Waiting to start...'
        for x in self.data:
            file = str(x)
            PROGRESS_DICT[file] = \
                {'status': STATUS_DICT['w'],
                    'line': (f"{file}{int(FCOLSIZE-len(file)+1)*' '} "
                             f"{int(SCOLSIZE/2-len(STATUS_DICT['w'])/2)*' '}"
                             f"{STATUS_DICT['w']}\n")}
            TO_PRINT += PROGRESS_DICT[file]['line']

        # Print all file statuses
        sys.stdout.write(TO_PRINT)

        return TO_PRINT, PROGRESS_DICT

    def _data_to_deliver(self, data: tuple, pathfile: str) -> (dict, dict):
        '''Puts all entered paths into one list

        Args:
            data (tuple):       Tuple containing paths
            pathfile (str):   Path to file containing paths

        Returns:
            tuple:  Info on user specified files

                dict:   Info on all files to be delivered
                dict:   Info on files which failed initial check

        '''

        # Variables ######################################### Variables #
        all_files = dict()
        initial_fail = dict()

        data_list = list(data)
        # --------------------------------------------------------------#

        # Add data included in pathfile to data dict
        if pathfile is not None and Path(pathfile).exists():
            with Path(pathfile).resolve().open(mode='r') as file:
                data_list += [line.strip() for line in file]

        # Fail delivery if not a correct method
        if self.method not in ["get", "put"]:
            sys.exit(
                printout_error(f"Delivery option {self.method} not allowed.\n\n"
                               "Cancelling delivery.")
            )

        # Gather data info ########################### Gather data info #
        # Iterate through all user specified paths
        for d in data_list:
            # 1. Check if compressed etc
            # 2. Get all files in project
            # 3. Check if files exist in db

            # Throw error if there are duplicate files
            if d in all_files or Path(d).resolve() in all_files:
                sys.exit(
                    printout_error(f"The path to file {d} is listed multiple "
                                   "times, please remove path dublicates.")
                )

            # Get file info ############################# Get file info #
            # if self.method == "get":
            #     iteminfo = self._get_download_info(item=d)

            #     # Save to failed dict or delivery dict
            #     if len(iteminfo) == 1 and d in iteminfo:    # File
            #         if not iteminfo[d]['proceed']:
            #             initial_fail.update(iteminfo)
            #             continue

            #         all_files.update(iteminfo)
            #     else:                                       # Folder
            #         for f in iteminfo:
            #             if not iteminfo[f]['proceed']:
            #                 initial_fail[f] = iteminfo[f]
            #                 continue

            #             all_files[f] = iteminfo[f]

            elif self.method == "put":
                # Error if path doesn't exist
                # NOTE: Keep this or remove? Should have been checked by click
                if not Path(d).exists():
                    sys.exit(
                        printout_error("Trying to deliver a non-existing "
                                       f"file/folder: {d}. Delivery not "
                                       "possible.")
                    )

                curr_path = Path(d).resolve()   # Full path to data

                # Get info on files within folder
                if curr_path.is_dir():
                    dir_info, dir_fail = self._get_dir_info(folder=curr_path)
                    initial_fail.update(dir_fail)   # Not to be delivered
                    all_files.update(dir_info)      # To be delivered
                    continue

                # Get info for individual files
                file_info = self._get_file_info(file=curr_path, in_dir=False)
                if not file_info['proceed']:
                    # Don't deliver --> save error message
                    initial_fail[curr_path] = file_info
                else:
                    # Deliver --> save info
                    all_files[curr_path] = file_info

                print(f"File info: {file_info}")
        
        # Get project files in database
        FILE_BASE = API_BASE + "/project/listfiles"
        req = FILE_BASE + f"/{self.project_id}"
        response = requests.get(req)
        files_in_db = response.json()

        print(f"Files in database: {files_in_db}")
        for file, info in list(all_files.items()):
            if info['new_file'] in files_in_db['files']:
                LOG.info(f"{file} already exists in database")
                initial_fail[file] = {
                    **all_files.pop(file),
                    'error': "File already exists in database"
                }
            else:
                with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                        as s3:
                    # Check if file exists in bucket already
                    in_bucket, s3error = s3.file_exists_in_bucket(
                        info['new_file']
                    )
                    # LOG.debug(f"File: {file}\t In bucket: {in_bucket}")

                    # if s3error != "":
                    #     error = s3error    # Add s3error to error message

                    # Error if the file exists in bucket, but not in the database
                    if in_bucket:
                        initial_fail[file] = {
                            **all_files.pop(file),
                            'error': (f"File '{file.name}' already exists in "
                                      "bucket, but does NOT exist in database. "
                                      "Delivery cancelled, contact support.")
                        }

        # --------------------------------------------------------- #

        return all_files, initial_fail

    def _finalize(self, file: Path, info: dict):
        '''Makes sure that the file is not in bucket or db and deletes
        if it is.

        Args:
            file (Path):    Path to file
            info (dict):    Info about file --> don't use around with real dict

        '''

        # Downloading ############## Delete local ############### Downloading #
        if self.method == 'get':
            if 'new_file' in info:
                file_deleter(file=info['new_file'])
                return

        # Uploading ########### Delete local and remote ########### Uploading #
        # Delete local encrypted
        if 'encrypted_file' in info:
            file_deleter(file=info['encrypted_file'])

        # NOTE: Add check here for if actually uploaded etc?
        # Delete from S3 if uploaded but not in database
        with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                as s3:
            if ('upload' in info and info['upload']['finished']
                    and 'database' in info
                    and not info['database']['finished']):
                try:
                    s3.delete_item(key=info['new_file'])
                except ClientError as e:
                    LOG.warning(e)

        # # Delete from database if in database but not uploaded
        # with DatabaseConnector(db_name='project_db') as prdb:
        #     try:
        #         proj = prdb[self.project_id]
        #         if ('database' in info and info['database']['finished']
        #                 and 'upload' in info
        #                 and not info['upload']['finished']):
        #             del proj['files'][info['new_file']]
        #     except CouchDBException as e:
        #         LOG.warning(e)

    def _get_dir_info(self, folder: Path) -> (dict, dict):
        '''Iterate through folder contents and get file info

        Args:
            folder (Path):  Path to folder

        Returns:
            dict:   Files to deliver
            dict:   Files which failed -- not to deliver
        '''

        # Variables ############################ Variables #
        dir_info = {}   # Files to deliver
        dir_fail = {}   # Failed files
        # -------------------------------------------------#

        # Iterate through folder contents and get file info
        for f in folder.glob('**/*'):
            if f.is_file() and "DS_Store" not in str(f):    # CHANGE LATER
                file_info = self._get_file_info(file=f,
                                                in_dir=True,
                                                dir_name=folder)

                # If file check failed in some way - do not deliver file
                # Otherwise deliver file -- no cancellation of folder here
                if not file_info['proceed']:
                    dir_fail[f] = file_info
                else:
                    dir_info[f] = file_info

        return dir_info, dir_fail

    def _get_download_info(self, item: str) -> (dict):
        '''Gets info on file in database and checks if
        item exists in S3 bucket.

        Args:
            item (str):   File or folder to download

        Returns:
            dict: Information on if file can be downloaded or not

        '''

        # Variables ################################# Variables #
        # General
        proceed = True      # To proceed with download or not
        in_db = False       # If item in db or not
        none_in_bucket = True   # If none of the items are in the s3 bucket
        to_download = {}    # Files to download
        error = ""          # Error message

        # Info about steps
        gen_finfo = {'download': {'in_progress': False,
                                  'finished': False},
                     'decryption': {'in_progress': False,
                                    'finished': False},
                     'database': {'in_progress': False,
                                  'finished': False}}
        # ----------------------------------------------------- #

        with DatabaseConnector(db_name='project_db') as project_db:
            # Error in DS if project doesn't exist in database or no file info
            if self.project_id not in project_db or \
                    'files' not in project_db[self.project_id]:
                raise CouchDBException("Project not in database or no file "
                                       "info about project -- error in "
                                       "delivery system!")

            # If no suffixes assuming folder and adding trailing slash
            if not Path(item).suffixes:
                item = os.path.join(item, '')

            # Check for file starting with the file/folder name
            for file in project_db[self.project_id]['files']:
                # Get info on file
                if file.startswith(item):
                    to_download[file] = {
                        **project_db[self.project_id]['files'][file],
                        **gen_finfo
                    }
                    in_db = True

                    # Check if the file was uploaded as a part of a directory
                    in_directory = to_download[file]['directory_path'] != "."

                    # Save file info
                    to_download[file].update({
                        'new_file': DIRS[1] / Path(file),   # Path in tempdir
                        'in_directory': in_directory,       # If in dir
                        'dir_name': item if in_directory else None,
                        'proceed': proceed,     # If ok to proceed with deliv
                        'error': error          # Error message, "" if none
                    })

            # No delivery if the item doesn't exist in the database
            if not in_db:
                error = f"Item: {item} -- not in database"
                LOG.warning(error)
                return {item: {'proceed': False, 'error': error}}

        # Check S3 bucket for item(s)
        with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                as s3:

            # If folder - can contain more than one
            for file in to_download:
                in_bucket, s3error = s3.file_exists_in_bucket(key=file,
                                                              put=False)

                if not in_bucket:
                    error = (f"File '{file}' in database but NOT in S3 bucket."
                             f"Error in delivery system! {s3error}")
                    LOG.warning(error)
                    to_download[file].update({'proceed': False,
                                              'error': error})
                else:
                    none_in_bucket = False   # There are files in the bucket

            # Error if none of the files were in S3 bucket
            if none_in_bucket:
                error = (f"Item: {item} -- not in S3 bucket, but in database "
                         f"-- Error in delivery system!")
                LOG.warning(error)
                return {item: {'proceed': False, 'error': error}}

        return to_download

    def _get_file_info(self, file: Path, in_dir: bool,
                       dir_name: Path = Path("")) -> (dict):
        '''Get info on file and check if already delivered

        Args:
            file (Path):        Path to file
            in_dir (bool):      True if in directory specified by user
            dir_name (Path):    Directory name, "" if not in folder

        Returns:
            dict:   Information about file e.g. format

        '''

        # Variables ###################################### Variables #
        proceed = True  # If proceed with file delivery
        in_db = False   # True if file in database
        path_base = dir_name.name if in_dir else None   # Folder name if in dir
        directory_path = get_root_path(file=file, path_base=path_base) \
            if path_base is not None else Path("")  # Path to file IN folder
        suffixes = file.suffixes    # File suffixes
        proc_suff = ""              # Saves final suffixes
        error = ""                  # Error message
        dir_info = {'in_directory': in_dir, 'dir_name': dir_name}
        # ---------------------------------------------------------- #

        # Check if file is compressed and fail delivery on error
        compressed, error = is_compressed(file=file)
        if error != "":
            return {'proceed': False, 'error': error, **dir_info}

        # If file not compressed -- add zst (Zstandard) suffix to final suffix
        # If compressed -- info that DS will not compress
        if not compressed:
            # Warning if suffixes are in magic dict but file "not compressed"
            if set(suffixes).intersection(set(MAGIC_DICT)):
                LOG.warning(f"File '{file}' has extensions belonging "
                            "to a compressed format but shows no "
                            "indication of being compressed. Not "
                            "compressing file.")

            proc_suff += ".zst"     # Update the future suffix
        elif compressed:
            LOG.info(f"File '{file}' shows indication of being "
                     "in a compressed format. "
                     "Not compressing the file.")

        # Add (own) encryption format extension
        proc_suff += ".ccp"     # ChaCha20-Poly1305

        # Path to file in temporary directory after processing, and bucket
        # after upload, >>including file name<<
        bucketfilename = str(directory_path / Path(file.name + proc_suff))

        # # NOTE: Similar (but different order) to _get_download_info - "merge"?
        # # Check if file exists in database

        # with DatabaseConnector('project_db') as project_db:
        #     # Error in DS if project doesn't exist in database or no file info
        #     if self.project_id not in project_db or \
        #             'files' not in project_db[self.project_id]:
        #         raise CouchDBException("Project not in database or no file "
        #                                "info about project -- error in "
        #                                "delivery system!")

        #     if bucketfilename in project_db[self.project_id]['files']:
        #         error = f"File '{file}' already exists in the database. "
        #         LOG.warning(error)
        #         # Cancel upload of file if --overwrite flag not specified
        #         if not self.overwrite:
        #             return {'proceed': False, 'error': error, **dir_info}

        #         # Do not cancel if --overwrite flag specified
        #         in_db = True

        # # Check if file exists in S3 bucket
        # with S3Connector(bucketname=self.bucketname, project=self.s3project) \
        #         as s3:
        #     # Check if file exists in bucket already
        #     in_bucket, s3error = s3.file_exists_in_bucket(bucketfilename)
        #     # LOG.debug(f"File: {file}\t In bucket: {in_bucket}")

        #     if s3error != "":
        #         error += s3error    # Add s3error to error message

        #     # Error if the file exists in bucket, but not in the database
        #     if in_bucket:
        #         if not in_db:
        #             error = (f"{error}\nFile '{file.name}' already exists in "
        #                      "bucket, but does NOT exist in database. " +
        #                      "Delivery cancelled, contact support.")
        #             LOG.critical(error)
        #             return {'proceed': False, 'error': error, **dir_info}

        #         # If file exists in bucket and in database and...
        #         # --overwrite flag not specified --> cancel file delivery
        #         # --overwrite flag --> deliver again, overwrite file
        #         if not self.overwrite:
        #             return {'proceed': False, 'error': error, **dir_info}

        return {'in_directory': in_dir,
                'dir_name': dir_name if in_dir else None,
                'path_base': path_base,
                'directory_path': directory_path,
                'size': file.stat().st_size,
                'suffixes': suffixes,
                'proceed': proceed,
                'compressed': compressed,
                'new_file': bucketfilename,
                'error': error,
                'encrypted_file': Path(""),
                'encrypted_size': 0,
                'key': "",
                'processing': {'in_progress': False,
                               'finished': False},
                'upload': {'in_progress': False,
                           'finished': False},
                'database': {'in_progress': False,
                             'finished': False}}

    ##################
    # Public Methods #
    ##################

    def finalize_delivery(self, file: str, fileinfo: dict) -> (tuple):
        '''Finalizes delivery after download from s3:
        Decrypts, decompresses (if compressed in DS), and checks integrity.

        Args:
            file (str):         Path to file
            fileinfo (dict):    Information on file

        Return:
            tuple:   Info on finalized file

                bool:   True if decryption etc successful
                str:    Path to new, delivered and decrypted file
                str:    Error message, "" if none

        '''

        # If DS noted cancelation of file -- quit and move on
        if not fileinfo['proceed']:
            return False, ""

        # Set file processing as in progress
        self.set_progress(item=file, decryption=True, started=True)

        # Decrypt etc
        info = reverse_processing(file=file, file_info=fileinfo,
                                  keys=(self.public, self.private))

        return info

    def prep_upload(self, path: Path, path_info: dict) -> (tuple):
        '''Prepares the files for upload.

        Args:
            path (Path):        Path to file
            path_info (dict):   Info on file

        Returns:
            tuple:  Info on success and info

                bool:   True if processing successful
                Path:   Path to processed file
                int:    Size of processed file
                bool:   True if file compressed by the delivery system
                bytes:  Public key needed for file decryption
                bytes:  Salt needed for shared key derivation
                str:    Error message, "" if none
        '''

        # If DS noted cancelation of file -- quit and move on
        if not path_info['proceed']:
            return False, Path(""), 0, False, "", b''

        # Set file processing as in progress
        self.set_progress(item=path, processing=True, started=True)

        # Begin processing incl encryption
        info = process_file(file=path,
                            file_info=path_info,
                            peer_public=self.public)

        return info

    def set_progress(self, item: Path, check: bool = False,
                     processing: bool = False, upload: bool = False,
                     download: bool = False, decryption: bool = False,
                     db: bool = False, started: bool = False,
                     finished: bool = False):
        '''Set progress of file to in progress or finished, regarding
        the file checks, processing, upload or database.

        Args:
            item (Path):        Path to file being handled
            check (bool):       True if file checking in progress or finished
            processing (bool):  True if processing in progress or finished
            upload (bool):      True if upload in progress or finshed
            db (bool):          True if database update in progress or finished

        Raises:
            DataException:  Data dictionary update failed

        '''

        # Which process to update
        to_update = ""

        if self.method == "put":
            if processing:
                to_update = 'processing'
            elif upload:
                to_update = 'upload'
            elif db:
                to_update = 'database'
        elif self.method == "get":
            if download:
                to_update = 'download'
            elif decryption:
                to_update = 'decryption'
            elif db:
                to_update = 'database'

        # Exit if trying to update something else
        if to_update == "":
            raise DeliverySystemException("Trying to update progress on "
                                          "forbidden process.")

        # Update the progress
        if started:
            self.data[item][to_update].update({'in_progress': started,
                                               'finished': not started})
            return
        elif finished:
            self.data[item][to_update].update({'in_progress': not finished,
                                               'finished': finished})
            return

        LOG.exception(f"Data delivery information failed to "
                      f"update: {dex}")

    def update_delivery(self, file: Path, updinfo: dict) -> (bool):
        '''Updates data delivery information dictionary

        Args:
            file (Path):        The files info to be updated
            updinfo (dict):     The dictionary to update the info with

        Returns:
            bool:   True if to continue with delivery

        Raises:
            DataException:  Data dictionary update failed

        '''

        # Variables ############################################### Variables #
        critical_op = 'upload' if self.method == "put" else 'download'
        all_info = self.data[file]  # All info on file
        # ------------------------------------------------------------------- #

        # If cancelled by another file set as not proceed and add error message
        if not all_info['proceed']:
            updinfo.update({'proceed': all_info['proceed'],
                            'error': all_info['error']})

        # Fail file if delivery cancelled by DS update dictionary
        if not updinfo['proceed']:
            # If failed file in directory, check if to fail all files or not
            if all_info['in_directory']:
                dir_name = all_info['dir_name']

                # Update current file
                self.data[file].update({'proceed': False,
                                        'error': updinfo['error']})

                # If break-on-fail flag --> fail all files in directory
                if self.break_on_fail:
                    for path, info in self.data.items():
                        # If within shared folder and upload not in progress or
                        # finished -- set current file error and cancel
                        if path != file and info['proceed'] and \
                            info['dir_name'] == dir_name \
                                and not all([info[critical_op]['in_progress'],
                                             info[critical_op]['finished']]):

                            self.data[path].update({
                                'proceed': False,
                                'error': ("break-on-fail chosen --"
                                          f"{updinfo['error']}")
                            })
                    return False

            # If individual file -- cancel this specific file only
            self.data[file].update({'proceed': False,
                                    'error': updinfo['error']})
            return False

        # If file to proceed, update file info
        try:
            self.data[file].update(updinfo)
        except DataException as dex:
            LOG.exception(f"Data delivery information failed to "
                          f"update: {dex}")

        return True

    def update_progress(self, file, status: str):
        '''Update the status of the file - Waiting, Encrypting, Uploading, etc.

        Args:
            file:             File to update progress on
            status (str):     Which stage the delivery is on

        '''

        file = str(file)    # For printing and len() purposes

        # Change the status
        self.PROGRESS[file]['status'] = STATUS_DICT[status]

        # Line to update to in progress output
        new_line = (f"{file}{int(FCOLSIZE-len(file)+1)*' '} "
                    f"{int(SCOLSIZE/2-len(STATUS_DICT[status])/2)*' '}"
                    f"{2*' '}{STATUS_DICT[status]}")

        # If shorter line than before -> cover up previous text
        diff = abs(len(self.PROGRESS[file]['line']) - len(new_line))
        new_line += diff*" " + "\n"

        # Replace the printout and progress dict with the update
        self.TO_PRINT = self.TO_PRINT.replace(self.PROGRESS[file]['line'],
                                              new_line)
        self.PROGRESS[file]['line'] = new_line

        # Print the status
        sys.stdout.write("\033[A"*len(self.PROGRESS))   # Jump up to cover prev
        sys.stdout.write(self.TO_PRINT)                 # Print new for all

    ################
    # Main Methods #
    ################
    def get(self, path: str, path_info: dict) -> (bool, str):
        '''Downloads specified data from S3 bucket

        Args:
            path (str):         File to be downloaded
            path_info (dict):   Name of downloaded file

        Returns:
            tuple:  Info on download success

                bool:   True if downloaded
                str:    Error message, "" if none

        Raises:
            OSError:                        Creating directory failed
            botocore.client.ClientError:    Failed download

        '''

        # Quit and move on if DS noted cancelation of file
        if not path_info['proceed']:
            return False, ""

        # Set file processing as in progress
        self.set_progress(item=path, download=True, started=True)

        # New temporary sub directory
        new_dir = DIRS[1] / Path(path_info['directory_path'])

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
        with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                as s3:

            # Download file from S3
            try:
                s3.resource.meta.client.download_file(
                    Bucket=s3.bucketname,
                    Key=path,
                    Filename=str(path_info['new_file'])
                )
            except ClientError as e:
                # Upload failed -- return error message and move on
                error = (f"File: {path}. Download failed: {e}")
                LOG.exception(error)
                return False, error
            else:
                # Upload successful
                LOG.info(f"File: {path}. Download successful! "
                         f"File location: {path_info['new_file']}")
                return True, ""

    def put(self, file: Path, fileinfo: dict) -> (bool, str):
        '''Uploads specified data to the S3 bucket.

        Args:
            file (Path):       Path to original file
            fileinfo (dict):   Info on file

        Returns:
            tuple:

                bool:   True if upload successful
                str:    Encrypted file, to upload
                str:    Remote path, path in bucket
                str:    Error message, "" if none

        '''

        # Quit and move on if DS noted cancelation of file
        if not fileinfo['proceed']:
            error = ""
            # Quit and move on if processing not performed
            if not fileinfo['processing']['finished']:
                error = (f"File: '{file}' -- File not processed (e.g. "
                         "encrypted). Bug in code. Moving on to next file.")
                LOG.critical(error)

            return False, error

        # Set delivery as in progress
        self.set_progress(item=file, upload=True, started=True)

        # UPLOAD START ######################################### UPLOAD START #
        with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                as s3:

            # Upload file
            try:
                s3.resource.meta.client.upload_file(
                    Filename=str(fileinfo['encrypted_file']),
                    Bucket=s3.bucketname,
                    Key=fileinfo['new_file']
                )
            except ClientError as e:
                # Upload failed -- return error message and move on
                error = (f"File: {file}, Uploaded: "
                         f"{fileinfo['encrypted_file']} -- "
                         f"Upload failed! -- {e}")
                LOG.exception(error)
                return False, error

            return True, ""


# DSUSER ############################################################## DSUER #


class _DSUser():
    '''
    A Data Delivery System user.

    Args:
        username (str):   Delivery System username
        password (str):   Delivery System password

    Attributes:
        username (str): Delivery System username
        password (str): Delivery System password
        id (str):       User ID
        role (str):     Facility or researcher
    '''
    # NOTE: Remove user class?

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.id = None
        self.role = None
