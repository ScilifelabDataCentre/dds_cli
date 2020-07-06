"""
Command line interface for Data Delivery System
"""

# IMPORTS ########################################################### IMPORTS #

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, \
    as_completed
import logging
import logging.config
from pathlib import Path
import sys
import os
import itertools

import click
from cli_code.crypt4gh.crypt4gh import lib, header, keys

from cli_code import LOG_FILE, timestamp
from cli_code.data_deliverer import DataDeliverer, finish_download
from cli_code.crypto_ds import Crypt4GHKey
from cli_code.database_connector import DatabaseConnector
from cli_code.exceptions_ds import DataException
import cli_code.file_handler as fh
from cli_code.s3_connector import S3Connector

# CONFIG ############################################################# CONFIG #

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def config_logger(logfile: str):
    '''Creates log file '''

    return fh.config_logger(logger=LOG, filename=logfile,
                            file=True, file_setlevel=logging.DEBUG,
                            fh_format="%(asctime)s::%(levelname)s::" +
                            "%(name)s::%(lineno)d::%(message)s",
                            stream=True, stream_setlevel=logging.WARNING,
                            sh_format="%(levelname)s::%(name)s::" +
                            "%(lineno)d::%(message)s")


# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #


COMPRESSED_FORMATS = dict()

# MAIN ################################################################# MAIN #


@click.group()
def cli():
    global COMPRESSED_FORMATS


@cli.command()
@click.option('--config', '-c',
              required=False,
              type=click.Path(exists=True),
              help="Path to config file containing e.g. username, password, "
                   "project id, etc.")
@click.option('--username', '-u',
              required=False,
              type=str,
              help="Delivery Portal username.")
@click.option('--password', '-pw',
              required=False,
              type=str,
              help="Delivery Portal password.")
@click.option('--project', '-p',
              required=False,
              type=str,
              help="Project to upload files to.")
@click.option('--owner', '-o',
              required=True,
              type=str,
              multiple=False,
              default="",
              help="The owner of the data.")
@click.option('--pathfile', '-f',
              required=False,
              type=click.Path(exists=True),
              multiple=False,
              help="Path to file containing all files and "
                   "folders to be uploaded.")
@click.option('--data', '-d',
              required=False,
              type=click.Path(exists=True),
              multiple=True,
              help="Path to file or folder to upload.")
