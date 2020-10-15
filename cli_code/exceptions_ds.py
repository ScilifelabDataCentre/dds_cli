"""
Custom xceptions related to the Data Delivery System
"""

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################

# DataDeliverer ############################################### DataDeliverer #


class DeliverySystemException(Exception):
    """Errors regarding Delivery Portal access etc"""


# S3 ##################################################################### S3 #


class S3Error(Exception):
    """Errors regarding S3 storage, e.g. upload, download,
    buckets, resources, etc. """



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
