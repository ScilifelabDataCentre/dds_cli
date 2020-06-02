import datetime
import json
import os
from pathlib import Path
import glob
import shutil
import sys
import threading
import traceback

import couchdb

from cli_code.crypt4gh.crypt4gh import lib, header
import cli_code.crypt4gh.crypt4gh.keys.c4gh as keys
from cli_code.crypt4gh.crypt4gh.keys.c4gh import MAGIC_WORD, parse_private_key

from cli_code.exceptions_ds import DeliveryOptionException, \
    DeliveryPortalException, CouchDBException, S3Error
from cli_code.s3_connector import S3Object
from cli_code.crypto_ds import secure_password_hash, gen_hmac
from cli_code.database_connector import DatabaseConnector


class DPUser():
    '''
    A Data Delivery Portal user.

    Args:
        username (str):   Delivery Portal username
        password (str):   Delivery Portal password

    Attributes:
        username (str): Delivery Portal username
        password (str): Delivery Portal password
        id (str):       User ID
        role (str):     Facility or researcher
    '''

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.id = None
        self.role = None


class DataDeliverer():
    '''
    Instanstiates the delivery by logging the user into the Delivery Portal,
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
        user (DPUser):          Data Delivery Portal user
        s3 (S3Object):          S3 connection object

    Raises:
        DeliveryPortalException:    Required info not found or access denied
        OSError:                    Temporary directory failure

    '''

    def __init__(self, config=None, username=None, password=None,
                 project_id=None, project_owner=None,
                 pathfile=None, data=None):
        # If none of username, password and config options are set
        # raise exception and quit execution -- dp cannot be accessed
        if all(x is None for x in [username, password, config]):
            raise DeliveryPortalException("Delivery Portal login credentials "
                                          "not specified. Enter: "
                                          "\n--username/-u AND --password/-pw,"
                                          " or --config/-c\n --owner/-o\n"
                                          "For help: 'dp_api --help'.")
        else:
            # put or get
            self.method = sys._getframe().f_back.f_code.co_name
            self.user = DPUser(username=username, password=password)
            self.project_id = project_id
            self.project_owner = project_owner
            self.data = None
            self.s3 = S3Object()

            self.check_user_input(config=config)

            dp_access_granted = self.check_dp_access()
            if dp_access_granted and self.user.id is not None:
                proj_access_granted, self.s3.project = \
                    self.check_project_access()
                if proj_access_granted and self.s3.project is not None:
                    # If no data to upload, cancel
                    if not data and not pathfile:
                        raise DeliveryPortalException(
                            "No data to be uploaded. Specify individual "
                            "files/folders using the --data/-d option one or "
                            "more times, or the --pathfile/-f. "
                            "For help: 'dp_api --help'"
                        )
                    else:
                        self.data = self.data_to_deliver(data=data,
                                                         pathfile=pathfile)
                else:
                    raise DeliveryPortalException(
                        f"Access to project {self.project_id} "
                        "denied. Delivery cancelled."
                    )
            else:
                raise DeliveryPortalException("Delivery Portal access denied! "
                                              "Delivery cancelled.")

            if self.data is not None:
                dirs_created, self.tempdir = self.create_directories()
                if not dirs_created:
                    raise OSError("Temporary directory could not be created. "
                                  "Unable to continue delivery. Aborting. ")

                self.s3.get_info(self.project_id)

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

        if config is not None:              # If config file entered
            user_config = Path(config).resolve()
            if user_config.is_file():      # and exist
                try:
                    with user_config.open(mode='r') as cf:
                        credentials = json.load(cf)
                except OSError as ose:
                    sys.exit(f"Could not open path-file {config}: {ose}")

                # Check that all credentials are entered and quit if not
                for c in ['username', 'password', 'project']:
                    if c not in credentials:
                        raise DeliveryOptionException(
                            f"The config file does not contain: '{c}'."
                        )

                self.user.username = credentials['username']
                self.user.password = credentials['password']
                self.project_id = credentials['project']
                if 'owner' in credentials:
                    self.project_owner = credentials['owner']
            else:
                raise OSError(f"Config file {config} does not exist. "
                              "Cancelling delivery.")

        else:
            if self.user.username is None or self.user.password is None:
                raise DeliveryOptionException(
                    "Delivery Portal login credentials not specified. "
                    "Enter --username/-u AND --password/-pw, or --config/-c."
                    "For help: 'dp_api --help'."
                )
            else:
                if self.project_id is None:
                    raise DeliveryOptionException(
                        "Project not specified. Enter project ID using "
                        "--project option or add to config file using "
                        "--config/-c option."
                    )

                # If no owner is set then assuming current user is owner
                if self.project_owner is None:
                    self.project_owner = self.user.username

        if self.project_owner is None and self.method == 'put':
            raise DeliveryOptionException("Project owner not specified. "
                                          "Cancelling delivery.")

    def check_dp_access(self):
        '''Checks the users access to the delivery portal

        Returns:
            tuple:  Granted access and user ID

                bool:   True if user login successful
                str:    User ID

        Raises:
            CouchDBException:           Database connection failure or
                                        user not found
            DeliveryPortalException:    Wrong password
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
                        raise DeliveryPortalException(
                            "Wrong password. Access to Delivery Portal "
                            "denied."
                        )
                    else:
                        # Check that facility putting or researcher getting
                        self.user.role = user_db[id_]['role']
                        if (self.user.role == 'facility'
                            and self.method == 'put') \
                           or (self.user.role == 'researcher'
                                and self.method == 'get'):
                            self.user.id = id_
                            if (self.user.role == 'researcher'
                                and self.method == 'get'
                                    and (self.project_owner is None or
                                         self.project_owner ==
                                         self.user.username)):
                                self.project_owner = self.user.id
                            return True
                        else:
                            raise DeliveryOptionException(
                                "Method error. Facilities can only use 'put' "
                                "and Researchers can only use 'get'."
                            )

            raise CouchDBException("Username not found in database. "
                                   "Access to Delivery Portal denied.")

    def check_project_access(self):
        '''Checks the users access to a specific project.

        Returns:
            tuple:  Project access and S3 project ID

                bool:   True if project access granted
                str:    S3 project to upload to/download from

        Raises:
            CouchDBException:           Database connection failure
                                        or missing project information
            DeliveryPortalException:    Access denied
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
                    f"The project {self.project_id} does not exist.")

            # If project exists, check if user has access to the project->quit
            if self.project_id not in user_projects:
                raise DeliveryPortalException(
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
                raise CouchDBException("An owner of the data has not been "
                                       "specified. Cannot guarantee data "
                                       "security. Cancelling delivery.")

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
                    raise CouchDBException("A delivery option has not been "
                                           "specified for this project.")

                # If delivery option exists, check if S3. If not -> quit
                if current_project['project_info']['delivery_option'] != "S3":
                    raise DeliveryOptionException(
                        "The specified project does not "
                        "have access to S3 delivery."
                    )

                # If S3 option specified, return S3 project ID
                try:
                    s3_project = user_db[self.user.id]['s3_project']['name']
                except DeliveryPortalException as dpe:
                    sys.exit("Could not get Safespring S3 project name from "
                             f"database: {dpe}. \nDelivery aborted.")
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

            if Path(d).exists():
                curr_path = Path(d).resolve()
                if curr_path.is_file():  # Save file info to dict
                    all_files[curr_path] = {"file": True,
                                            "directory": False,
                                            "path_base": None}
                elif curr_path.is_dir():  # Get info on files in folder
                    all_files.update({f: {"file": True,
                                          "directory": False,
                                          "path_base": curr_path.name} for f
                                      in curr_path.glob('**/*') if f.is_file()
                                      and "DS_Store" not in str(f)})
            else:
                if self.method == "put":
                    all_files[d] = False
                elif self.method == "get":
                    all_files[d] = {}
                else:
                    raise DeliveryOptionException(
                        "Delivery option {self.method} not allowed. "
                        "Cancelling delivery."
                    )

        return all_files

    def create_directories(self):
        '''Creates all temporary directories.

        Returns:
            tuple:  Directories created and all paths

                bool:   True if directories created
                tuple:  All created directories

        Raises:
            IOError:    Temporary folder failure
        '''

        # Create temporary folder with timestamp and all subfolders
        timestamp_ = timestamp()
        temp_dir = Path.cwd() / Path(f"DataDelivery_{timestamp_}")
        dirs = tuple(temp_dir / Path(sf)
                     for sf in ["", "files/", "keys/", "meta/", "logs/"])
        for d_ in dirs:
            try:
                d_.mkdir(parents=True)
            except IOError as ose:
                print(f"The directory '{d_}' could not be created: {ose}"
                      "Cancelling delivery. ")

                if temp_dir.exists() and not isinstance(ose, FileExistsError):
                    print("Deleting temporary directory.")
                    try:
                        # Remove all prev created folders
                        shutil.rmtree(temp_dir)
                        sys.exit(f"Temporary directory deleted. \n\n"
                                 "----DELIVERY CANCELLED---\n")  # and quit
                    except IOError as ose:
                        sys.exit(f"Could not delete directory {temp_dir}: "
                                 f"{ose}\n\n ----DELIVERY CANCELLED---\n")

                        return False, ()

                else:
                    pass  # create log file here

        return True, dirs

    def get_bucket_path(self, file: Path, path_base: str = None):
        """Gets the path to the file, from the entered folder. """

        filename = file.name    # name + suffixes
        suff = "".join(file.suffixes)   # suffixes
        stem = filename.split(suff)[0]  # name only

        if path_base is not None:
            fileparts = file.parts
            start_ind = fileparts.index(path_base)
            return Path(*fileparts[start_ind:-1])
        else:
            return Path("")

    def get_recipient_key(self, keytype="public"):
        """Retrieves the recipient public key from the database."""

        with DatabaseConnector() as dbconnection:
            # try:
            #     dbconnection = self.couch_connect()
            # except CouchDBException as cdbe:
            #     sys.exit(f"Could not connect to the database: {cdbe}")
            # else:
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
                    raise CouchDBException(f"Could not find any projects for "
                                           "the user {self.project_owner}.")

                if keytype not in project_db[self.project_id]['project_keys']:
                    raise CouchDBException(
                        f"There is no public key recorded for "
                        "user {self.project_owner} and "
                        "project {self.project_id}."
                    )

                return bytes.fromhex(project_db[self.project_id]['project_keys'][keytype])

    def put(self, file: str, spec_path: str, orig_file: str) -> (str):
        '''Uploads specified data to the S3 bucket.

        Args:
            file:       File to be uploaded
            spec_path:  Root folder path to file
        '''

        filepath = str(spec_path / Path(file.name))

        # check if bucket exists
        if self.s3.bucket in self.s3.resource.buckets.all():
            # Check if file exists (including path)
            file_already_in_bucket = \
                self.s3.file_exists_in_bucket(key=filepath)
            # Upload if doesn't exist
            if file_already_in_bucket:
                return orig_file, file, False, filepath, "exists"
            else:
                try:
                    self.s3.resource.meta.client.upload_file(
                        str(file), self.s3.bucket.name,
                        filepath
                    )
                except Exception as e:
                    return orig_file, file, False, e
                else:
                    return orig_file, file, True, filepath
        else:
            return orig_file, file, False, "Bucket not found in S3 resource"

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


def finish_download(file, recipient_sec, sender_pub):
    '''Finishes file download, including decryption and
    checksum generation'''

    if isinstance(file, Path):
        try:
            dec_file = Path(str(file).split(
                file.name)[0]) / Path(file.stem)
        except Exception:
            sys.exit("FEL")
        finally:
            original_umask = os.umask(0)
            with file.open(mode='rb') as infile:
                with dec_file.open(mode='ab+') as outfile:
                    lib.decrypt(keys=[(0, recipient_sec, sender_pub)],
                                infile=infile,
                                outfile=outfile)

    # _, checksum = gen_hmac(file=dec_file)
    # _, checksum_orig = gen_hmac(file=Path(
    #     "/Users/inaod568/repos/Data-Delivery-Portal/files/testfolder/testfile_05.fna"))

    # print(checksum)
    # print(checksum_orig)
    # print(
    #     f"Decryption successful - original and decrypted file identical: {checksum==checksum_orig}")

    return file


def timestamp() -> (str):
    '''Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    '''

    now = datetime.datetime.now()
    timestamp = ""

    for t in (now.year, "-", now.month, "-", now.day, " ",
              now.hour, ":", now.minute, ":", now.second):
        if len(str(t)) == 1 and isinstance(t, int):
            timestamp += f"0{t}"
        else:
            timestamp += f"{t}"

    return timestamp.replace(" ", "_").replace(":", "-")


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
