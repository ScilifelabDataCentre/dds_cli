"""CLI for the Data Delivery System.

The CLI begins with checking if the user has access - both if the user exists
in the database, and if the current delivery is being performed by the correct
role: Facilities can only use put (upload), while other users can only use get
(download). The user credentials (independent of role) can either be specified
within a json file (--creds option) or by using the --username, --password, etc
options. Whether the file or loose options are used or not, the same user
information is required:

    * Username
    * Password
    * Project ID
    * Project owner (only required for Facilities)

    Example of --creds option json file:
        {
            "username": <username>,\n
            "password": <password>,\n
            "project": <project_id>,\n
            "owner": <owner_id>
        }

All files are checked for duplicates and later compressed (if not
already so) to save space. Directories can be specified in the delivery and
the system keeps the original directory structure, but the system always
handles and processes the files within. This is to enable individual files to
be delivered. All files, independent of previous encryption, are encrypted by
the Data Delivery System.
"""

# TODO(ina): Add example to module docstring?
# TODO(ina): Fix or ignore pylint "too-many-arguments" warnings etc

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import concurrent.futures
import logging
import logging.config
import sys

# Installed
import click
import requests

# Own modules
import cli_code
from cli_code import data_deliverer as dd
from cli_code import ENDPOINTS
from cli_code import exceptions_ds
from cli_code import file_handler


###############################################################################
# SETUP ############################################################### SETUP #
###############################################################################

# Initiate logging variables
LOG = None
CLI_LOGGER = None


###############################################################################
# MAIN ################################################################# MAIN #
###############################################################################


@click.group()
def cli():
    """Data Delivery System CLI.

    Initiates the required delivery objects: A temporary directory where logs
    and files will be stored, and the CLI logger. Cannot be used
    independently - put or get must be specified as an argument.
    """

    created = cli_code.create_directories()
    if not created:
        raise OSError("Temporary directory could not be created. "
                      "Unable to continue delivery. Aborting. ")

    global LOG
    LOG = cli_code.config_logger(filename=cli_code.LOG_FILE)

    global CLI_LOGGER
    CLI_LOGGER = logging.getLogger(__name__)
    CLI_LOGGER.setLevel(logging.WARNING)


###############################################################################
# PUT ################################################################### PUT #
###############################################################################


@cli.command()
@click.option("--creds", "-c", required=False, type=click.Path(exists=True),
              help=("Path to file containing user credentials - username, "
                    "password, project id, project owner."))
@click.option("--username", "-u", required=False, type=str,
              help="Your Data Delivery System username.")
@click.option("--project", "-p", required=False, type=str,
              help="Project ID to which the delivery belongs to.")
@click.option("--owner", "-o", required=False, type=str, multiple=False,
              show_default=True,
              help="Owner ID - the user to whom you are delivering.")
@click.option("--pathfile", "-f", required=False, type=click.Path(exists=True),
              multiple=False, help=("Path to file containing all files and "
                                    "folders to be delivered."))
@click.option("--source", "-s", required=False, type=click.Path(exists=True),
              multiple=True, help="Path to file or folder to be delivered.")
@click.option("--break-on-fail", is_flag=True, default=False,
              show_default=True, help=("Failure to deliver one file results in"
                                       " cancellation of all specified files."))
@click.option("--overwrite", is_flag=True, default=False, show_default=True,
              help=("Replace any previously delivered files specified in the "
                    "current delivery."))
