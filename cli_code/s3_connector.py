from pathlib import Path
import os
import sys
import json
import logging
import traceback

import boto3
from boto3.s3.transfer import TransferConfig
import botocore


from cli_code.exceptions_ds import *
from cli_code import LOG_FILE
from cli_code.file_handler import config_logger

S3_LOG = logging.getLogger(__name__)
S3_LOG.setLevel(logging.DEBUG)

S3_LOG = config_logger(
    logger=S3_LOG, filename=LOG_FILE,
    file=True, file_setlevel=logging.DEBUG,
    fh_format="%(asctime)s::%(levelname)s::" +
    "%(name)s::%(lineno)d::%(message)s",
    stream=True, stream_setlevel=logging.DEBUG,
    sh_format="%(levelname)s::%(name)s::" +
    "%(lineno)d::%(message)s"
)


class S3Connector():
    '''
    Keeps information regarding the resource, project and bucket
    currently in use, and handles S3-related checks.

    Args:
        bucketname:     Name of bucket to access
        project:        S3 project to access

    Attributes:
        project:        S3 project ID
        bucketname:     Name of bucket to access
        bucket:         Bucket object to access
        resource:       S3 connection object
    '''

    def __init__(self, bucketname, project):

        self.project = project
        self.bucketname = bucketname
        self.bucket = None
        self.resource = None
        self.connect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through
        else:
            self = None
        return True

    def connect(self):
        '''Connect to S3'''

        # Project access granted -- Get S3 credentials
        s3path = Path.cwd() / Path("sensitive/s3_config.json")
        with s3path.open(mode='r') as f:
            s3creds = json.load(f)

        # Keys and endpoint from file - this will be changed to database
        endpoint_url = s3creds['endpoint_url']
        project_keys = s3creds['sfsp_keys'][self.project]

        # Start s3 connection resource
        self.resource = boto3.resource(
            service_name='s3',
            endpoint_url=endpoint_url,
            aws_access_key_id=project_keys['access_key'],
            aws_secret_access_key=project_keys['secret_key'],
        )
        self.bucket = self.resource.Bucket(self.bucketname)

    def file_exists_in_bucket(self, key: str, put: bool = True) -> (bool, str):
        '''Checks if the current file already exists in the specified bucket.
        If so, the file will not be uploaded.

        Args:
            key:    File to check for in bucket
            put:    True if uploading (default)

        Returns:
            bool:   True if the file already exists, False if it doesnt

        '''

        # if not put:
        #     # If extension --> file, if not --> folder (?)
        #     folder = (len(key.split(os.extsep)) == 1)

        #     if folder:  # path is a folder
        #         if not key.endswith(os.path.sep):
        #             key += os.path.sep  # add path ending
        #             S3_LOG.debug(f"Folder to search for in bucket: {key}")

        # Check if file has been uploaded previously
        try:
            self.resource.Object(
                self.bucket.name, key
            ).load()    # Calls head_object() -- retrieves meta data for object
        except botocore.exceptions.ClientError as e:
            # S3_LOG.debug(f"-------error: {e}")
            if e.response['Error']['Code'] == "404":    # 404 --> not in bucket
                # S3_LOG.debug("The file doesn't exist")
                return False, ""
            else:   # Other eror --> error
                error_message = (f"Checking for file in S3 bucket failed! "
                                 f"Error: {e}")
                S3_LOG.warning(error_message)
                return False, error_message
        else:   # In bucket --> no delivery of file
            S3_LOG.debug(f"The file {key} already exists.")
            return True, ""

    def delete_item(self, key: str):
        '''Deletes specified item

        Args:
            key:    Item (e.g. file) to delete from bucket
        '''

        try:
            self.resource.Object(
                self.bucket.name, key
            ).delete()
        except Exception as delex:
            S3_LOG.exception(delex)
        else:
            S3_LOG.info(f"Item {key} deleted from bucket.")
