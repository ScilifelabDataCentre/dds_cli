"""S3 Connector module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import traceback
import os
import sys
import dataclasses
import functools
import requests

# Installed
import boto3
import botocore
import rich

# Own modules
from cli_code import DDSEndpoint
from cli_code.cli_decorators import connect_cloud

###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@dataclasses.dataclass
class S3Connector:
    """Connects to Simple Storage Service."""

    project_id: dataclasses.InitVar[str]
    token: dataclasses.InitVar[dict]
    safespring_project: str = dataclasses.field(init=False)
    keys: dict = dataclasses.field(init=False)
    url: str = dataclasses.field(init=False)
    bucketname: str = dataclasses.field(init=False)
    resource = None

    def __post_init__(self, project_id, token):

        self.safespring_project, self.keys, self.url, self.bucketname, \
            self.message = self.get_s3_info(project_id=project_id, token=token)

    @connect_cloud
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    @staticmethod
    def get_s3_info(project_id, token):
        """Get information required to connect to cloud."""

        if None in [project_id, token]:
            raise Exception("Project information missing, cannot connect "
                            "to cloud.")

        response = requests.get(DDSEndpoint.S3KEYS,
                                headers=token)

        if not response.ok:
            return (None, None, None, None,
                    "Failed retrieving Safespring project name:"
                    f"{response.text}")

        s3info = response.json()

        return s3info["safespring_project"], s3info["keys"], s3info["url"], \
            s3info["bucket"], ""

    def check_bucket_exists(self):
        """Checks if the bucket exists"""

        try:
            self.resource.meta.client.head_bucket(Bucket=self.bucketname)
        except botocore.client.ClientError:
            log.info("Bucket '%s' does not exist!", self.bucketname)
            return False

        return True

    def create_bucket(self):
        """Creates the bucket"""

        log.info("Creating bucket '%s'...", self.bucketname)

        try:
            self.resource.meta.client.create_bucket(Bucket=self.bucketname,
                                                    ACL="private")
        except botocore.client.ClientError as err2:
            log.critical("Could not create bucket %s! %s",
                         self.bucketname, err2)
            return False

        bucket_exists = self.check_bucket_exists()
        if not bucket_exists:
            sys.exit("Bucket '%s' does not exist. Failed second attempt.")

        log.info("Bucket '%s' created!", self.bucketname)

        return True
