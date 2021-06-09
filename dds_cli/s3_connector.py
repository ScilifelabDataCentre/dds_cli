"""S3 Connector module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import dataclasses
import logging
import os
import requests
import sys
import traceback

# Installed
import botocore
import rich
import simplejson

# Own modules
from dds_cli import DDSEndpoint
from dds_cli.cli_decorators import connect_cloud

###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################

LOG = logging.getLogger(__name__)

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

        (
            self.safespring_project,
            self.keys,
            self.url,
            self.bucketname,
            self.message,
        ) = self.get_s3_info(project_id=project_id, token=token)

    @connect_cloud
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    # Static methods ############ Static methods #
    @staticmethod
    def get_s3_info(project_id, token):
        """Get information required to connect to cloud."""

        sfsp_proj, keys, url, bucket, error = (None, None, None, None, "")

        if None in [project_id, token]:
            raise Exception("Project information missing, cannot connect to cloud.")

        # Perform request to API
        try:
            response = requests.get(
                DDSEndpoint.S3KEYS,
                headers=token,
                timeout=DDSEndpoint.TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            LOG.warning(err)
            raise SystemExit from err

        # Error
        assert (
            response.ok
        ), f"Failed retrieving Safespring project name. Server response: {response.text}"

        # Get s3 info
        try:
            s3info = response.json()
        except simplejson.JSONDecodeError as err:
            raise SystemExit from err

        if any(value is None for value in s3info.values()):
            error = "Response ok but s3 info missing."
        else:
            sfsp_proj, keys, url, bucket = (
                s3info["safespring_project"],
                s3info["keys"],
                s3info["url"],
                s3info["bucket"],
            )

        return sfsp_proj, keys, url, bucket, error

    # Public methods ############ Public methods #
    def check_bucket_exists(self):
        """Checks if the bucket exists"""

        LOG.debug(f"Bucket name: {self.bucketname}")
        try:
            self.resource.meta.client.head_bucket(Bucket=self.bucketname)
        except botocore.client.ClientError:
            LOG.info(f"Bucket '{self.bucketname}' does not exist!")
            return False

        return True

    def check_bucketname(self):
        """Checks that the bucketname restrictions are met."""

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
