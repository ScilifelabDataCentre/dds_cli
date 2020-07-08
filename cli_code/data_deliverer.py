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

from cli_code import DIRS, LOG_FILE
from cli_code.exceptions_ds import DeliveryOptionException, \
    DeliverySystemException, CouchDBException, S3Error
from cli_code.s3_connector import S3Connector
from cli_code.crypto_ds import secure_password_hash
from cli_code.database_connector import DatabaseConnector
from cli_code.file_handler import config_logger, get_root_path, \
    is_compressed, MAGIC_DICT, process_file

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
                 pathfile=None, data=None, break_on_fail=True):

        # Quit execution if none of username, password, config are set
        if all(x is None for x in [username, password, config]):
            raise DeliverySystemException(
                "Delivery System login credentials not specified. "
                "Enter: \n--username/-u AND --password/-pw,"
                " or --config/-c\n --owner/-o\n"
                "For help: 'ds_deliver --help'."
            )

        # Initialize attributes
        self.break_on_fail = break_on_fail
        self.method = sys._getframe().f_back.f_code.co_name  # put or get
        self.user = _DSUser(username=username, password=password)
        self.project_id = project_id        # Project ID - not S3
        self.project_owner = project_owner  # User, not facility
        self.data = None           # Dictionary, keeps track of delivery

        # S3 related
        self.bucketname = ""    # S3 bucket name -- to connect to S3
        self.s3project = ""     # S3 project ID -- to connect to S3

        # Check if all required info is entered
        self._check_user_input(config=config)

        # Check if user has access to delivery system
        ds_access_granted = self._check_ds_access()
        if ds_access_granted and self.user.id is not None:
            # Check users access to specified project
            proj_access_granted, self.s3project = self._check_project_access()
            if proj_access_granted and self.s3project is not None:
                # If no data to upload, cancel
                if not data and not pathfile:
                    raise DeliverySystemException(
                        "No data to be uploaded. Specify individual "
                        "files/folders using the --data/-d option one or "
                        "more times, or the --pathfile/-f. "
                        "For help: 'ds_deliver --help'"
                    )
                else:
                    self.data = self._data_to_deliver(data=data,
                                                      pathfile=pathfile)
            else:
                raise DeliverySystemException(
                    f"Access to project {self.project_id} "
                    "denied. Delivery cancelled."
                )
        else:
            raise DeliverySystemException("Delivery System access denied! "
                                          "Delivery cancelled.")

        if self.data is not None:
            self.tempdir = DIRS

            # Initialize logger
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
            # self.LOGGER.debug(f"-- Login successful -- \n"
            #                   f"\t\tmethod: {self.method}, \n"
            #                   f"\t\tusername: {self.user.username}, \n"
            #                   f"\t\tpassword: {self.user.password}, \n"
            #                   f"\t\tproject ID: {self.project_id}, \n"
            #                   f"\t\tproject owner: {self.project_owner}, \n"
            #                   f"\t\tdata: {self.data} \n")

            self.bucketname = f"project_{self.project_id}"
            # self.LOGGER.debug(f"S3 bucket: {self.bucketname}")

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

        succeeded = PrettyTable(['Item', 'Location'])
        failed = PrettyTable(['Item', 'Error'])
        suc_dict = {}
        fai_dict = {}
        succeeded.align['Delivered item'] = "r"
        failed.align['Failed item'] = "r"
        succeeded.align['Location'] = "l"
        failed.align['Error'] = "l"
        succeeded.padding_width = 2
        failed.padding_width = 2
        wrapper = textwrap.TextWrapper(width=100)

        for f in self.data:
            if self.data[f]["proceed"] and self.data[f]['upload']['finished']:
                suc = str(self.data[f]['dir_name']) \
                    if self.data[f]["in_directory"] else str(f)
                loc = str(self.data[f]["directory_path"]) + "\n" \
                    if self.data[f]["in_directory"] \
                    else str(self.data[f]['directory_path']) + "\n"

                if suc not in suc_dict:
                    succeeded.add_row([suc, loc])
                    suc_dict[suc] = loc
            else:
                finalized = self._finalize(file=f)
                # Print failed items
                fail = str(self.data[f]['dir_name']) \
                    if self.data[f]['in_directory'] else str(f)
                err = '\n'.join(wrapper.wrap(self.data[f]["error"])) + "\n" \
                    if self.data[f]['in_directory'] else \
                    '\n'.join(wrapper.wrap(self.data[f]['error'])) + "\n"

                if fail not in fai_dict:
                    failed.add_row([fail, err])
                    fai_dict[fail] = err

        self._clear_tempdir()

        if len(suc_dict) > 0:
            self.LOGGER.info("----DELIVERY COMPLETED----")
            self.LOGGER.info(
                f"The following items were uploaded:\n{succeeded}\n")
        if len(fai_dict) == len(suc_dict) + len(fai_dict):
            self.LOGGER.error("----DELIVERY FAILED----")
        if len(fai_dict) > 0:
            self.LOGGER.error(
                f"The following items were NOT uploaded:\n{failed}\n")

    ###################
    # Private Methods #
    ###################
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

        # If config file not entered use loose credentials
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

        # If config file specified move on to check credentials in it
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
        if 'owner' in credentials:
            self.project_owner = credentials['owner']
            return

        if self.project_owner is None and self.method == 'put':
            raise DeliveryOptionException("Project owner not specified. "
                                          "Cancelling delivery.")

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
                    password_hash = \
                        secure_password_hash(
                            password_settings=password_settings,
                            password_entered=self.user.password
                        )
                    # Compare to correct password
                    if user_db[id_]['password']['hash'] != password_hash:
                        raise DeliverySystemException(
                            "Wrong password. Access to Delivery System denied."
                        )

                    # Check that facility putting or researcher getting
                    self.user.role = user_db[id_]['role']
                    if (self.user.role == 'facility'and self.method == 'put') \
                            or (self.user.role == 'researcher' and self.method == 'get'):
                        self.user.id = id_  # User granted access to put or get

                        if (self.user.role == 'researcher' and self.method == 'get'
                                and (self.project_owner is None or
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

    def _clear_tempdir(self):
        '''Remove all contents from temporary file directory'''

        for d in [x for x in self.tempdir[1].iterdir() if x.is_dir()]:
            try:
                shutil.rmtree(d)
            except Exception as e:  # FIX EXCEPTION HERE
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

        all_files = dict()
        data_list = list(data)

        # Get all paths from pathfile
        if pathfile is not None and Path(pathfile).exists():
            with Path(pathfile).resolve().open(mode='r') as file:
                data_list += [line.strip() for line in file]

        for d in data_list:
            # Throw error if there are duplicate files
            if d in all_files or Path(d).resolve() in all_files:
                raise DeliveryOptionException(
                    f"The path to file {d} is listed multiple times, "
                    "please remove path dublicates."
                )

            if Path(d).exists():     # Should always be valid for put
                curr_path = Path(d).resolve()
                if curr_path.is_file():  # Save file info to dict
                    path_base = None
                    all_files[curr_path] = \
                        {"in_directory": False,
                         "dir_name": None,
                         "path_base": path_base,
                         "directory_path": get_root_path(
                             file=curr_path,
                             path_base=path_base
                         ),   # path in bucket & tempfolder
                         "size": curr_path.stat().st_size,
                         "suffixes": curr_path.suffixes,
                         'proceed': True,
                         'encrypted_file': Path(""),
                         'encrypted_size': 0,
                         'filecheck': {'in_progress': False,
                                       'finished': False},
                         'processing': {'in_progress': False,
                                        'finished': False},
                         'upload': {'in_progress': False,
                                    'finished': False}}
                elif curr_path.is_dir():  # Get info on files in folder
                    path_base = curr_path.name
                    all_files.update({f: {"in_directory": True,
                                          "dir_name": curr_path,
                                          "path_base": path_base,
                                          "directory_path": get_root_path(
                                              file=f,
                                              path_base=path_base
                                          ),  # path in bucket & tempfolder
                                          "size": f.stat().st_size,
                                          "suffixes": f.suffixes,
                                          'proceed': True,
                                          'encrypted_file': Path(""),
                                          'encrypted_size': 0,
                                          'filecheck': {'in_progress': False,
                                                        'finished': False},
                                          'processing': {'in_progress': False,
                                                         'finished': False},
                                          'upload': {'in_progress': False,
                                                     'finished': False},
                                          'database': {'in_progress': False,
                                                       'finished': False}}
                                      for f in curr_path.glob('**/*')
                                      if f.is_file()
                                      and "DS_Store" not in str(f)})

            else:
                if self.method == "put":
                    error_message = "Trying to deliver a non-existing " \
                        f"file/folder: {d} -- Delivery not possible."
                    LOG.fatal(error_message)
                    all_files[d] = {'proceed': False,
                                    'error': error_message}
                elif self.method == "get":
                    all_files[d] = {}
                else:
                    raise DeliveryOptionException(
                        "Delivery option {self.method} not allowed. "
                        "Cancelling delivery."
                    )
        return all_files

    def _finalize(self, file: Path) -> (bool):
        '''Makes sure that the file is not in bucket or db and deletes
        if it is.

        Args:
            file:   Path to file

        Returns:
            bool:   True if deletion successful
        '''

        try:
            with S3Connector(bucketname=self.bucketname,
                             project=self.s3project) as s3:
                if all(x in self.data[file] for x in ['new_file', 'up_ok']) \
                        and self.data[file]['up_ok']:
                    s3.delete_item(key=self.data[file]['new_file'])
        except Exception as e:  # FIX EXCEPTION HERE
            self.LOGGER.warning(e)
            return False

        try:
            with DatabaseConnector(db_name='project_db') as prdb:
                proj = prdb[self.project_id]

                if 'new_file' in self.data[file] and self.data[file]['proceed'] \
                        and 'db_ok' in self.data[file] and self.data[file]['db_ok']:
                    del proj['files'][self.data[file]['new_file']]
        except Exception as e:  # FIX EXCEPTION HERE
            self.LOGGER.warning(e)
            return False

        return True

    ##################
    # Public Methods #
    ##################

    def do_file_checks(self, file: Path, fileinfo: dict) -> (bool, bool, str):
        '''Checks if file is compressed and if it has already been delivered.

        Args:
            file (Path):       Path to file
            fileinfo (dict):   Info about file and delivery

        Returns:
            tuple:  Information on if the file is compressed, whether or not
                    to proceed with the delivery of the file, and the file path
                    after (future) processing.

                bool:   True if delivery should proceed for file
                bool:   True if file is already compressed
                str:    Bucketfilename -- File path with new suffixes
                str:    Error message, "" if none
        '''

        # Set file check as in progress
        self.set_progress(item=file, check=True, started=True)

        # Variables ############################################### Variables #
        proc_suff = ""      # Saves final suffixes
        # ------------------------------------------------------------------- #

        # Check if compressed
        compressed, error = is_compressed(file)
        if error != "":     # If error in checking compression format quit file
            return False, compressed, "", error

        # If file not compressed -- add zst (Zstandard) suffix to final suffix
        if not compressed:
            # Warning if suffixes are in magic dict but file "not compressed"
            if set(fileinfo['suffixes']).intersection(set(MAGIC_DICT)):
                self.LOGGER.warning(f"File '{file}' has extensions belonging "
                                    "to a compressed format but shows no "
                                    "indication of being compressed. Not "
                                    "compressing file.")

            proc_suff += ".zst"     # Update the future suffix
            # self.LOGGER.debug(f"File: {file} -- Added suffix: {proc_suff}")
        elif compressed:
            self.LOGGER.warning(f"File '{file}' shows indication of being "
                                "in a compressed format. "
                                "Not compressing the file.")

        proc_suff += ".ccp"     # ChaCha20 (encryption format) extension added
        # self.LOGGER.debug(f"File: {file} -- Added suffix: {proc_suff}")

        # Path to file in temporary directory after processing, and bucket
        # after upload, >>including file name<<
        bucketfilename = str(fileinfo['directory_path'] /
                             Path(file.name + proc_suff))
        # self.LOGGER.debug(f"File: {file}\t Bucket path: {bucketfilename}")

        # If file exists in DB -- cancel delivery of file
        with DatabaseConnector('project_db') as project_db:
            if bucketfilename in project_db[self.project_id]['files']:
                error = f"File '{file}' already exists in the database. "
                self.LOGGER.warning(error)
                return False, compressed, bucketfilename, error

        # If file exists in S3 bucket -- cancel delivery of file
        with S3Connector(bucketname=self.bucketname, project=self.s3project) \
                as s3:
            # Check if file exists in bucket already
            in_bucket, error = s3.file_exists_in_bucket(bucketfilename)
            # self.LOGGER.debug(f"File: {file}\t In bucket: {in_bucket}")

            if in_bucket:  # If the file is already in bucket
                error = (f"{error}\nFile '{file.name}' already exists in "
                         "bucket, but does NOT exist in database. " +
                         "Delivery cancelled, contact support.")
                self.LOGGER.critical(error)
                return False, compressed, bucketfilename, error

        # Proceed with delivery and return info on file
        return True, compressed, bucketfilename, error

    def prep_upload(self, path: Path, path_info: dict) \
            -> (tuple):
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
            error = ""
            # If file checks incl compression check, db check etc,
            # not done --> quit and move on.
            if not path_info['filecheck']['finished']:
                error = (f"File: '{path}' -- Content checks etc not performed."
                         " Bug in code. Moving on to next file.")
                self.LOGGER.critical(error)

            return False, Path(""), 0, False, error

        # Set file processing as in progress
        self.set_progress(item=path, processing=True, started=True)

        # Begin processing incl encryption
        info = process_file(file=path,
                            file_info=path_info,
                            filedir=self.tempdir[1])

        return info

    def update_delivery(self, file, updinfo):

        # self.LOGGER.debug(f"Updating file: {file}:: {updinfo}")
        if not updinfo['proceed']:

            if self.data[file]['in_directory']:
                # self.LOGGER.debug(f"File {file} in directory")
                if self.break_on_fail:
                    for path, info in self.data.items():
                        if info['dir_name'] == self.data[file]['dir_name'] \
                                and not info['upload']['in_progress'] \
                                and not info['upload']['finished']:
                            self.data[path].update(
                                {'proceed': False,
                                 'error': f"Failed file: {file} -- "
                                 f"{updinfo['error']}"}
                            )
                        # self.LOGGER.debug(f"Updating file: {path} -- {info} --> "
                        #                   f"\nUpdated? -- {self.data[path]}")
                    return

            upd = self.data[file].update({'proceed': False,
                                          'error': updinfo['error']})
            # self.LOGGER.debug(f"-------{upd}")
            return

        try:
            upd = self.data[file].update(updinfo)
            # self.LOGGER.debug(f"-------{upd}")
        except Exception as exc:
            self.LOGGER.exception(exc)

        # self.LOGGER.debug(f"Updating file: {file} -- {updinfo} --> "
        #                   f"\nUpdated? -- {self.data[file]}")
        return

    def set_progress(self, item: Path, check: bool = False,
                     processing: bool = False, upload: bool = False,
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

        '''

        to_update = ""
        if check:
            to_update = 'filecheck'
        elif processing:
            to_update = 'processing'
        elif upload:
            to_update = 'upload'
        elif db:
            to_update = 'database'

        if started:
            self.data[item][to_update].update({'in_progress': started,
                                               'finished': not started})
        elif finished:
            self.data[item][to_update].update({'in_progress': not finished,
                                               'finished': finished})

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
    def get(self, path: str) -> (str):
        '''Downloads specified data from S3 bucket

        Args:
            file:           File to be downloaded
            dl_file:        Name of downloaded file

        Returns:
            str:    Success message if download successful

        '''
        # Check if bucket exists
        if self.s3.bucket in self.s3.resource.buckets.all():
            # Check if path exists in bucket
            file_in_bucket = self.s3.files_in_bucket(key=path)

            for file in file_in_bucket:
                new_path = self.tempdir[1] / \
                    Path(file.key)  # Path to downloaded
                if not new_path.parent.exists():
                    try:
                        new_path.parent.mkdir(parents=True)
                    except IOError as ioe:
                        sys.exit("Could not create folder "
                                 f"{new_path.parent}. Cannot"
                                 "proceed with delivery. Cancelling: "
                                 f"{ioe}")

                if not new_path.exists():
                    try:
                        self.s3.resource.meta.client.download_file(
                            self.s3.bucket.name,
                            file.key, str(new_path))
                    except Exception as e:
                        self.data[path][new_path] = {"downloaded": False,
                                                     "error": e}
                    else:
                        self.data[path][new_path] = {"downloaded": True}

                else:
                    print(f"File {str(new_path)} already exists. "
                          "Not downloading.")
            return True, path

        raise S3Error(f"Bucket {self.s3.bucket.name} does not exist.")

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
                self.LOGGER.info("File uploaded: {fileinfo['encrypted_file']},"
                                 f"Bucket location: {fileinfo['new_file']}")
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
