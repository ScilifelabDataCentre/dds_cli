#!/usr/bin/env python3
"""Exceptions"""

# IMPORTS ############################################################ IMPORTS #
from cli_code import PRINT_ERR_S, PRINT_ERR_E
# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #
# CLASSES ############################################################ CLASSES #

# Database ######################################################### Database #


class CouchDBException(Exception):
    """Errors in database operations."""

    def __init__(self, msg: str):
        """Passes message from exception call to the base class __init__."""

        super().__init__(msg)


# DataDeliverer ############################################### DataDeliverer #


class DataException(Exception):
    """Errors related to the data entered as an option"""

    def __init__(self, msg: str):
        """Passes message from exception call to the base class __init__"""

        super().__init__(msg)


class DeliveryOptionException(Exception):
    """Errors regarding data delivery options (s3 delivery) etc."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


class DeliverySystemException(Exception):
    """Errors regarding Delivery Portal access etc"""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


# Logging ########################################################### Logging #

class LoggingError(Exception):
    """Errors regarding logging"""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


# Main -- CLI ################################################### Main -- CLI #


class PoolExecutorError(Exception):
    """Errors relating to ThreadPoolExecutors and ProcessPoolExecutors"""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


# S3 ##################################################################### S3 #


class S3Error(Exception):
    """Errors regarding S3 storage, e.g. upload, download,
    buckets, resources, etc. """

    def __init__(self, msg: str):
        super().__init__(msg)


# ----


class AuthenticationError(Exception):
    """Custom exception class. Handles errors regarding delivery portal authentications."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


class CompressionError(Exception):
    """Errors related to compression operations."""

    def __init__(self, msg: str):
        """Passes message from exception call to the base class __init__."""

        super().__init__(msg)


class EncryptionError(Exception):
    """Handles errors regarding data encryption."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


class HashException(Exception):
    """Handles errors regarding checksum generation."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


class SecurePasswordException(Exception):
    """Custom exception class. Handles errors regarding password retrieval and handling."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


class StreamingError(Exception):
    """Custom exception class. Handles errors regarding streaming file contents."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


def printout_error(message):

    return ("\nx x x x x x x x x x x x x x x x x x x x x x x x\n\n"
            + message +
            "\n\nx x x x x x x x x x x x x x x x x x x x x x x x\n")