def put(creds: str, username: str, project: str,
        owner: str, pathfile: str, source: tuple, break_on_fail=True,
        overwrite=False) -> (str):
    """Handles the upload of files to the project-specific S3 bucket.

    Currently only usable by facilities.
    """
    #testing to close issue
    # TODO(ina): Add example in docstring

    # Instantiate DataDeliverer
    # - checks access and gets neccessary delivery info
    with dd.DataDeliverer(creds=creds, username=username,
                          project_id=project, project_owner=owner,
                          pathfile=pathfile, data=source,
                          break_on_fail=break_on_fail, overwrite=overwrite) \
            as delivery:

        # print(delivery.data)
        sys.exit()
        # POOLEXECUTORS STARTED ####################### POOLEXECUTORS STARTED #
        pool_executor = concurrent.futures.ProcessPoolExecutor()   # Processing
        thread_executor = concurrent.futures.ThreadPoolExecutor()  # IO related

        # Futures -- Pools and threads
        pools = {}          # Processing e.g. compression, encryption etc
        threads = {}        # Upload to S3
        final_threads = {}  # Delete files

        # count = 0     # For testing if failing works
        # BEGINS DELIVERY # # # # # # # # # # # # # # # # # # BEGINS DELIVERY #
        for path, info in delivery.data.items():
            # Quits and moves on if DS noted cancelation for file
            if not info["proceed"]:
                CLI_LOGGER.warning("CANCELLED: '%s'", path)
                dd.update_progress_bar(file=path, status="e")  # -> X-symbol
                continue

            # Displays progress = "Encrypting..."
            dd.update_progress_bar(file=path, status="enc")

            # Starts file processing - compression and encryption
            pools[
                pool_executor.submit(delivery.prep_upload,
                                     path=path,
                                     path_info=delivery.data[path])
            ] = path

        # Get results from processing when each pool is finished
        for pfuture in concurrent.futures.as_completed(pools):
            ppath = pools[pfuture]      # Original file path
            try:
                # Gets information from processing:
                # processed - processing successful, efile - encrypted file,
                # esize - size of efile, ds_compressed - compressed by
                # delivery system or not, key - encryption public key,
                # salt - salt used for key generation, error - error message
                processed, efile, esize, \
                    ds_compressed, key, salt, error = pfuture.result()
            except concurrent.futures.BrokenExecutor:
                sys.exit(f"{pfuture.exception()}")
                break  # Precaution if sys.exit not quit completely

            # count += 1
            # if count == 3:
            #     processed = False
            #     error = "Test error message. Something went wrong."
            # Updates file info
            proceed = delivery.update_delivery(
                file=ppath,
                updinfo={"proceed": processed,
                         "encrypted_file": efile,
                         "encrypted_size": esize,
                         "ds_compressed": ds_compressed,
                         "error": error,
                         "key": key,
                         "salt": salt}
            )

            # Sets processing as finished
            delivery.set_progress(item=ppath, processing=True, finished=True)

            # Quits and moves on if DS noted cancelation for file
            if not proceed:
                CLI_LOGGER.warning("CANCELLED: '%s'", ppath)
                dd.update_progress_bar(file=ppath, status="e")  # -> X-symbol
                continue

            # Displays progress = "Uploading..."
            dd.update_progress_bar(file=ppath, status="u")

            # Starts upload
            threads[
                thread_executor.submit(delivery.put,
                                       file=ppath,
                                       fileinfo=delivery.data[ppath])
            ] = ppath

        # FINISH DELIVERY # # # # # # # # # # # # # # # # # # FINISH DELIVERY #
        for ufuture in concurrent.futures.as_completed(threads):
            upath = threads[ufuture]       # Original file path
            try:
                # Gets information from upload:
                # uploaded - if upload successful or not, error - error message
                uploaded, error = ufuture.result()
            except concurrent.futures.BrokenExecutor:
                sys.exit(f"{ufuture.exception()}")
                break  # Precaution if sys.exit not quit completely

            # Updates file info
            proceed = delivery.update_delivery(file=upath,
                                               updinfo={"proceed": uploaded,
                                                        "error": error})

            # Sets upload as finished
            delivery.set_progress(item=upath, upload=True, finished=True)

            # Quits and moves on if DS noted cancelation for file
            if not proceed:
                CLI_LOGGER.warning("CANCELLED: '%s'", upath)
                dd.update_progress_bar(file=upath, status="e")  # -> X-symbol
                continue

            CLI_LOGGER.info("UPLOAD COMPLETED: '%s' -> '%s'",
                            upath, delivery.data[upath]["path_in_bucket"])

            # Set db update as in progress
            delivery.set_progress(item=upath, db=True, started=True)

            # TODO(ina): Put db update request in function - threaded?
            # Adds (or updates if --overwrite) file information to database
            # Args to send in request to api
            req_args = {
                "project": delivery.project_id,
                "file": delivery.data[upath]["path_in_db"],
                "directory_path": delivery.data[upath]["directory_path"],
                "size": delivery.data[upath]["size"],
                "size_enc": delivery.data[upath]["encrypted_size"],
                "ds_compressed": delivery.data[upath]["ds_compressed"],
                "extension": delivery.data[upath]["extension"],
                "key": delivery.data[upath]["key"],
                "salt": delivery.data[upath]["salt"],
                "overwrite": delivery.overwrite,
                "token": delivery.token
            }

            # Perform request to DatabaseUpdate - update file and project info
            req = ENDPOINTS["update_file"]
            try:
                response = requests.post(req, params=req_args)
            except requests.exceptions.ConnectionError:
                sys.exit(
                    exceptions_ds.printout_error(
                        "Failed to establish connection to the Data Delivery "
                        "System. The service is down. \n"
                        "Contact the SciLifeLab Data Centre."
                    )
                )

            # TODO (ina): If this or database update failed - save info to log
            # what info? facility should not have private key access
            if not response.ok:
                sys.exit(
                    exceptions_ds.printout_error(
                        f"Could not update database. {response.text}"
                    )
                )

            # Get response from api
            db_response = response.json()
            # db_response - "updated"=True if database update successful
            if not db_response["access_granted"] or not db_response["updated"]:
                emessage = f"Database update failed: {db_response['message']}"
                CLI_LOGGER.warning(emessage)
                dd.update_progress_bar(file=upath, status="e")
                _ = delivery.update_delivery(file=upath,
                                             updinfo={"proceed": False,
                                                      "error": emessage})
                # TODO (ina): Info to save if failed after processing:
                dd.save_failed(file=upath, file_info=req_args)
                continue

            CLI_LOGGER.info("File added to database: '%s'", upath)

            # Sets delivery as finished and display progress = check mark
            delivery.set_progress(item=upath, db=True, finished=True)
            dd.update_progress_bar(file=upath.name, status="f")
            encrypted_file = delivery.data[upath]["encrypted_file"]

            # Deletes encrypted files as soon as success
            final_threads[
                thread_executor.submit(file_handler.file_deleter,
                                       file=encrypted_file)
            ] = (upath, encrypted_file)

        # Check if deletion successful
        for dfuture in concurrent.futures.as_completed(final_threads):
            # Path to original (origpath) and encrypted (cryptpath) file
            origpath, cryptpath = final_threads[dfuture]
            try:
                # Get information from thread:
                # deleted - if file deletion was successful
                deleted, _ = dfuture.result()
            except concurrent.futures.BrokenExecutor:
                CLI_LOGGER.critical("%s", dfuture.exception())
                continue

            if deleted:
                CLI_LOGGER.info("File deleted: '%s' ('%s')",
                                cryptpath, origpath)
            else:
                CLI_LOGGER.warning("Failed to delete file: '%s' ('%s')",
                                   cryptpath, origpath)

        # DELIVERY FINISHED ------------------------------- DELIVERY FINISHED #

        # STOPPING POOLEXECUTORS ##################### STOPPING POOLEXECUTORS #
        pool_executor.shutdown(wait=True)
        thread_executor.shutdown(wait=True)
        sys.stdout.write("\n")

