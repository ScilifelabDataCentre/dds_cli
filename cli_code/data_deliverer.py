import json
import os
from pathlib import Path
import sys
import threading
import traceback
import logging


from cli_code.crypt4gh.crypt4gh import lib

from cli_code import DIRS, LOG_FILE
from cli_code.exceptions_ds import DeliveryOptionException, \
    DeliverySystemException, CouchDBException, S3Error
from cli_code.s3_connector import S3Connector
from cli_code.crypto_ds import secure_password_hash
from cli_code.database_connector import DatabaseConnector
from cli_code.file_handler import config_logger, get_root_path, \
    process_file, process_folder, is_compressed, update_dir

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
        project_id (str):       Project ID to upload to/download from
        project_owner (str):    Owner of the current project
        data (list):            Paths to files/folders
        tempdir (list):         Paths to temporary DP folders
        user (DSUser):          Data Delivery System user
        s3 (S3Connector):          S3 connection object

    Raises:
        DeliverySystemException:    Required info not found or access denied
        OSError:                    Temporary directory failure

    '''

    def __init__(self, config=None, username=None, password=None,
                 project_id=None, project_owner=None,
                 pathfile=None, data=None):

        # Quit execution if none of username, password, config are set
        if all(x is None for x in [username, password, config]):
            raise DeliverySystemException(
                "Delivery System login credentials not specified. "
                "Enter: \n--username/-u AND --password/-pw,"
                " or --config/-c\n --owner/-o\n"
                "For help: 'ds_deliver --help'."
            )

        # Initialize attributes
        self.method = sys._getframe().f_back.f_code.co_name  # put or get?
        self.user = DSUser(username=username, password=password)
        self.project_id = project_id
        self.project_owner = project_owner  # user, not facility
        self.data = None           # dictionary, keeps track of delivery
        self.bucketname = ""
        self.s3project = ""

        # Check if all required info is entered
        self.check_user_input(config=config)

        # Check if user has access to delivery system
        ds_access_granted = self.check_ds_access()
        if ds_access_granted and self.user.id is not None:
            # Check users access to specified project
            proj_access_granted, self.s3project = self.check_project_access()
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
                    self.data = self.data_to_deliver(data=data,
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
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.DEBUG)
            self.logger = config_logger(
                logger=self.logger, filename=self.logfile,
                file=True, file_setlevel=logging.DEBUG,
                fh_format="%(asctime)s::%(levelname)s::" +
                "%(name)s::%(lineno)d::%(message)s",
                stream=True, stream_setlevel=logging.DEBUG,
                sh_format="%(levelname)s::%(name)s::" +
                "%(lineno)d::%(message)s"
            )
            self.logger.debug(f"-- Login successful -- \n"
                              f"\t\tmethod: {self.method}, \n"
                              f"\t\tusername: {self.user.username}, \n"
                              f"\t\tpassword: {self.user.password}, \n"
                              f"\t\tproject ID: {self.project_id}, \n"
                              f"\t\tproject owner: {self.project_owner}, \n"
                              f"\t\tdata: {self.data} \n")

            self.bucketname = f"project_{self.project_id}"
            self.logger.debug(f"S3 bucket: {self.bucketname}")

            self.logger.info("Delivery initialization successful.")

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

        failed = {}
        succeeded = []
        for f in self.data:
            if "success" in self.data[f]:
                if self.data[f]["success"]:
                    if self.data[f]["path_base"] is not None:
                        succeeded.append(self.data[f]["path_base"])
                    else:
                        succeeded.append(f)
            elif "Error" in self.data[f]:
                failed[f] = self.data[f]["Error"]

        print("\n----DELIVERY COMPLETED----")
        if len(succeeded) != 0:
            print("\nThe following files were uploaded: ")
            succeeded = list(dict.fromkeys(succeeded))
            for u in succeeded:
                print(u)

        if failed != {}:
            print("\nThe following files were NOT uploaded: ")
            for n_u in failed:
                print(f"{n_u}\t -- {failed[n_u]}")

        print("\n--------------------------")

    def check_user_input(self, config):
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
        if not all(c in credentials
                   for c in ['username', 'password', 'project']):
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

    def check_ds_access(self):
        '''Checks the users access to the delivery system

        Returns:
            tuple:  Granted access and user ID

                bool:   True if user login successful
                str:    User ID

        Raises:
            CouchDBException:           Database connection failure or
                                        user not found
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

    def check_project_access(self):
        '''Checks the users access to a specific project.

        Returns:
            tuple:  Project access and S3 project ID

                bool:   True if project access granted
                str:    S3 project to upload to/download from

        Raises:
            CouchDBException:           Database connection failure
                                        or missing project information
            DeliverySystemException:    Access denied
            DeliveryOptionException:    S3 delivery option not available
                                        or incorrect project owner
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

    def data_to_deliver(self, data: tuple, pathfile: str) -> (list):
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
                        {"file": True,
                         "directory": False,
                         "contents": None,
                         "path_base": path_base,
                         "directory_path": get_root_path(
                             file=curr_path,
                             path_base=path_base
                         ),   # path in bucket & tempfolder
                         "size": curr_path.stat().st_size,
                         "suffixes": curr_path.suffixes}
                    print(f"{curr_path}: {all_files[curr_path]}")
                elif curr_path.is_dir():  # Get info on files in folder
                    path_base = curr_path.name
                    all_files[curr_path] = \
                        {
                            "file": False,
                            "directory": True,
                            "contents": {f: {"file": True,
                                             "directory": False,
                                             "contents": None,
                                             "path_base": path_base,
                                             "directory_path": get_root_path(
                                                 file=f,
                                                 path_base=path_base
                                             ),  # path in bucket & tempfolder
                                             "size": f.stat().st_size,
                                             "suffixes": f.suffixes}
                                         for f in curr_path.glob('**/*')
                                         if f.is_file()
                                         and "DS_Store" not in str(f)}
                    }

            else:
                if self.method == "put":
                    error_message = "Trying to deliver a non-existing " \
                        f"file/folder: {d} -- Delivery not possible."
                    LOG.fatal(error_message)
                    all_files[d] = {"error": error_message}
                elif self.method == "get":
                    all_files[d] = {}
                else:
                    raise DeliveryOptionException(
                        "Delivery option {self.method} not allowed. "
                        "Cancelling delivery."
                    )

        return all_files

    def do_file_checks(self, file, file_info):
        ''''''

        self.logger.debug(f"do file checks: {file}")
        proceed = True

        # Check if compressed and save algorithm info if yes
        compressed, alg = is_compressed(file)
        self.logger.debug(f"{compressed}, {alg}")

        proc_suff = ""  # Suffix after file processed
        LOG.debug(f"Original suffixes: {''.join(file_info['suffixes'])}")
        if not compressed:
            # check if suffixes are in magic dict

            # update the future suffix
            proc_suff += ".zst"
            alg = ".zst"
            self.logger.debug(f"File {file.name} not compressed. "
                              f"New file suffix: {proc_suff}")
        elif compressed and alg not in file_info['suffixes']:
            self.logger.warning(f"Indications of the file '{file}' being in a "
                                f"compressed format but extension {alg} not "
                                "present in file extensions. Not compressing "
                                "the file.")

        proc_suff += ".ccp"     # chacha extension
        self.logger.debug(f"New file suffix: {proc_suff}")

        bucketfilename = str(file_info['directory_path'] /
                             Path(file.name + proc_suff))
        self.logger.debug(f"bucket file name: {bucketfilename}")
        # Check if file/folder exists in bucket
        with S3Connector(bucketname=self.bucketname,
                         project=self.s3project) as s3:
            # Check if file exists in bucket already
            exists = s3.file_exists_in_bucket(
                bucketfilename
            )
            if exists:
                self.logger.warning(
                    f"{file.name} already exists in bucket")
                proceed = False

        # filedir = update_dir(
        #     self.tempdir.files,
        #     file_info['directory_path']
        # )
        # self.logger.debug(f"filedir : {filedir}")
        return proceed, compressed, alg, bucketfilename

    def get_content_info(self, item):

        proceed = False

        self.logger.debug(f"item: {item}")

        if item.is_file():
            proceed, compressed, algorithm, new_file = \
                self.do_file_checks(
                    file=item, file_info=self.data[item]
                )
            self.logger.debug(f"proceed: {proceed}, \n"
                              f"compressed: {compressed}, \n"
                              f"algorithm: {algorithm}, \n"
                              f"new_file: {new_file} \n")
            if proceed:
                self.data[item].update({"compressed": compressed,
                                        "algorithm": algorithm,
                                        "new_file": new_file})

        elif item.is_dir():
            folder_file_info = {}

            # Check if compressed archive first
            '''here'''

            # if not compressed archive check files
            for file in self.data[item]['contents']:
                proceed, compressed, algorithm, new_file = \
                    self.do_file_checks(
                        file=file,
                        file_info=self.data[item]['contents'][file]
                    )
                if proceed:
                    folder_file_info[file] = {"compressed": compressed,
                                              "algorithm": algorithm,
                                              "new_file": new_file}
                else:
                    return proceed

            for file in self.data[item]['contents']:
                self.data[item]['contents'][file].update(
                    folder_file_info[file]
                )

        self.data[item].update({"error": "Exists"})

        return proceed

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

    def put(self, file: str, spec_path: str, orig_file: str) -> (str):
        '''Uploads specified data to the S3 bucket.

        Args:
            file:       File to be uploaded
            spec_path:  Root folder path to file
        '''

        filepath = str(spec_path / Path(file.name))
        self.logger.debug(f"Path in bucket: {filepath}")

        # Return error if bucket doesn't exist
        if self.s3.bucket not in self.s3.resource.buckets.all():
            self.logger.critical("Bucket not found in S3 resource. Upload will"
                                 " not be possible. "
                                 f"Bucket: {self.s3.bucket.name}")
            return orig_file, file, False, "Bucket not found in S3 resource"

        # Check if file exists (including path)
        file_already_in_bucket = self.s3.file_exists_in_bucket(key=filepath)
        self.logger.warning("file already in bucket: "
                            f"{file_already_in_bucket}")

        # Upload if doesn't exist
        if file_already_in_bucket:
            self.logger.warning("File already exists in bucket, will not be "
                                f"uploaded. File: {file}")
            return orig_file, file, False, filepath, "exists"
        else:
            self.logger.debug(f"Beginning upload of file {file} ({orig_file})")
            try:
                self.s3.resource.meta.client.upload_file(
                    str(file), self.s3.bucket.name,
                    filepath
                )
            except Exception as e:   # FIX EXCEPTION
                self.logger.exception(f"Upload failed! {e} -- file: {file} "
                                      f"({orig_file})")
                return orig_file, file, False, e
            else:
                self.logger.info(f"Upload completed! file: {file} "
                                 f"({orig_file}). Bucket location: {filepath}")
                return orig_file, file, True, filepath

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
                new_path = self.tempdir.files / \
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

# DSUSER ############################################################## DSUER #


class DSUser():
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
