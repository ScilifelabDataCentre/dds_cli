"""S3 Connector module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import traceback
import requests
import sys
import dataclasses
import functools

# Installed
import boto3
import botocore

# Own modules
from cli_code import DDSEndpoint
from cli_code import timestamp

###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################


def s3info_required(func):
    """Gets required cloud information incl. project and keys."""

    @functools.wraps(func)
    def get_s3_info(self, *args, **kwargs):

        if not all(x in kwargs for x in ["project_id", "token"]):
            raise Exception("Project information missing, cannot connect "
                            "to cloud.")

        params = {"project": kwargs["project_id"]}

        response = requests.get(DDSEndpoint.S3KEYS,
                                params=params, headers=kwargs["token"])

        if not response.ok:
            raise Exception("Failed retrieving Safespring project name. "
                            f"Error code: {response.status_code} "
                            f" -- {response.reason}"
                            f"{response.text}")

        s3info = response.json()

        return func(self, safespring_project=s3info["safespring_project"],
                    keys=s3info["keys"], url=s3info["url"],
                    bucketname=s3info["bucket"])

    return get_s3_info


def connect_cloud(func):
    """Connect to S3"""

    @functools.wraps(func)
    def init_resource(self, *args, **kwargs):

        # Connect to service
        try:
            session = boto3.session.Session()

            self.resource = session.resource(
                service_name="s3",
                endpoint_url=self.url,
                aws_access_key_id=self.keys["access_key"],
                aws_secret_access_key=self.keys["secret_key"]
            )
        except botocore.client.ClientError as err:
            sys.exit("S3 connection failed: %s", err)

        return func(self, *args, **kwargs)

    return init_resource


###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class S3Connector:
    """Connects to Simple Storage Service."""

    @s3info_required
    def __init__(self, safespring_project, keys, url, bucketname):
        self.safespring_project = safespring_project
        self.keys = keys
        self.url = url
        self.bucketname = bucketname
        self.resource = None

    @connect_cloud
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def __repr__(self):
        return "<S3Connector>"

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
