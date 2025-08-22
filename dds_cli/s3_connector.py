"""S3 Connector module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import dataclasses
import logging
import traceback

# Installed
import boto3
import botocore

# Own modules
import dds_cli.utils
from dds_cli import DDSEndpoint

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
        """Initiate S3Connector object by getting s3 info from API."""
        (
            self.safespring_project,
            self.keys,
            self.url,
            self.bucketname,
        ) = self.__get_s3_info(project_id=project_id, token=token)

    # @connect_cloud
    def __enter__(self):
        """Enter context."""
        self.resource = self.connect()

        return self

    def __exit__(self, exc_type, exc_value, traceb):
        """Close context manager, incl. connection."""
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, traceb)
            return False  # uncomment to pass exception through

        return True

    def connect(self):
        """Connect to S3 resource."""
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
            LOG.warning("S3 connection failed: %s", err)
            raise

        LOG.debug("Connected to S3.")
        return resource

    # Static methods ############ Static methods #
    @staticmethod
    def __get_s3_info(project_id, token):
        """Get information required to connect to cloud."""
        # Perform request to API
        s3info, _ = dds_cli.utils.perform_request(
            DDSEndpoint.S3KEYS,
            method="get",
            params={"project": project_id},
            headers=token,
            error_message="Failed to get cloud information",
        )
        LOG.debug("API call for S3 info")
        # Get s3 info

        safespring_project, keys, url, bucket = (
            s3info.get("safespring_project"),
            s3info.get("keys"),
            s3info.get("url"),
            s3info.get("bucket"),
        )
        if None in [safespring_project, keys, url, bucket]:
            raise SystemExit("Missing safespring information in response.")  # TODO: change

        return safespring_project, keys, url, bucket