###############################################################################
# GET ################################################################### GET #
###############################################################################


@cli.command()
@click.option("--creds", "-c", required=False, type=click.Path(exists=True),
              help=("Path to file containing user credentials - username, "
                    "password, project id, project owner."))
@click.option("--username", "-u", required=False, type=str,
              help="Your Data Delivery System username.")
@click.option("--project", "-p", required=False, type=str,
              help="Project ID to which the delivery belongs to.")
@click.option("--pathfile", "-f", required=False, type=click.Path(exists=True),
              multiple=False, help=("Path to file containing all files and "
                                    "folders to be delivered."))
@click.option("--source", "-s", required=False, type=str,
              multiple=True, help="Path to file or folder to be delivered.")
@click.option("--break-on-fail", is_flag=True, default=False,
              show_default=True, help=("Failure to deliver one file results in"
                                       " cancellation of all specified files."))
def get(creds: str, username: str, project: str,
        pathfile: str, source: tuple, break_on_fail: bool = True):
    """Handles the download of files from the project-specific S3 bucket.

    Currently not usable by facilities.
    """

    # TODO(ina): Add example to docstring

    # Instantiate DataDeliverer
    # - checks access and gets neccessary delivery info
    with dd.DataDeliverer(creds=creds, username=username,
                          project_id=project, pathfile=pathfile, data=source,
                          break_on_fail=break_on_fail) \
            as delivery:

        # POOLEXECUTORS STARTED ####################### POOLEXECUTORS STARTED #
        pool_executor = concurrent.futures.ProcessPoolExecutor()   # Processing
        thread_executor = concurrent.futures.ThreadPoolExecutor()  # IO related

        # Futures -- Pools and threads
        pools = {}          # Finalizing e.g. decompression, decryption etc
        threads = {}        # Download from S3

        # count = 0
        # BEGINS DELIVERY # # # # # # # # # # # # # # # # # # BEGINS DELIVERY #
        for path, info in delivery.data.items():

            # Quits and moves on if DS noted cancelation for file
            if not info["proceed"]:
                CLI_LOGGER.warning("Cancelled: '%s'", path)
                dd.update_progress_bar(file=path, status="e")  # -> X
                continue

            # Displays progress = "Downloading..."
            dd.update_progress_bar(file=path, status="d")

            # Starts download from S3
            threads[
                thread_executor.submit(delivery.get, path=path, path_info=info)
            ] = path

        # Get results from download when each thread is finished
        for dfuture in concurrent.futures.as_completed(threads):
            dpath = threads[dfuture]  # Original file path
            try:
                # Gets information from download:
                # downloaded - if download successful or not,
                # error - error message
                downloaded, error = dfuture.result()
            except concurrent.futures.BrokenExecutor:
                sys.exit(f"{dfuture.exception()}")
                break   # Precaution if sys.exit not quit completely

            # count += 1
            # if count == 1:
            #     downloaded = False
            #     error = "Test error message. Something went wrong."
            # Updates file info
            proceed = delivery.update_delivery(file=dpath,
                                               updinfo={"proceed": downloaded,
                                                        "error": error})

            # Sets file upload as finished
            delivery.set_progress(item=dpath, download=True, finished=True)

            # Quits and moves on if DS noted cancelation for file
            if not proceed:
                CLI_LOGGER.warning("Cancelled: '%s'", dpath)
                dd.update_progress_bar(file=dpath, status="e")  # -> X
                continue

            CLI_LOGGER.info("DOWNLOAD COMPLETED: '%s' -> '%s'",
                            dpath, delivery.data[dpath]["path_in_temp"])

            # Displays progress = "Decrypting..."
            dd.update_progress_bar(file=dpath, status="dec")

            # Starts file finalizing -- decompression, decryption, etc.
            pools[
                pool_executor.submit(delivery.finalize_delivery,
                                     file=dpath,
                                     fileinfo=delivery.data[dpath])
            ] = dpath

        # FINISH DELIVERY # # # # # # # # # # # # # # # # # # FINISH DELIVERY #
        for ffuture in concurrent.futures.as_completed(pools):
            fpath = pools[ffuture]  # Original file path
            try:
                # Gets information from finalizing:
                # decrypted - if decryption successful or not,
                # decrypted_file - path to decrypted file,
                # error - error message
                decrypted, decrypted_file, error = ffuture.result()
            except concurrent.futures.BrokenExecutor:
                sys.exit(f"{ffuture.exception()}")
                break  # Precaution if sys.exit not quit completely

            # Updates file info
            proceed = delivery.update_delivery(
                file=fpath,
                updinfo={"proceed": decrypted,
                         "decrypted_file": decrypted_file,
                         "error": error}
            )

            # Sets file finalizing as finished
            delivery.set_progress(item=fpath,
                                  decryption=True,
                                  finished=True)

            # Quits and moves on if DS noted cancelation for file
            if not proceed:
                CLI_LOGGER.warning("File: '%s' -- cancelled "
                                   "-- moving on to next file", fpath)
                dd.update_progress_bar(file=fpath, status="e")  # -> X

                args = {
                    "project": delivery.project_id,
                    "file": delivery.data[fpath]["path_in_bucket"],
                    "directory_path": delivery.data[fpath]["directory_path"],
                    "size": delivery.data[fpath]["size"],
                    "size_enc": delivery.data[fpath]["size_enc"],
                    "ds_compressed": delivery.data[fpath]["compressed"],
                    "extension": delivery.data[fpath]["extension"],
                    "key": delivery.data[fpath]["public_key"],
                    "salt": delivery.data[fpath]["salt"]
                }
                dd.save_failed(file=delivery.data[fpath]["path_in_temp"],
                               file_info=args)
                continue

            # TODO(ina): Put db update request in function - threaded?
            # Updates file information in database
            # Args to send in request to api
            delivery.set_progress(item=fpath, db=True, started=True)

            # Perform request to DeliveryDate -- update delivery date
            req = ENDPOINTS["delivery_date"]
            args = {"file_id": delivery.data[fpath]["id"],
                    "project": delivery.project_id,
                    "token": delivery.token}
            try:
                response = requests.post(req, params=args)
            except requests.exceptions.ConnectionError:
                sys.exit(
                    exceptions_ds.printout_error(
                        "Failed to establish connection to the Data Delivery "
                        "System. The service is down. \n"
                        "Contact the SciLifeLab Data Centre."
                    )
                )

            #
            if not response.ok:
                emessage = f"{response.status_code} - {response.reason}:" + \
                    f"\n{req}\n{response.text}"
                _ = delivery.update_delivery(
                    file=fpath,
                    updinfo={"proceed": False, "error": emessage}
                )
                dd.update_progress_bar(file=fpath, status="e")  # -> X-symbol
                CLI_LOGGER.warning(emessage)
            else:
                json_resp = response.json()
                if not json_resp["access_granted"] or not json_resp["updated"]:
                    emessage = json_resp["message"]
                    _ = delivery.update_delivery(
                        file=fpath,
                        updinfo={"proceed": False, "error": emessage}
                    )
                    dd.update_progress_bar(file=fpath, status="e")  # -> X
                else:
                    CLI_LOGGER.info("File updated in db: '%s'", fpath)

                    # Sets delivery as finished and display progress = check
                    delivery.set_progress(item=fpath, db=True, finished=True)
                    dd.update_progress_bar(file=fpath, status="f")

        # DELIVERY FINISHED ------------------------------- DELIVERY FINISHED #

        # STOPPING POOLEXECUTORS ##################### STOPPING POOLEXECUTORS #
        pool_executor.shutdown(wait=True)
        thread_executor.shutdown(wait=True)
        sys.stdout.write("\n")

###############################################################################
# LIST  ################################################################ LIST #
###############################################################################

# TODO (ina): list function

###############################################################################
# DELETE ############################################################# DELETE #
###############################################################################

# TODO (ina): delete function
