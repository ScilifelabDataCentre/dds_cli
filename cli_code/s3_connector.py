"""S3 Connector.

Communicates with and handles operations related to Safespring S3, including
deleting items from the bucket and performing checks on whether the files
exist in the buckets.
"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import traceback

# Installed
import boto3
import boto3.session
import botocore
import botocore.client
import requests

# Own modules
from cli_code import ENDPOINTS
from cli_code import exceptions_ds

###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################

S3_LOG = logging.getLogger(__name__)
S3_LOG.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class S3Connector:
    """Connection to the Safespring S3 instance.

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
        session:        Session - needed for multithreading/processing

    """

    def __init__(self, bucketname, project):

        self.project = project
        self.bucketname = bucketname
        self.bucket = None
        self.resource = None
        self.session = None
        self._connect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def _connect(self):
        """Connect to S3"""

        s3_creds_resp = requests.get(ENDPOINTS["s3info"])
        if not s3_creds_resp.ok:
            sys.exit(
                exceptions_ds.printout_error(
                    "No S3 access information available. "
                    f"Cannot upload/download. {s3_creds_resp.status_code}, "
                    f"{s3_creds_resp.reason}"
                )
            )
        s3creds = s3_creds_resp.json()

        try:
            # Start S3 session
            self.session = boto3.session.Session()      # --> Thread safe

            # TODO (ina): Put in DB, not in file
            # Get S3 credentials
            # Structure in file: {
            # 	                    "endpoint_url": "endpointurl",
            # 	                    "sfsp_keys": {
            # 		                    "s3projectname": {
            # 			                    "access_key": "accesskey",
            # 			                    "secret_key": "secretkey"
            # 		                    }
            # 	                    }
            #                   }

            # Keys and endpoint from file - this will be changed to database
            endpoint_url = s3creds["endpoint_url"]
            for key in s3creds["sfsp_keys"]:  # TODO (ina): get project from db
                self.project = key
                break
            project_keys = s3creds["sfsp_keys"][self.project]

            # Start s3 connection resource
            self.resource = self.session.resource(
                service_name="s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=project_keys["access_key"],
                aws_secret_access_key=project_keys["secret_key"],
            )

            # Connect to bucket
            try:
                self.resource.meta.client.head_bucket(Bucket=self.bucketname)
            except botocore.client.ClientError as cle:
                error = (f"Bucket: {self.bucketname} - Bucket not found in "
                         f"S3 resource. Error: {cle}")
                S3_LOG.critical(error)

                # Create bucket if it doesn't already exist
                try:
                    self.resource.meta.client.create_bucket(
                        Bucket=self.bucketname)
                except botocore.client.ClientError as cle:
                    error = (f"Bucket: {self.bucketname} could not be created "
                             "in S3 resource. Error: {cle}")
                    S3_LOG.critical(error)
                    sys.exit(error)     # Fatal -> ds will not work
                else:
                    # Connect to the bucket if it was successfully created
                    try:
                        self.resource.meta.client.head_bucket(
                            Bucket=self.bucketname)
                    except botocore.client.ClientError as cle:
                        # Cancel delivery if connection failed
                        error = (f"Bucket: {self.bucketname} - Bucket not found in "
                                 f"S3 resource. Error: {cle}")
                        S3_LOG.critical(error)
                        sys.exit(error)     # Fatal -> ds will not work

            self.bucket = self.resource.Bucket(self.bucketname)
        except botocore.client.ClientError as e:
            S3_LOG.exception("S3 connection failed: %s", e)

        # S3_LOG.info("S3 connection successful.")

    def delete_item(self, key: str):
        """Deletes specified item from S3 bucket.

        Args:
            key (str):    Item (e.g. file) to delete from bucket

        Raises:
            S3Error:    Error while deleting object
        """

        try:
            self.resource.Object(
                self.bucket.name, key
            ).delete()
        except exceptions_ds.S3Error as delex:
            S3_LOG.exception(delex)
        else:
            S3_LOG.info("Item %s deleted from bucket.", key)

    def file_exists_in_bucket(self, key: str) -> (bool, str):
        """Checks if the current file already exists in the specified bucket.
        If so, the file will not be uploaded (put), or will be downloaded (get)

        Args:
            key (str):      File to check for in bucket
            put (bool):     True if uploading (default)

        Returns:
            bool:   True if the file already exists, False if it doesnt
            str:    Error message, "" if none

        Raises:
            botocore.exceptions.ClientError:    Error in searching bucket.
                                                404 -> OK, not 404 -> not OK

        """

        try:
            # Retrieve meta data for object -- 404 error if not in bucket
            self.resource.Object(self.bucket.name, key).load()
        except botocore.exceptions.ClientError as e:
            # If 404 -- OK! If other error -- NOT OK!
            if e.response["Error"]["Code"] == "404":   # 404 --> not in bucket
                S3_LOG.info("File %s: Not in bucket --> proceeding", key)
                return False, ""
            else:
                error_message = (f"Checking for file in S3 bucket failed! "
                                 f"Error: {e}")
                S3_LOG.warning(error_message)
                return False, error_message

        S3_LOG.info("File %s: In bucket.", key)
        return True, ""
