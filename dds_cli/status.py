"""Status module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging

# Installed


# Own modules

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DeliveryStatus:
    """Delivery status class."""

    UPLOAD_STATUS = {
        "upload": {"in_progress": False, "finished": False},
        "processing": {"in_progress": False, "finished": False},
        "database": {"in_progress": False, "finished": False},
    }

    # Class methods ############ Class methods #
    @classmethod
    def cancel_all(cls):
        """Cancel upload all files."""

    @classmethod
    def cancel_one(cls):
        """Cancel the failed file."""


class ProgressPercentage:
    """Updates the progress bar with the callback from boto3."""

    def __init__(self, progress, task):
        """Keep track of progress."""
        self.progress = progress
        self.task = task

        self._seen_so_far = 0

    def __call__(self, bytes_amount, **_):
        """Update progress."""
        self._seen_so_far += bytes_amount
        self.progress.update(self.task, advance=bytes_amount)
