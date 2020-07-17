"""
Custom xceptions related to the Data Delivery System
"""

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


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


# File handling ############################################### File handling #
class CompressionError(Exception):
    """Errors related to compression operations."""

    def __init__(self, msg: str):
        """Passes message from exception call to the base class __init__."""

        super().__init__(msg)


###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def printout_error(message: str = "") -> (str):
    '''Adds "padding" to error messages -> more attention.

    Args:
        message (str): Error message

    Returns:
        str: Padded error message for console printout

    '''

    return ("\nx x x x x x x x x x x x x x x x x x x x x x x x\n\n"
            + message +
            "\n\nx x x x x x x x x x x x x x x x x x x x x x x x\n")
