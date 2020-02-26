from pathlib import Path
import os
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
        s3path = str(Path(os.getcwd())) + "/sensitive/s3_config.json"
        with open(s3path) as f:
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

        response = self.resource.meta.client.list_objects_v2(
            Bucket=self.bucket.name,
            Prefix=key,
        )
        for obj in response.get('Contents', []):
            if obj['Key'] == key:
                return True

        return False

    def upload(self, file: str, spec_path: str) -> (str):
        '''Handles processing of files including compression and encryption.

        Args:
            file:           File to be uploaded
            spec_path:      The original specified path, None if single specified file
            s3_resource:    The S3 connection resource
            bucket:         S3 bucket to upload to

        '''

        filetoupload = os.path.abspath(file)
        filename = os.path.basename(filetoupload)

        root_folder = ""
        filepath = ""
        all_subfolders = ""

        # Upload file
        MB = 1024 ** 2
        GB = 1024 ** 3
        config = TransferConfig(multipart_threshold=5*GB,
                                multipart_chunksize=5*MB)

        # check if bucket exists
        if self.bucket in self.resource.buckets.all():
            # if file, not within folder
            if spec_path is None:
                filepath = filename
            else:
                root_folder = os.path.basename(os.path.normpath(spec_path))
                filepath = f"{root_folder}{filetoupload.split(root_folder)[-1]}"
                all_subfolders = f"{filepath.split(filename)[0]}"

                # check if folder exists
                response = self.resource.meta.client.list_objects_v2(
                    Bucket=self.bucket.name,
                    Prefix="",
                )

                found = False
                for obj in response.get('Contents', []):
                    if obj['Key'] == all_subfolders:
                        found = True
                        break

                if not found:   # if folder doesn't exist then create folder
                    self.resource.meta.client.put_object(Bucket=self.bucket.name,
                                                         Key=all_subfolders)

            # check if file exists
            if self.file_exists_in_bucket(key=filepath):
                return f"File exists: {filename}, not uploading file."
            else:
                try:
                    self.resource.meta.client.upload_file(filetoupload, self.bucket.name,
                                                          filepath, Config=config)
                except Exception as e:
                    print("Something wrong: ", e)
                else:
                    return f"Success: {filetoupload} uploaded to S3!"

    def download(self, file: str, dl_file: str) -> (str):
        '''Downloads the specified files

        Args: 
            file:           File to be downloaded
            s3_resource:    S3 connection
            bucket:         Bucket to download from
            dl_file:        Name of downloaded file

        Returns:
            str:    Success message if download successful 

        '''

        print(file, os.path.basename(file))
        # check if bucket exists
        if self.bucket in self.resource.buckets.all():

            # check if file exists
            if not self.file_exists_in_bucket(key=file) and not \
                    self.file_exists_in_bucket(key=f"{file}/"):
                return f"File does not exist: {file}, not downloading anything."
            else:
                try:
                    self.resource.meta.client.download_file(
                        self.bucket.name, file, dl_file)
                except Exception as e:
                    print("Something wrong: ", e)
                else:
                    return f"Success: {file} downloaded from S3!"
