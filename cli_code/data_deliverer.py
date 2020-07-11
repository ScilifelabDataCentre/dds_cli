import json
import os
from pathlib import Path
import sys
import threading
import traceback
import logging
import textwrap
import shutil

from cli_code.crypt4gh.crypt4gh import lib
from prettytable import PrettyTable
from botocore.client import ClientError

from cli_code import (DIRS, LOG_FILE)
from cli_code.exceptions_ds import (DataException, DeliveryOptionException,
                                    DeliverySystemException, CouchDBException,
                                    S3Error)
from cli_code.s3_connector import S3Connector
from cli_code.crypto_ds import secure_password_hash
from cli_code.database_connector import DatabaseConnector
from cli_code.file_handler import (config_logger, get_root_path, is_compressed,
                                   MAGIC_DICT, process_file,
                                   reverse_processing)

# CONFIG ############################################################# CONFIG #

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

# DATA DELIVERER ############################################# DATA DELIVERER #


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

    Attributes:
        method (str):           Delivery method, put or get
        user (DSUser):          Data Delivery System user
        project_id (str):       Project ID to upload to/download from
        project_owner (str):    Owner of the current project
        data (list):            Paths to files/folders
        bucketname (str):       Name of S3 bucket to deliver to/from
        s3project (str):        ID of S3 project containing buckets
        tempdir (tuple):        Paths to temporary DP folders
        logfile (str):          Path to log file
        logger (Logger):        Logger - keeps track of bugs, info, errors etc

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
                 overwrite=False):

        # Flags ------------------------------------------------------- Flags #
        self.break_on_fail = break_on_fail
        self.overwrite = overwrite

        # Initialize logger ------------------------------- Initialize logger #
        self.logfile = LOG_FILE
        self.LOGGER = logging.getLogger(__name__)
        self.LOGGER.setLevel(logging.DEBUG)
        self.LOGGER = config_logger(
            logger=self.LOGGER, filename=self.logfile,
            file=True, file_setlevel=logging.DEBUG,
            fh_format="%(asctime)s::%(levelname)s::" +
            "%(name)s::%(lineno)d::%(message)s",
            stream=True, stream_setlevel=logging.DEBUG,
            sh_format="%(levelname)s::%(name)s::" +
            "%(lineno)d::%(message)s"
        )
        # --------------------------------------------------------------------#
        # Quit execution if none of username, password, config are set
        if all(x is None for x in [username, password, config]):
            raise DeliverySystemException(
                "Delivery System login credentials not specified. "
                "Enter: \n--username/-u AND --password/-pw,"
                " or --config/-c\n --owner/-o\n"
                "For help: 'ds_deliver --help'."
            )

        # Main attributes ----------------------------------- Main attributes #
        # General
        self.method = sys._getframe().f_back.f_code.co_name  # put or get
        self.user = _DSUser(username=username, password=password)
        self.project_id = project_id        # Project ID - not S3
        self.project_owner = project_owner  # User, not facility
        self.data = None           # Dictionary, keeps track of delivery

        # S3 related
        self.bucketname = ""    # S3 bucket name -- to connect to S3
        self.s3project = ""     # S3 project ID -- to connect to S3

        # Checks ----------------------------------------------------- Checks #
        # Check if all required info is entered
        # Sets: self.project_owner, self.user.username, self.user.password,
        #       self.project_id
        self._check_user_input(config=config)

        # Check access to delivery system
        ds_access_granted = self._check_ds_access()
        if not ds_access_granted or self.user.id is None:
            raise DeliverySystemException(
                "Delivery System access denied! "
                "Delivery cancelled."
            )

        # If access to delivery system, check project access
        proj_access_granted, self.s3project = self._check_project_access()
        if not proj_access_granted:
            raise DeliverySystemException(
                f"Access to project {self.project_id} "
                "denied. Delivery cancelled."
            )

        # If access to project, check that some data is specified
        if not data and not pathfile:
            raise DeliverySystemException(
                "No data to be uploaded. Specify individual "
                "files/folders using the --data/-d option one or "
                "more times, or the --pathfile/-f. "
                "For help: 'ds_deliver --help'"
            )

        # If everything ok, set bucket name -- CHANGE LATER
        self.bucketname = f"project_{self.project_id}"

        # Get all data to be delivered
        self.data, self.failed = self._data_to_deliver(data=data,
                                                       pathfile=pathfile)

        # Success message
        self.LOGGER.info("Delivery initialization successful.")

    def __enter__(self):
        '''Allows for implementation using "with" statement.
        Building.'''

        return self

    def __exit__(self, exc_type, exc_value, tb):
        '''Allows for implementation using "with" statement.
        Tear it down. Delete class.'''

        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        if self.method == "put":
            folders_table = PrettyTable(
                ['Directory', 'File', 'Delivered', 'Error']
            )
            folders_table.padding_width = 2
            folders_table.align['File'] = "r"
            folders_table.align['Error'] = "l"

            files_table = PrettyTable(
                ['File', 'Delivered', 'Error']
            )
            files_table.align['File'] = "r"
            files_table.align['Error'] = "l"

            wrapper = textwrap.TextWrapper(width=100)

            folders = {}
            files = {}

            are_folders = False
            are_files = False

            for file, info in self.failed.items():
                if info['in_directory'] and info['dir_name'] not in folders:
                    are_folders = True
                    folders[info['dir_name']] = {
                        f: val for f, val in self.failed.items()
                        if val['in_directory'] and
                        val['dir_name'] == info['dir_name']
                    }
                    print(f"--- {folders}")
                    folders_table.add_row(
                        [str(info['dir_name']) + "\n", "", "", ""]
                    )
                    for f, v in folders[info['dir_name']].items():
                        folders_table.add_row(
                            ["",
                             (v['directory_path'] if 'directory_path' in v
                              else get_root_path(file=f, path_base=v['dir_name'].name)) / f.name,
                             "NO",
                             '\n'.join(wrapper.wrap(v["error"])) + '\n']
                        )

                elif not info['in_directory']:
                    are_files = True
                    files_table.add_row(
                        [file,
                         "NO",
                         '\n'.join(wrapper.wrap(info["error"])) + '\n'])

            for file, info in self.data.items():
                if info['in_directory'] and info['dir_name'] not in folders:
                    are_folders = True
                    folders[info['dir_name']] = {
                        f: val for f, val in self.data.items()
                        if val['in_directory'] and
                        val['dir_name'] == info['dir_name']
                    }
                    folders_table.add_row(
                        [info['dir_name'], "", "", ""]
                    )
                    for f, v in folders[info['dir_name']].items():
                        folders_table.add_row(
                            ["",
                             str(v['directory_path'] / f.name),
                             "YES"
                             if all([v['proceed'], v['upload']['finished'],
                                     v['database']['finished']]) else "NO",
                             '\n'.join(wrapper.wrap(v["error"])) + '\n']
                        )

                elif not info['in_directory']:
                    are_files = True
                    self.LOGGER.debug(are_files)
                    files_table.add_row(
                        [str(file),
                         "YES"
                         if all([info['proceed'], info['upload']['finished'],
                                 info['database']['finished']]) else "NO",
                         '\n'.join(wrapper.wrap(info["error"])) + '\n'])

            self.LOGGER.info("DELIVERY COMPLETED!")
            self.LOGGER.info(
                f"\n#################### FOLDERS DELIVERED ####################"
                f"\n{folders_table}\n" if are_folders else "\n")
            self.LOGGER.info(
                f"\n##################### FILES DELIVERED #####################"
                f"\n{files_table}\n" if are_files else "\n")

    ###################
    # Private Methods #
    ###################

    def _check_ds_access(self):
        '''Checks the users access to the delivery system

        Returns:
            tuple:  Granted access and user ID

                bool:   True if user login successful
                str:    User ID

        Raises:
            CouchDBException:           Database connection failure or
                                        user not found
            DeliveryOptionException:    Invalid method option
            DeliverySystemException:    Wrong password
        '''

        with DatabaseConnector('user_db') as user_db:
            # Search the database for the user
            for id_ in user_db:
                # If found, create secure password hash
                if self.user.username == user_db[id_]['username']:
                    password_settings = user_db[id_]['password']['settings']
                    password_hash = secure_password_hash(
                        password_settings=password_settings,
                        password_entered=self.user.password
                    )
                    # Compare to correct password, error if no match
                    if user_db[id_]['password']['hash'] != password_hash:
                        raise DeliverySystemException(
                            "Wrong password. Access to Delivery System denied."
                        )

                    # Check that facility putting or researcher getting
                    self.user.role = user_db[id_]['role']
                    if (self.user.role == 'facility'and self.method == 'put') \
                            or (self.user.role == 'researcher' and
                                self.method == 'get'):
                        self.user.id = id_  # User granted access to put or get

                        # If role allowed to get
                        if (self.user.role == 'researcher' and
                            self.method == 'get' and
                            (self.project_owner is None or
                             self.project_owner == self.user.username)):
                            self.project_owner = self.user.id
                        return True  # Access granted
                    else:
                        raise DeliveryOptionException(
                            "Method error. Facilities can only use 'put' "
                            "and Researchers can only use 'get'."
                        )

            raise CouchDBException(
                "Username not found in database. "
                "Access to Delivery System denied."
            )

    def _check_project_access(self):
        '''Checks the users access to a specific project.

        Returns:
            tuple:  Project access and S3 project ID

                bool:   True if project access granted
                str:    S3 project to upload to/download from

        Raises:
            CouchDBException:           Database connection failure
                                        or missing project information
            DeliveryOptionException:    S3 delivery option not available
                                        or incorrect project owner
            DeliverySystemException:    Access denied

        '''

        with DatabaseConnector() as couch:
            user_db = couch['user_db']

            # Get the projects registered to the user
            user_projects = user_db[self.user.id]['projects']

            # Check if project doesn't exists in project database -> quit
            if self.project_id not in couch['project_db']:
                raise CouchDBException(
                    f"The project {self.project_id} does not exist."
                )

            # If project exists, check if user has access to the project->quit
            if self.project_id not in user_projects:
                raise DeliverySystemException(
                    "You do not have access to the specified project "
                    f"{self.project_id}. Aborting delivery."
                )

            # If user has access, get current project
            current_project = couch['project_db'][self.project_id]
            # If project information doesn't exist -> quit
            if 'project_info' not in current_project:
                raise CouchDBException(
                    "There is no 'project_info' recorded for the specified "
                    "project. Aborting delivery."
                )

            # If project info exists, check if owner info exists.
            # If not -> quit
            if 'owner' not in current_project['project_info']:
                raise CouchDBException(
                    "An owner of the data has not been specified. "
                    "Cannot guarantee data security. Cancelling delivery."
                )

            # If owner info exists, find owner of project
            # and check if specified owner matches. If not -> quit
            correct_owner = current_project['project_info']['owner']
            # If facility specified correct user or researcher is owner
            if (self.method == 'put'
                and correct_owner == self.project_owner != self.user.id) \
                or (self.method == 'get'
                    and correct_owner == self.project_owner == self.user.id):
                # If delivery_option not recorded in database -> quit
                if 'delivery_option' not in current_project['project_info']:
                    raise CouchDBException(
                        "A delivery option has not been "
                        "specified for this project."
                    )

                # If delivery option exists, check if S3. If not -> quit
                if current_project['project_info']['delivery_option'] != "S3":
                    raise DeliveryOptionException(
                        "The specified project does not "
                        "have access to S3 delivery."
                    )

                # If S3 option specified, return S3 project ID
                try:
                    s3_project = user_db[self.user.id]['s3_project']['name']
                except DeliverySystemException as dpe:
                    sys.exit(
                        "Could not get Safespring S3 project name from "
                        f"database: {dpe}. \nDelivery aborted."
                    )
                else:
                    return True, s3_project
            else:
                raise DeliveryOptionException(
                    "Incorrect data owner! You do not have access to this "
                    "project. Cancelling delivery."
                )

    def _check_user_input(self, config):
        '''Checks that the correct options and credentials are entered.

        Args:
            config:     File containing the users DP username and password,
                        and the project relating to the upload/download.
                        Can be used instead of inputing the creds separately.

        Raises:
            OSError:                    Config file not found or opened
            DeliveryOptionException:    Required information not found

        '''

        # No config file --------- loose credentials --------- No config file #
        if config is None:
            # If username or password not specified cancel delivery
            if not all([self.user.username, self.user.password]):
                raise DeliveryOptionException(
                    "Delivery System login credentials not specified. "
                    "Enter --username/-u AND --password/-pw, or --config/-c."
                    "For help: 'ds_deliver --help'."
                )

            # If project_id not specified cancel delivery
            if self.project_id is None:
                raise DeliveryOptionException(
                    "Project not specified. Enter project ID using "
                    "--project option or add to config file using "
                    "--config/-c option."
                )

            # If no owner is set assume current user is owner
            if self.project_owner is None:
                self.project_owner = self.user.username
                return

        # Config file ------------ credentials in it ------------ Config file #
        user_config = Path(config).resolve()
        try:
            # Get info from credentials file
            with user_config.open(mode='r') as cf:
                credentials = json.load(cf)
        except OSError as ose:
            sys.exit(f"Could not open path-file {config}: {ose}")

        # Check that all credentials are entered and quit if not
        if not all(c in credentials for c
                   in ['username', 'password', 'project']):
            raise DeliveryOptionException(
                "The config file does not contain all required information."
            )

        # Save username, password and project_id from credentials file
        self.user.username = credentials['username']
        self.user.password = credentials['password']
        self.project_id = credentials['project']

        # If owner specified - ok
        if 'owner' in credentials:
            self.project_owner = credentials['owner']
            return

        # If owner not specified and trying to out -- error
        if self.project_owner is None and self.method == 'put':
            raise DeliveryOptionException("Project owner not specified. "
                                          "Cancelling delivery.")

    def _clear_tempdir(self):
        '''Remove all contents from temporary file directory

        Raises:
            DeliverySystemException:    Deletion of temporary folder failed

        '''

        for d in [x for x in DIRS[1].iterdir() if x.is_dir()]:
            try:
                shutil.rmtree(d)
            except DeliverySystemException as e:
                self.LOGGER.exception(
                    f"Failed emptying the temporary folder {d}: {e}"
                )

    def _data_to_deliver(self, data: tuple, pathfile: str) -> (list):
        '''Puts all entered paths into one list

        Args:
            data:       Tuple containing paths
            pathfile:   Path to file containing paths

        Returns:
            list:   List of all paths entered in data and pathfile option

        Raises:
            IOError:                    Pathfile not found
            DeliveryOptionException:    Multiple identical files or
                                        false delivery method
        '''

        # Variables ##################################### Variables #
        all_files = dict()
        initial_fail = dict()

        data_list = list(data)
        # ----------------------------------------------------------#

        # Get all paths from pathfile
        if pathfile is not None and Path(pathfile).exists():
            with Path(pathfile).resolve().open(mode='r') as file:
                data_list += [line.strip() for line in file]

        # If not a correct method fail delivery
        if self.method not in ["get", "put"]:
            raise DeliveryOptionException(
                "Delivery option {self.method} not allowed. "
                "Cancelling delivery."
            )

        # Gather data info ####################### Gather data info #
        # Iterate through all user specified paths
        for d in data_list:
            # Throw error if there are duplicate files
            if d in all_files or Path(d).resolve() in all_files:
                raise DeliveryOptionException(
                    f"The path to file {d} is listed multiple times, "
                    "please remove path dublicates."
                )

            # If downloading - empty dict for file info
            # If uploading - check file contents
            if self.method == "get":
                iteminfo = self._get_download_info(item=d)
                # If folder info returned -- did not find contents of folder
                # or it doesn't exist
                if len(iteminfo) == 1 and d in iteminfo:
                    if not iteminfo[d]['proceed']:
                        initial_fail.update(iteminfo)
                        continue

                    all_files.update(iteminfo)
                else:
                    for f in iteminfo:
                        if not iteminfo[f]['proceed']:
                            initial_fail[f] = iteminfo[f]
                            continue

                        all_files[f] = iteminfo[f]

            elif self.method == "put":
                # Error if path doesn't exist -- should be checked by click
                if not Path(d).exists():
                    raise OSError("Trying to deliver a non-existing file/"
                                  f"folder: {d} -- Delivery not possible.")

                # Get file for files within folder
                curr_path = Path(d).resolve()   # Full path to data
                if curr_path.is_dir():  # Get info on files in folder
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

        return all_files, initial_fail

    def _finalize(self, file: Path, info: dict) -> (bool):
        '''Makes sure that the file is not in bucket or db and deletes
        if it is.

        Args:
            file (Path):    Path to file
            info (dict):    Info about file --> don't use around with real dict

        Returns:
            bool:   True if deletion successful

        '''

        with S3Connector(bucketname=self.bucketname,
                         project=self.s3project) as s3:
            if info['upload']['finished'] and \
                    not info['database']['finished']:
                try:
                    s3.delete_item(key=info['new_file'])
                except ClientError as e:
                    self.LOGGER.warning(e)
                    return False

        with DatabaseConnector(db_name='project_db') as prdb:

            try:
                proj = prdb[self.project_id]
                if info['database']['finished'] and \
                        not info['upload']['finished']:
                    del proj['files'][info['new_file']]
            except CouchDBException as e:
                self.LOGGER.warning(e)
                return False

        return True

    def _get_dir_info(self, folder: Path) -> (dict, dict):
        '''Iterate through folder contents and get file info

        Args:
            folder (Path):  Path to folder

        Returns:
            dict:   Files to deliver
            dict:   Files which failed -- not to deliver
        '''

        # Variables ########################## Variables #
        dir_info = {}   # Files to deliver
        dir_fail = {}   # Failed files
        # -----------------------------------------------#

        # Iterate through folder contents and get file info
        for f in folder.glob('**/*'):
            if f.is_file() and "DS_Store" not in str(f):    # CHANGE LATER
                file_info = self._get_file_info(file=f,
                                                in_dir=True,
                                                dir_name=folder)
                self.LOGGER.debug(file_info)
                # If file check failed in some way - do not deliver file
                # Otherwise deliver file -- no cancellation of folder here
                if not file_info['proceed']:
                    dir_fail[f] = file_info
                else:
                    dir_info[f] = file_info     # Deliver file

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

        # Check if file or folder exists in database
        with DatabaseConnector(db_name='project_db') as project_db:
            # self.LOGGER.debug(project_db[self.project_id]['files'])
            for file in project_db[self.project_id]['files']:
                # If path matches items in database, get info on file
                if file.startswith(item):
                    to_download[file] = {
                        **project_db[self.project_id]['files'][file],
                        **gen_finfo
                    }
                    # self.LOGGER.debug(f"{to_download[file]}")
                    in_db = True

                    in_directory = to_download[file]['directory_path'] != "."
                    to_download[file].update({
                        'new_file': DIRS[1] / Path(file),
                        'in_directory': in_directory,
                        'dir_name': item if in_directory else None,
                        'proceed': proceed,
                        'error': error
                    })

            # If the file doesn't exist in the database -- no delivery
            if not in_db:
                error = f"Item: {item} -- not in database"
                self.LOGGER.warning(error)
                return {item: {'proceed': False, 'error': error}}

        # If item in database, check S3 bucket for item(s)
        with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                as s3:

            # If folder - can contain more than one
            for file in to_download:
                in_bucket, s3error = s3.file_exists_in_bucket(key=file,
                                                              put=False)
                # self.LOGGER.debug(f"Item: {item}, File: {file}, "
                #                   f"In bucket: {in_bucket}, Error: {s3error}")

                # If not in bucket then error
                if not in_bucket:
                    error = (f"File '{file}' in database but NOT in S3 bucket."
                             f"Error in delivery system! {s3error}")
                    to_download[file].update({'proceed': False,
                                              'error': error})
                else:
                    none_in_bucket = False

            # If none of the files were in S3 bucket then error
            if none_in_bucket:
                error = (f"Item: {item} -- not in S3 bucket, but in database "
                         f"-- Error in delivery system!")
                self.LOGGER.warning(error)
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
        path_base = dir_name.name if in_dir else None   # Folder name if in dir
        directory_path = get_root_path(file=file, path_base=path_base) \
            if path_base is not None else Path("")  # Path to file in folder
        suffixes = file.suffixes    # File suffixes
        proc_suff = ""              # Saves final suffixes
        error = ""                  # Error message
        dir_info = {'in_directory': in_dir, 'dir_name': dir_name}
        # ------------------------------------------------ #

        # Check if file is compressed and fail delivery on error
        compressed, error = is_compressed(file=file)
        if error != "":
            return {'proceed': False, 'error': error, **dir_info}

        # If file not compressed -- add zst (Zstandard) suffix to final suffix
        # If compressed -- info that DS will not compress
        if not compressed:
            # Warning if suffixes are in magic dict but file "not compressed"
            if set(suffixes).intersection(set(MAGIC_DICT)):
                self.LOGGER.warning(f"File '{file}' has extensions belonging "
                                    "to a compressed format but shows no "
                                    "indication of being compressed. Not "
                                    "compressing file.")

            proc_suff += ".zst"     # Update the future suffix
            # self.LOGGER.debug(f"File: {file} -- Added suffix: {proc_suff}")
        elif compressed:
            self.LOGGER.info(f"File '{file}' shows indication of being "
                             "in a compressed format. "
                             "Not compressing the file.")

        # Add (own) encryption format extension
        proc_suff += ".ccp"     # ChaCha20-Poly1305
        # self.LOGGER.debug(f"File: {file} -- Added suffix: {proc_suff}")

        # Path to file in temporary directory after processing, and bucket
        # after upload, >>including file name<<
        bucketfilename = str(directory_path / Path(file.name + proc_suff))

        # Check if file exists in database
        in_db = False
        with DatabaseConnector('project_db') as project_db:
            if bucketfilename in project_db[self.project_id]['files']:
                error = f"File '{file}' already exists in the database. "
                self.LOGGER.warning(error)
                # If --overwrite flag not specified cancel upload of file
                if not self.overwrite:
                    return {'proceed': False, 'error': error, **dir_info}

                # If --overwrite flag specified -- do not cancel
                in_db = True

        # Check if file exists in S3 bucket
        with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                as s3:
            # Check if file exists in bucket already
            in_bucket, s3error = s3.file_exists_in_bucket(bucketfilename)
            # self.LOGGER.debug(f"File: {file}\t In bucket: {in_bucket}")

            if s3error != "":
                error += s3error

            # If the file exists in bucket, but not in the database -- error
            if in_bucket:
                if not in_db:
                    error = (f"{error}\nFile '{file.name}' already exists in "
                             "bucket, but does NOT exist in database. " +
                             "Delivery cancelled, contact support.")
                    self.LOGGER.critical(error)
                    return {'proceed': False, 'error': error, **dir_info}

                # If file exists in bucket and in database and...
                # --overwrite flag not specified --> cancel file delivery
                # --overwrite flag --> deliver again, overwrite file
                if not self.overwrite:
                    return {'proceed': False, 'error': error, **dir_info}

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

    def finalize_delivery(self, file: str, fileinfo: dict):
        '''Finalizes delivery after download from s3'''

        # If DS noted cancelation of file -- quit and move on
        if not fileinfo['proceed']:
            return False, ""

        # Set file processing as in progress
        self.set_progress(item=file, decryption=True, started=True)

        decrypted, error = reverse_processing(file=file, file_info=fileinfo)
        return decrypted, error

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
                str:    Error message, "" if none
        '''

        # If DS noted cancelation of file -- quit and move on
        if not path_info['proceed']:
            return False, Path(""), 0, False, "", b''

        # Set file processing as in progress
        self.set_progress(item=path, processing=True, started=True)

        # Begin processing incl encryption
        info = process_file(file=path,
                            file_info=path_info)

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

        Returns:
            None

        Raises:
            DataException:  Data dictionary update failed

        '''

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

        if to_update == "":
            raise DeliverySystemException("Trying to update progress on "
                                          "forbidden process.")

        try:
            if started:
                self.data[item][to_update].update({'in_progress': started,
                                                   'finished': not started})
            elif finished:
                self.data[item][to_update].update({'in_progress': not finished,
                                                   'finished': finished})
        except DataException as dex:
            self.LOGGER.exception(f"Data delivery information failed to "
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

        critical_op = 'upload' if self.method == "put" else 'download'
        all_info = self.data[file]  # All info on file

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
                            # self.LOGGER.debug(self.failed)
                    return False

            # If individual file -- cancel this specific file only
            self.data[file].update({'proceed': False,
                                    'error': updinfo['error']})
            return False

        # If file to proceed, update file info
        try:
            self.data[file].update(updinfo)
        except DataException as dex:
            self.LOGGER.exception(f"Data delivery information failed to "
                                  f"update: {dex}")

        return True

    def get_recipient_key(self, keytype="public"):
        """Retrieves the recipient public key from the database."""

        with DatabaseConnector() as dbconnection:
            try:
                project_db = dbconnection['project_db']
            except CouchDBException as cdbe2:
                sys.exit(f"Could not connect to the user database: {cdbe2}")
            else:
                if self.project_id not in project_db:
                    raise CouchDBException(f"The project {self.project_id} "
                                           "does not exist.")

                if 'project_info' not in project_db[self.project_id]:
                    raise CouchDBException("There is no project information"
                                           "registered for the specified "
                                           "project.")

                if 'owner' not in project_db[self.project_id]['project_info']:
                    raise CouchDBException("The specified project does not "
                                           "have a recorded owner.")

                if self.project_owner != project_db[self.project_id]['project_info']['owner']:
                    raise CouchDBException(f"The user {self.project_owner} "
                                           "does not exist.")

                if 'project_keys' not in project_db[self.project_id]:
                    raise CouchDBException("Could not find any projects for "
                                           f"the user {self.project_owner}.")

                if keytype not in project_db[self.project_id]['project_keys']:
                    raise CouchDBException(
                        "There is no public key recorded for "
                        f"user {self.project_owner} and "
                        f"project {self.project_id}."
                    )

                return bytes.fromhex(project_db[self.project_id]['project_keys'][keytype])

    def update_data_dict(self, path: str, pathinfo: dict) -> (bool):
        '''Update file information in data dictionary.

        Args:
            path:       Path to file
            pathinfo:   Information about file incl. potential errors

        Returns:
            bool:   True if info update succeeded
        '''

        try:
            proceed = pathinfo['proceed']   # All ok so far --> processing
            self.data[path].update(pathinfo)    # Update file info
        except Exception as e:  # FIX EXCEPTION HERE
            self.LOGGER.critical(e)
            return False
        else:
            if not proceed:     # Cancel delivery of file
                nl = '\n'
                emessage = (
                    f"{pathinfo['error'] + nl if 'error' in pathinfo else ''}"
                )
                self.LOGGER.exception(emessage)
                # If the processing failed, the e_size is an exception
                self.data[path]['error'] = emessage

                if self.data[path]['in_directory']:  # Failure in folder > all fail
                    to_stop = {
                        key: val for key, val in self.data.items()
                        if self.data[key]['in_directory'] and
                        (val['dir_name'] == self.data[path]['dir_name'])
                    }

                    for f in to_stop:
                        self.data[f]['proceed'] = proceed
                        self.data[f]['error'] = (
                            "One or more of the items in folder "
                            f"'{self.data[f]['dir_name']}' (at least '{path}') "
                            "has already been delivered!"
                        )
                        if 'up_ok' in self.data[path]:
                            self.data[f]['up_ok'] = self.data[path]['up_ok']
                        if 'db_ok' in self.data[path]:
                            self.data[f]['db_ok'] = self.data[path]['db_ok']

            # self.LOGGER.debug(self.data[path])
            return True

    ################
    # Main Methods #
    ################
    def get(self, path: str, path_info: dict) -> (str):
        '''Downloads specified data from S3 bucket

        Args:
            file:           File to be downloaded
            dl_file:        Name of downloaded file

        Returns:
            str:    Success message if download successful

        '''

        # If DS noted cancelation of file -- quit and move on
        if not path_info['proceed']:
            return False, ""

        # Set file processing as in progress
        self.set_progress(item=path, download=True, started=True)

        new_dir = DIRS[1] / Path(path_info['directory_path'])
        # If new temporary subdir doesn't exist -- create it
        if not new_dir.exists():
            try:
                new_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                error = (f"File: {path} -- Creating tempdir "
                         f"{new_dir} failed! :: {e}")
                LOG.exception(error)
                return False, error
        # self.LOGGER.debug(f"new_dir: {new_dir}")

        # UPLOAD START ######################################### UPLOAD START #
        with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                as s3:

            try:
                # Upload file
                s3.resource.meta.client.download_file(
                    Bucket=s3.bucketname,
                    Key=path,
                    Filename=str(path_info['new_file'])
                )
            except Exception as e:   # FIX EXCEPTION HERE
                # Upload failed -- return error message and move on
                error = (f"File: {path}, Downloaded: "
                         f"{path_info['new_file']} -- "
                         f"Download failed! -- {e}")
                self.LOGGER.exception(error)
                return False, error
            else:
                # Upload successful
                self.LOGGER.info(f"File downloaded: {path}"
                                 f", File location: {path_info['new_file']}")
                return True, ""

        #     for file in file_in_bucket:
        #         new_path = DIRS[1] / \
        #             Path(file.key)  # Path to downloaded
        #         if not new_path.parent.exists():
        #             try:
        #                 new_path.parent.mkdir(parents=True)
        #             except IOError as ioe:
        #                 sys.exit("Could not create folder "
        #                          f"{new_path.parent}. Cannot"
        #                          "proceed with delivery. Cancelling: "
        #                          f"{ioe}")

        #         if not new_path.exists():
        #             try:
        #                 self.s3.resource.meta.client.download_file(
        #                     self.s3.bucket.name,
        #                     file.key, str(new_path))
        #             except Exception as e:
        #                 self.data[path][new_path] = {"downloaded": False,
        #                                              "error": e}
        #             else:
        #                 self.data[path][new_path] = {"downloaded": True}

        #         else:
        #             print(f"File {str(new_path)} already exists. "
        #                   "Not downloading.")
        #     return True, path

        # raise S3Error(f"Bucket {self.s3.bucket.name} does not exist.")

    def put(self, file: Path, fileinfo: dict) -> (bool, Path, list, list, str):
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

        # If DS noted cancelation of file -- quit and move on
        if not fileinfo['proceed']:
            error = ""
            # If processing not performed --> quit and move on
            if not fileinfo['processing']['finished']:
                error = (f"File: '{file}' -- File not processed (e.g. "
                         "encrypted). Bug in code. Moving on to next file.")
                self.LOGGER.critical(error)

            return False, error

        # Set delivery as in progress
        self.set_progress(item=file, upload=True, started=True)

        # UPLOAD START ######################################### UPLOAD START #
        with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                as s3:

            try:
                # Upload file
                s3.resource.meta.client.upload_file(
                    Filename=str(fileinfo['encrypted_file']),
                    Bucket=s3.bucketname,
                    Key=fileinfo['new_file']
                )
            except Exception as e:   # FIX EXCEPTION HERE
                # Upload failed -- return error message and move on
                error = (f"File: {file}, Uploaded: "
                         f"{fileinfo['encrypted_file']} -- "
                         f"Upload failed! -- {e}")
                self.LOGGER.exception(error)
                return False, error
            else:
                # Upload successful
                self.LOGGER.info(f"File uploaded: {fileinfo['encrypted_file']}"
                                 f", Bucket location: {fileinfo['new_file']}")
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

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.id = None
        self.role = None

# PROGRESS BAR ################################################# PROGRESS BAR #


class ProgressPercentage(object):

    def __init__(self, filename, filesize):
        self._filename = filename
        self._size = filesize
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(f"\r{self._filename}  {self._seen_so_far} / "
                             f"{self._size}  ({percentage:.2f}%)")
            sys.stdout.flush()

# FUNCTIONS ####################################################### FUNCTIONS #


def finish_download(file, recipient_sec, sender_pub):
    '''Finishes file download, including decryption and
    checksum generation'''

    if isinstance(file, Path):
        try:
            dec_file = Path(str(file).split(
                file.name)[0]) / Path(file.stem)
        except Exception:   # FIX EXCEPTION
            sys.exit("FEL")
        finally:
            original_umask = os.umask(0)
            with file.open(mode='rb') as infile:
                with dec_file.open(mode='ab+') as outfile:
                    lib.decrypt(keys=[(0, recipient_sec, sender_pub)],
                                infile=infile,
                                outfile=outfile)
            os.umask(original_umask)

    return file
