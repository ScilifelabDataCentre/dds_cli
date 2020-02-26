from code_api.dp_exceptions import *
from code_api.datadel_s3 import S3Object
from code_api.dp_crypto import secure_password_hash

import sys
import os
import json
import shutil
import datetime

import traceback
import concurrent

import couchdb


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
        config (str):           Path to file containing user credentials and project info
        username (str):         User specified username, None if config entered
        password (str):         User specified password, None if config entered
        project_id (str):       User specified project ID, None if config entered
        project_owner (str):    User specified project owner, None if config entered
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
                 project_id=None, project_owner=None, pathfile=None, data=None):

        # If none of username, password and config options are set
        # raise exception and quit execution -- dp cannot be accessed
        if all(x is None for x in [username, password, config]):
            raise DeliveryPortalException("Delivery Portal login credentials "
                                          "not specified. Enter: \n --username/-u "
                                          "AND --password/-pw, or --config/-c\n "
                                          "--owner/-o\n"
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
                proj_access_granted, self.s3.project = self.check_project_access()
                if proj_access_granted and self.s3.project is not None:
                    # If no data to upload, cancel
                    if not data and not pathfile:
                        raise DeliveryPortalException(
                            "No data to be uploaded. Specify individual files/folders using "
                            "the --data/-d option one or more times, or the --pathfile/-f. "
                            "For help: 'dp_api --help'"
                        )
                    else:
                        self.data = self.data_to_deliver(data=data,
                                                         pathfile=pathfile)
                else:
                    raise DeliveryPortalException(f"Access to project {self.project_id} "
                                                  "denied. Delivery cancelled.")
            else:
                raise DeliveryPortalException("Delivery Portal access denied! "
                                              "Delivery cancelled.")

            if self.data is not None:
                dirs_created, self.tempdir = self.create_directories()
                if not dirs_created:
                    raise OSError(
                        "Temporary directory could not be created. Unable to continue delivery. Aborting. ")

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

        return True

    def couch_connect(self):
        '''Connects to a couchdb interface. Currently hard-coded.

        Returns:
            couchdb.client.Server:  CouchDB server instance.
            '''

        try:
            couch = couchdb.Server('http://delport:delport@localhost:5984/')
        except CouchDBException as cdbe:
            sys.exit(f"Database login failed. {cdbe}")
        else:
            return couch

    def check_user_input(self, config):
        '''Checks that the correct options and credentials are entered.

        Args:
            config:     File containing the users DP username and password,
                        and the project relating to the upload/download.
                        Can be used instead of inputing the credentials separately.

        Raises:
            OSError:                    Config file not found or opened
            DeliveryOptionException:    Required information not found
        '''

        if config is not None:              # If config file entered
            if os.path.exists(config):      # and exist
                try:
                    with open(config, 'r') as cf:
                        credentials = json.load(cf)
                except OSError as ose:
                    sys.exit(f"Could not open path-file {config}: {ose}")

                # Check that all credentials are entered and quit if not
                for c in ['username', 'password', 'project']:
                    if c not in credentials:
                        raise DeliveryOptionException("The config file does not "
                                                      f"contain: '{c}'.")

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
                raise DeliveryOptionException("Delivery Portal login credentials "
                                              "not specified. Enter --username/-u "
                                              "AND --password/-pw, or --config/-c."
                                              "For help: 'dp_api --help'.")
            else:
                if self.project_id is None:
                    raise DeliveryOptionException("Project not specified. Enter "
                                                  "project ID using --project option "
                                                  "or add to config file using --config/-c"
                                                  "option.")

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

        try:
            user_db = self.couch_connect()['user_db']
        except CouchDBException as cdbe:
            sys.exit(f"Could not collect database 'user_db'. {cdbe}")
        else:   
            # Search the database for the user
            for id_ in user_db:
                # If found, create secure password hash and compare to correct password
                if self.user.username == user_db[id_]['username']:
                    password_settings = user_db[id_]['password']['settings']
                    password_hash = secure_password_hash(password_settings=password_settings,
                                                         password_entered=self.user.password)
                    if user_db[id_]['password']['hash'] != password_hash:
                        raise DeliveryPortalException("Wrong password. "
                                                      "Access to Delivery Portal denied.")
                    else:
                        # Check that facility is uploading or researcher downloading
                        self.user.role = user_db[id_]['role']
                        if (self.user.role == 'facility' and self.method == 'put') or \
                                (self.user.role == 'researcher' and self.method == 'get'):
                            self.user.id = id_
                            if (self.user.role == 'researcher' and self.method == 'get' and self.project_owner is None):
                                self.project_owner = self.user.id
                            return True
            
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

        try:
            couch = self.couch_connect()  # Connect to database
        except CouchDBException as cdbe:
            sys.exit(f"Could not connect to CouchDB: {cdbe}")
        else:
            user_db = couch['user_db']
            # Get the projects registered to the user
            user_projects = user_db[self.user.id]['projects']
            # Check if project exists in project database
            if self.project_id not in couch['project_db']:
                raise CouchDBException(
                    f"The project {self.project_id} does not exist.")
            else:
                # If user does not have access to the project, quit
                if self.project_id not in user_projects:
                    raise DeliveryPortalException("You do not have access to the specified project "
                                                  f"{self.project_id}. Aborting delivery.")
                else:
                    current_project = couch['project_db'][self.project_id]
                    # Get project information if it exists
                    if 'project_info' not in current_project:
                        raise CouchDBException("There is no 'project_info' recorded "
                                               "for the specified project. Aborting delivery.")
                    else:
                        # Find owner of project and check if specified owner matches
                        if 'owner' not in current_project['project_info']:
                            raise CouchDBException("An owner of the data has not been "
                                                   "specified. Cannot guarantee data "
                                                   "security. Cancelling delivery.")
                        else:
                            correct_owner = current_project['project_info']['owner']
                            # If facility specified correct user or researcher is owner
                            if (self.method == 'put' and correct_owner == self.project_owner != self.user.id) or \
                                    (self.method == 'get' and correct_owner == self.project_owner == self.user.id):
                                if 'delivery_option' not in current_project['project_info']:
                                    raise CouchDBException("A delivery option has not been "
                                                           "specified for this project.")
                                else:
                                    if current_project['project_info']['delivery_option'] != "S3":
                                        raise DeliveryOptionException("The specified project does not "
                                                                      "have access to S3 delivery.")
                                    else:
                                        try:
                                            s3_project = user_db[self.user.id]['s3_project']['name']
                                        except DeliveryPortalException as dpe:
                                            sys.exit("Could not get Safespring S3 project name from database."
                                                     f"{dpe}. \nDelivery aborted.")
                                        else:
                                            return True, s3_project
                            else:
                                raise DeliveryOptionException("Incorrect data owner! You do not "
                                                              "have access to this project. "
                                                              "Cancelling delivery.")

    def data_to_deliver(self, data: tuple, pathfile: str) -> (list):
        '''Puts all entered paths into one list

        Args:
            data:       Tuple containing paths
            pathfile:   Path to file containing paths

        Returns:
            list:   List of all paths entered in data and pathfile option

        Raises:
            IOError:                    Pathfile not found
            DeliveryOptionException:    Multiple identical files
        '''

        all_files = list()

        # If --data option --> put all files in list
        if data is not None:
            if self.method == "put":
                all_files = [os.path.abspath(d) if os.path.exists(d)
                             else [None, d] for d in data]
            elif self.method == "get":
                all_files = [d for d in data]
            else:
                pass    # raise an error here

        # If --pathfile option --> put all files in list
        if pathfile is not None:
            pathfile_abs = os.path.abspath(pathfile)
            # Precaution, already checked in click.option
            if os.path.exists(pathfile_abs):
                with open(pathfile_abs, 'r') as file:  # Read lines, strip \n and put in list
                    if self.method == "put":
                        all_files += [os.path.abspath(line.strip()) if os.path.exists(line.strip())
                                      else [None, line.strip()] for line in file]
                    elif self.method == "get":
                        all_files += [line.strip() for line in file]
                    else:
                        pass    # raise an error here
            else:
                raise IOError(
                    f"--pathfile option {pathfile} does not exist. Cancelling delivery.")

        # Check for file duplicates
        for element in all_files:
            if all_files.count(element) != 1:
                raise DeliveryOptionException(f"The path to file {element} is listed multiple times, "
                                              "please remove path dublicates.")

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
        timestamp_ = self.timestamp()
        temp_dir = f"{os.getcwd()}/DataDelivery_{timestamp_}"
        dirs = tuple(
            f"{temp_dir}/{sf}" for sf in ["", "files/", "keys/", "meta/", "logs/"])

        for d_ in dirs:
            try:
                os.mkdir(d_)
            except IOError as ose:
                sys.exit(f"The directory '{d_}' could not be created: {ose}"
                         "Cancelling delivery. Deleting temporary directory.")

                if os.path.exists(temp_dir):
                    try:
                        # Remove all prev created folders
                        shutil.rmtree(temp_dir)
                        sys.exit(f"Temporary directory deleted. \n\n"
                                 "----DELIVERY CANCELLED---\n")  # and quit
                    except IOError as ose:
                        sys.exit(f"Could not delete directory {temp_dir}: {ose}\n\n "
                                 "----DELIVERY CANCELLED---\n")

                        return False, ()

                else:
                    pass  # create log file here
                    # logging.basicConfig(filename=f"{temp_dir}/logs/data-delivery.log",
                    #         level=logging.DEBUG)

        return True, dirs

    def timestamp(self) -> (str):
        '''Gets the current time. Formats timestamp.

        Returns:
            str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

        '''

        now = datetime.datetime.now()
        timestamp = ""
        sep = ""

        for t in (now.year, "-", now.month, "-", now.day, " ",
                  now.hour, ":", now.minute, ":", now.second):
            if len(str(t)) == 1 and isinstance(t, int):
                timestamp += f"0{t}"
            else:
                timestamp += f"{t}"

        return timestamp.replace(" ", "_").replace(":", "-")

    def put(self):
        '''Uploads specified data to the S3 bucket.


        '''

        # Create multithreading pool
        with concurrent.futures.ThreadPoolExecutor() as executor:
            upload_threads = []
            for path in self.data:
                if type(path) == str:
                    # check if folder and then get all subfolders
                    if os.path.isdir(path):
                        all_dirs = [x[0]
                                    for x in os.walk(path)]  # all (sub)dirs
                        for dir_ in all_dirs:
                            # check which files are in the directory
                            all_files = [os.path.join(dir_, f) for f in os.listdir(dir_)
                                         if os.path.isfile(os.path.join(dir_, f))]
                            # Upload all files
                            for file in all_files:
                                future = executor.submit(
                                    self.s3.upload, file, path)
                                upload_threads.append(future)
                    elif os.path.isfile(path):
                        # Upload file
                        future = executor.submit(self.s3.upload, path, None)
                        upload_threads.append(future)
                    else:
                        sys.exit(f"Path type {path} not identified."
                                 "Have you entered the correct path?")

            for f in concurrent.futures.as_completed(upload_threads):
                print(f.result())

    def get(self):
        '''Downloads specified data from S3 bucket

        '''

        print(self.project_owner)