@click.option('--break-on-fail', is_flag=True)
def put(config: str, username: str, password: str, project: str,
        owner: str, pathfile: str, data: tuple, break_on_fail) -> (str):
    """Uploads the files to S3 bucket. Only usable by facilities. """

    # Create DataDeliverer to handle files and folders
    with DataDeliverer(config=config, username=username, password=password,
                       project_id=project, project_owner=owner,
                       pathfile=pathfile, data=data, break_on_fail=True) \
            as delivery:

        # Setup logging
        CLI_LOGGER = config_logger(LOG_FILE)

        # Pools and threads
        pools = {}
        cthreads = {}
        uthreads = {}

        # POOLEXECUTORS ####################################### POOLEXECUTORS #
        pool_executor = ProcessPoolExecutor()
        thread_executor = ThreadPoolExecutor()

        # Iterate through data
        for path, info in delivery.data.items():
            CLI_LOGGER.debug(f"{path}: {info}\n")  # Print out before

            if not info['proceed']:
                CLI_LOGGER.warning(f"File: {ppath} -- moving on to next file")
                continue

            cthreads[
                thread_executor.submit(delivery._do_file_checks,
                                       file=path,
                                       fileinfo=info)
            ] = path

        for cfuture in as_completed(cthreads):
            cpath = cthreads[cfuture]
            proceed, compressed, new_file, error = cfuture.result()

            proceed = False

            # Update file info
            delivery.update_delivery(file=cpath,
                                     updinfo={"proceed": proceed,
                                              "compressed": compressed,
                                              "new_file": new_file,
                                              "error": error})

            # Set file as finished
            delivery.set_progress(item=cpath, check=True, finished=True)

            CLI_LOGGER.debug(f"File: {cpath}, Proceed: {proceed}, "
                             f"Info: {delivery.data[cpath]}\n")

            if not proceed:
                CLI_LOGGER.warning(f"File: {cpath} -- moving on to next file")
                continue

            pools[pool_executor.submit(
                delivery.prep_upload,
                cpath,
                delivery.data[cpath])
            ] = cpath

        for pfuture in as_completed(pools):
            ppath = pools[pfuture]
            processed, efile, esize, dp_compressed, error = pfuture.result()

            delivery.update_delivery(file=ppath,
                                     updinfo={'proceed': processed,
                                              'encrypted_file': efile,
                                              'encrypted_size': esize,
                                              'ds_compressed': dp_compressed,
                                              'error': error})

            delivery.set_progress(item=ppath, processing=True, finished=True)

            CLI_LOGGER.debug(f"File: {ppath}, Proceed: {processed}, "
                             f"Info: {delivery.data[ppath]}\n")

            if not processed:
                CLI_LOGGER.warning(f"File: {ppath} -- moving on to next file")
                continue

            uthreads[
                thread_executor.submit(delivery.put,
                                       file=ppath,
                                       fileinfo=delivery.data[ppath])
            ] = ppath

        for ufuture in as_completed(uthreads):
            upath = uthreads[ufuture]
            uploaded, delivered_file, file_path, error = ufuture.result()

            delivery.update_delivery(file=upath,
                                     updinfo={'proceed': uploaded,
                                              'encrypted_file': delivered_file,
                                              'encrypted_size': file_path,
                                              'error': error})

            delivery.set_progress(item=upath, upload=True, finished=True)

            CLI_LOGGER.debug(f"File: {upath}, Uploaded: {uploaded}, "
                             f"Info: {delivery.data[upath]}\n")

            if not uploaded:
                CLI_LOGGER.warning(f"File: {upath} -- moving on to next file")
                continue

            CLI_LOGGER.info(f"File: {upath} -- DELIVERED")

            # update database here
            try:
                with DatabaseConnector('project_db') as project_db:
                    _project = project_db[delivery.project_id]
                    keyinfo = delivery.data[upath]
                    key = str(keyinfo['new_file'])
                    dir_path = str(keyinfo['directory_path'])

                    _project['files'][key] = \
                        {"directory_path": dir_path,
                            "size": keyinfo['size'],
                            "ds_compressed": keyinfo['ds_compressed'],
                            "date_uploaded": timestamp()}
                    project_db.save(_project)
            except Exception as e:  # FIX EXCEPTION HERE
                emessage = f"Could not update database: {e}"
                CLI_LOGGER.warning(emessage)
            else:
                CLI_LOGGER.info("Upload completed!"
                                f"{delivery.data[upath]}")

        # # PROCESSPOOL ########################################### PROCESSPOOL #
        # with ProcessPoolExecutor() as pool_executor:
        #     CLI_LOGGER.debug("Started ProcessPoolExecutor...")

        #     for path in delivery.data:  # Iterate through all files

        #         CLI_LOGGER.debug(f"Beginning delivery of {path}")

        #         # Check files in same folder as failed file
        #         proceed = delivery.get_content_info(item=path)

        #         # CLI_LOGGER.debug(f"Proceed to processing: {proceed}")
        #         if not proceed:
        #             CLI_LOGGER.debug("Moving on to next file")
        #             continue

        #         # CLI_LOGGER.debug(f"proceed: {proceed} --> {path}")

        #         pools[pool_executor.submit(
        #             fh.prep_upload,
        #             path,
        #             delivery.data[path],
        #             delivery.tempdir.files)
        #         ] = path

        #         CLI_LOGGER.info(f"Started processing {path}...")

        #     # THREADPOOL ######################################### THREADPOOL #
        #     with ThreadPoolExecutor() as thread_executor:

        #         # COMPLETED POOLS ########################### COMPLETED POOLS #
        #         for pfuture in as_completed(pools):
        #             opath = pools[pfuture]
        #             try:
        #                 success, (epath, esize, ds_compressed), \
        #                     error = pfuture.result()
        #             except Exception as exc:    # FIX EXCEPTION HERE
        #                 CLI_LOGGER.exception(exc)
        #                 continue

        #             CLI_LOGGER.debug(f"prepped: {success}, \n{opath}, \n"
        #                              f"{epath}, \n{esize}, \n{ds_compressed}, "
        #                              f"\n{error}")

        #             updated = delivery.update_data_dict(
        #                 path=opath,
        #                 pathinfo={
        #                     'proceed': success,
        #                     'encrypted_file': epath,
        #                     'encrypted_size': esize,
        #                     'ds_compressed': ds_compressed,
        #                     'error': error
        #                 }
        #             )
        #             if not updated:
        #                 CLI_LOGGER.exception("Data info dictionary failed"
        #                                      " to be updated, cannot proceed"
        #                                      f" with delivery of '{opath}'")
        #                 continue
        #             if not delivery.data[opath]['proceed']:
        #                 continue

        #             # begin upload
        #             threads[thread_executor.submit(
        #                 delivery.put,
        #                 opath)
        #             ] = opath

        #         # COMPLETED THREADS ####################### COMPLETED THREADS #
        #         for tfuture in as_completed(threads):
        #             ofile = threads[tfuture]
        #             try:
        #                 uploaded, ufile, bucketpath, error = \
        #                     tfuture.result()
        #             except Exception as exc:    # FIX EXCEPTION HERE
        #                 CLI_LOGGER.exception(exc)
        #                 continue

        #             CLI_LOGGER.debug(f"{uploaded}, {ofile}, {ufile}")

        #             if ofile not in delivery.data:  # Bug in code -- FAIL
        #                 CLI_LOGGER.exception("File not recognized.")
        #                 raise Exception("File not found in data dict."
        #                                 " Cancelling delivery.")
        #                 # FIX EXCEPTION HERE

        #             # Data delivery info and returned not equal
        #             if delivery.data[ofile]['encrypted_file'] \
        #                     != ufile:
        #                 emessage = ("Encrypted file path not recorded"
        #                             " for original, entered path.")
        #                 CLI_LOGGER.exception(emessage)
        #                 error = error + emessage

        #             # Update data dictionary
        #             upload_updated = delivery.update_data_dict(
        #                 path=ofile,
        #                 pathinfo={'proceed': uploaded,
        #                           'error': error,
        #                           'up_ok': uploaded}
        #             )

        #             # If data dictionary not uploaded -- failure, move on
        #             if not upload_updated:
        #                 CLI_LOGGER.exception("Data info dictionary failed"
        #                                      " to be updated, cannot proceed"
        #                                      f" with delivery of '{ofile}'")
        #                 continue

        #             # CLI_LOGGER.debug(delivery.data[ofile])
        #             if not delivery.data[ofile]['proceed']:
        #                 CLI_LOGGER.warning("Upload failed, continuing to next file - "
        #                                    f"file: {ofile} "
        #                                    f"({ufile})")
        #                 continue

        #             # Delete file from temporary directory
        #             fh.del_from_temp(file=ufile)

        #             CLI_LOGGER.debug(f"Beginning database update. {ofile}\n"
        #                              f"{delivery.data[ofile]}")
        #             # update database here
        #             try:
        #                 with DatabaseConnector('project_db') as project_db:
        #                     _project = project_db[delivery.project_id]
        #                     keyinfo = delivery.data[ofile]
        #                     key = str(keyinfo['new_file'])
        #                     dir_path = str(keyinfo['directory_path'])

        #                     _project['files'][key] = \
        #                         {"directory_path": dir_path,
        #                          "size": keyinfo['size'],
        #                          "ds_compressed": keyinfo['ds_compressed'],
        #                          "date_uploaded": timestamp()}
        #                     project_db.save(_project)
        #             except Exception as e:  # FIX EXCEPTION HERE
        #                 emessage = f"Could not update database: {e}"
        #                 CLI_LOGGER.warning()
        #                 delivery.data[ofile].update({'error': emessage,
        #                                              'proceed': False,
        #                                              'db_ok': False})
        #             else:
        #                 CLI_LOGGER.info("Upload completed!"
        #                                 f"{delivery.data[ofile]}")
        #                 delivery.data[ofile].update({'proceed': True,
        #                                              'db_ok': True})

        #             CLI_LOGGER.debug("success: "
        #                              f"{delivery.data[ofile]['proceed']}")


