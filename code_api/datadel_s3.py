from pathlib import Path
import os
import sys
import json

import boto3
from boto3.s3.transfer import TransferConfig

from code_api.dp_exceptions import *


class S3Object():
    '''
    Keeps information regarding the resource, project and bucket
    currently in use, and handles S3-related checks.

    Attributes:
        resource:       S3 connection object
        project (str):  S3 project ID
        bucket:         S3 bucket object
    '''

    def __init__(self):
        self.resource = None
        self.project = None
        self.bucket = None

    def get_info(self, current_project: str):
        '''Gets the users s3 credentials including endpoint and key pair,
        and a bucket object representing the current project.

        Args:
            current_project (str):    The project ID to which the data belongs

        '''

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

        # Bucket to upload to specified by user
        bucketname = f"project_{current_project}"
        self.bucket = self.resource.Bucket(bucketname)

    def file_exists_in_bucket(self, key: str) -> (bool):
        '''Checks if the current file already exists in the specified bucket.
        If so, the file will not be uploaded.

        Args:
            s3_resource:    Boto3 S3 resource
            bucket:         Name of bucket to check for file
            key:            Name of file to look for

        Returns:
            bool:   True if the file already exists, False if it doesnt

        '''

        folder = (len(key.split(os.extsep)) == 1)
        matching_paths = list()

        if folder: 
            if not key.endswith(os.path.sep):  # path is a folder
                key += os.path.sep

        response = self.resource.meta.client.list_objects_v2(
            Bucket=self.bucket.name,
            Prefix=key,
        )

        matching_paths = [path['Key'] for path in response.get('Contents', []) if path['Key'].startswith(key) and Path(path['Key']).is_file()]
        
        if matching_paths: 
            return True, matching_paths
        else: 
            return False, matching_paths
        # sys.exit(f"Download paths: {matching_paths}")

        # for obj in response.get('Contents', []):
        #     print(f"{obj['Key']}, {key in obj['Key']}")
        #     print(Path(obj['Key']).match(f'{key}*'))
        #     if obj['Key'] == key:
        #         # print(Path(obj['Key']).parts)
        #         return True
        #     else: 
        #         print("nope")

        # return False
