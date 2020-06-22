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
S3_LOG.debug("6. debug")


class S3Connector():
    '''
    Keeps information regarding the resource, project and bucket
    currently in use, and handles S3-related checks.

    Attributes:
        resource:       S3 connection object
        project (str):  S3 project ID
        bucket:         S3 bucket object
    '''

    def __init__(self, bucketname, project):
        
        self.project = project
        self.bucketname = bucketname
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

    def file_exists_in_bucket(self, key: str, put: bool = True) -> (bool):
        '''Checks if the current file already exists in the specified bucket.
        If so, the file will not be uploaded.

        Args:
            s3_resource:    Boto3 S3 resource
            bucket:         Name of bucket to check for file
            key:            Name of file to look for

        Returns:
            bool:   True if the file already exists, False if it doesnt

        '''

        # If extension --> file, if not --> folder (?)
        folder = (len(key.split(os.extsep)) == 1)
        S3_LOG.debug(f"{key} -- folder? -- {folder}, should be false for put")

        if folder:  # path is a folder
            if not key.endswith(os.path.sep):
                key += os.path.sep  # add path ending
                S3_LOG.debug(f"Folder to search for in bucket: {key}")

        try:    # Check if file has been uploaded previously
            self.resource.Object(
                self.bucket.name, key   # swap to suff or full
            ).load()    # Calls head_object() -- retrieves meta data for object
        except botocore.exceptions.ClientError as e:
            S3_LOG.debug(f"-------error: {e}")
            if e.response['Error']['Code'] == "404":
                S3_LOG.debug("The file doesn't exist")
                return False
            else:
                error_message = f"Checking for file in S3 bucket failed! " \
                    f"Error: {e}"
                S3_LOG.warning(error_message)
                return error_message
        else:
            S3_LOG.debug("The file already exists.")
            return True

    def files_in_bucket(self, key: str):
        '''Checks if the current file already exists in the specified bucket.
        If so, the file will not be uploaded.

        Args:
            s3_resource:    Boto3 S3 resource
            bucket:         Name of bucket to check for file
            key:            Name of file to look for

        Returns:
            bool:   True if the file already exists, False if it doesnt

        '''
        # If extension --> file, if not --> folder (?)
        folder = (len(key.split(os.extsep)) == 1)

        if folder:
            if not key.endswith(os.path.sep):  # path is a folder
                key += os.path.sep

        object_summary_iterator = self.bucket.objects.filter(Prefix=key)
        return object_summary_iterator
        # for o in object_summary_iterator:
        #     yield o
