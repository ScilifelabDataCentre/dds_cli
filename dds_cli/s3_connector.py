"""S3 Connector module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import dataclasses
import logging
import os
import requests
import traceback
import sys
import gc

# Installed
import boto3
import botocore
import simplejson

# Own modules
from dds_cli import DDSEndpoint
from dds_cli.cli_decorators import connect_cloud
from dds_cli import utils

###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@dataclasses.dataclass
class S3Connector:
    """Connect to Simple Storage Service."""

    project_id: dataclasses.InitVar[str]
    token: dataclasses.InitVar[dict]
    safespring_project: str = dataclasses.field(init=False)
    keys: dict = dataclasses.field(init=False)
    url: str = dataclasses.field(init=False)
    bucketname: str = dataclasses.field(init=False)
    resource = None

    def __post_init__(self, project_id, token):
        LOG.info("starting.....")
        (
            self.safespring_project,
            self.keys,
            self.url,
            self.bucketname,
        ) = self.__get_s3_info(project_id=project_id, token=token)

    # @connect_cloud
    def __enter__(self):
        LOG.info("entering...")
        self.resource = self.connect()

        return self

    def __exit__(self, exc_type, exc_value, tb):
        del self.resource
        gc.collect()
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def connect(self):
        # Connect to service
        try:
            session = boto3.session.Session()

            resource = session.resource(
                service_name="s3",
                endpoint_url=self.url,
                aws_access_key_id=self.keys["access_key"],
                aws_secret_access_key=self.keys["secret_key"],
            )
        except (boto3.exceptions.Boto3Error, botocore.exceptions.BotoCoreError) as err:
            LOG.warning(f"S3 connection failed: {err}")
            raise

        LOG.info(f"Resource :{self.resource}")
        return resource

    # Static methods ############ Static methods #
    @staticmethod
    def __get_s3_info(project_id, token):
        """Get information required to connect to cloud."""
        # Perform request to API
        try:
            response = requests.get(
                DDSEndpoint.S3KEYS,
                params={"project": project_id},
                headers=token,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            LOG.warning(err)
            raise SystemExit from err

        # Error
        if not response.ok:
            message = f"Failed retrieving Safespring project name. Server response: {response.text}"
            LOG.warning(message)
            raise SystemExit(message)  # TODO: Change

        # Get s3 info
        s3info = utils.get_json_response(response=response)

        safespring_project, keys, url, bucket = (
            s3info.get("safespring_project"),
            s3info.get("keys"),
            s3info.get("url"),
            s3info.get("bucket"),
        )
        if None in [safespring_project, keys, url, bucket]:
            raise SystemExit("Missing safespring information in response.")  # TODO: change

        return safespring_project, keys, url, bucket

    # Public methods ############ Public methods #
    def check_bucket_exists(self):
        """Check if the bucket exists."""
        LOG.debug(f"Bucket name: {self.bucketname}")
        try:
            self.resource.meta.client.head_bucket(Bucket=self.bucketname)
        except botocore.client.ClientError:
            LOG.info(f"Bucket '{self.bucketname}' does not exist!")
            return False

        return True

    def check_bucketname(self):
        """Check that the bucketname restrictions are met."""
        bnlen = len(self.bucketname)
        if not 3 <= bnlen <= 63:
            # Add custom exception
            LOG.error(
                f"Invalid bucket name length. Must be between 3 and 63 characters, found {bnlen}"
            )
            os._exit(0)

        if "_" in self.bucketname:
            # Add custom exception
            LOG.error(f"Invalid bucket name characters. Cannot contain underscores.")
            os._exit(0)

        bucketnamefirst = list(self.bucketname)[0]
        if not (bucketnamefirst.islower() or bucketnamefirst.isdigit()):
            # Add custom exception
            LOG.error(
                f"Invalid first character. Must be digit or lowercase letter, found '{bucketnamefirst}'",
            )
            os._exit(0)

    def create_bucket(self):
        """Creates the bucket"""

        self.check_bucketname()

        LOG.info(f"Creating bucket '{self.bucketname}'...")
        try:
            self.resource.meta.client.create_bucket(Bucket=self.bucketname, ACL="private")
        except botocore.client.ClientError as err2:
            LOG.critical(f"Could not create bucket {self.bucketname}! {err2}")

        bucket_exists = self.check_bucket_exists()
        if not bucket_exists:
            print(f"Bucket '{self.bucketname}' does not exist. Failed second attempt.")
            os._exit(0)
        LOG.info(f"Bucket '{self.bucketname}' created!")

        return True