@cli.command()
@click.option('--config', '-c',
              required=False,
              type=click.Path(exists=True),
              help="Path to config file containing e.g. username, password, "
                   "project id, etc.")
@click.option('--username', '-u',
              required=False,
              type=str,
              help="Delivery Portal username.")
@click.option('--password', '-pw',
              required=False,
              type=str,
              help="Delivery Portal password.")
@click.option('--project', '-p',
              required=False,
              type=str,
              help="Project to upload files to.")
@click.option('--pathfile', '-f',
              required=False,
              multiple=False,
              type=click.Path(exists=True),
              help="Path to file containing all files and "
                   "folders to be uploaded.")
@click.option('--data', '-d',
              required=False,
              multiple=True,
              type=str,
              help="Path to file or folder to upload.")
def get(config: str, username: str, password: str, project: str,
        pathfile: str, data: tuple):
    """Downloads the files from S3 bucket. Not usable by facilities. """

    with DataDeliverer(config=config, username=username, password=password,
                       project_id=project, pathfile=pathfile, data=data) \
            as delivery:

        recip_pub = delivery.get_recipient_key(keytype="public")
        recip_secret = delivery.get_recipient_key(keytype="private")

        # Create multithreading pool
        with concurrent.futures.ThreadPoolExecutor() as thread_executor:
            download_threads = []
            for path in delivery.data:

                # Download all files
                t_future = thread_executor.submit(delivery.get, path)
                download_threads.append(t_future)

            with concurrent.futures.ProcessPoolExecutor() as pool_exec:
                pools = []
                for f in concurrent.futures.as_completed(download_threads):
                    downloaded = f.result()[0]
                    down_path = f.result()[1]

                    for p in delivery.data[down_path]:
                        sender_pub = delivery.get_recipient_key(
                            keytype="fac_public")
                        p_future = pool_exec.submit(finish_download,
                                                    p, recip_secret, sender_pub)

                        pools.append(p_future)
                        # p_future = pool_exec.submit(gen_hmac, p)
                        # pools.append(p_future)

                    for p in concurrent.futures.as_completed(pools):
                        print(p.result())
