"""
Custom xceptions related to the Data Delivery System
"""

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################

# DataDeliverer ############################################### DataDeliverer #


class DeliveryOptionException(Exception):
    """Errors regarding data delivery options (s3 delivery) etc."""


class DeliverySystemException(Exception):
    """Errors regarding Delivery Portal access etc"""


# Logging ########################################################### Logging #
class LoggingError(Exception):
    """Errors regarding logging"""


# Main -- CLI ################################################### Main -- CLI #
class PoolExecutorError(Exception):
    """Errors relating to ThreadPoolExecutors and ProcessPoolExecutors"""


# S3 ##################################################################### S3 #
class S3Error(Exception):
    """Errors regarding S3 storage, e.g. upload, download,
    buckets, resources, etc. """


# File handling ############################################### File handling #
class CompressionError(Exception):
    """Errors related to compression operations."""


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
