"""Data Delivery System

This package allows SciLifeLab facilities to deliver data to their users in
a secure way.

Any type of file or folder can be delivered. Compressed files or archives will
not be compressed, all other files will (with Zstandard). All files (if not
--no-encryption flag used) will be encrypted with ChaCha20-Poly1305.

"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime
import logging
import shutil
import sys
from pathlib import Path

###############################################################################
# PROJECT SPEC ################################################# PROJECT SPEC #
###############################################################################

__title__ = 'SciLifeLab Data Delivery System'
__version__ = '0.1'
__author__ = 'SciLifeLab Data Centre'
__author_email__ = ''
__license__ = 'MIT'
__all__ = ['DIRS', 'LOG_FILE']  # TODO: Add things here and add to modules

PROG = 'ds_deliver'

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# DEBUG     -- Detailed information, typically of interest only when diagnosing
#              problems.
# INFO      -- Confirmation that things are working as expected.
# WARNING   -- An indication that something unexpected happened, or indicative
#              of some problem in the near future (e.g. ‘disk space low’). The
#              software is still working as expected.
# ERROR     -- Due to a more serious problem, the software has not been able to
#              perform some function.
# CRITICAL  -- A serious error, indicating that the program itself may be
#           -- unable to continue running.
LOG = logging.getLogger(__name__)

###############################################################################
# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #
###############################################################################

SEGMENT_SIZE = 65536                        # Chunk size while reading file
CIPHER_SEGMENT_SIZE = SEGMENT_SIZE + 16     # Chunk to read from encrypted file
DS_MAGIC = b'DelSys'                        # DS signature in encrypted key

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def timestamp() -> (str):
    '''Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    '''

    now = datetime.datetime.now()
    timestamp = ""

    for t in (now.year, "-", now.month, "-", now.day, " ",
              now.hour, ":", now.minute, ":", now.second):
        if len(str(t)) == 1 and isinstance(t, int):
            timestamp += f"0{t}"
        else:
            timestamp += f"{t}"

    return timestamp.replace(" ", "_").replace(":", "-")


def create_directories():
    '''Creates all temporary directories.

    Returns:
        tuple:  Directories created and all paths

            bool:   True if directories created
            tuple:  All created directories

    Raises:
        IOError:    Temporary folder failure
    '''

    # Create temporary folder with timestamp and all subfolders
    timestamp_ = timestamp()
    temp_dir = Path.cwd() / Path(f"DataDelivery_{timestamp_}")

    # TemporaryDirectories = collections.namedtuple('TemporaryDirectories',
    #                                               'root files meta logs')
    dirs = (temp_dir / Path(""),
            temp_dir / Path("files/"),
            temp_dir / Path("meta/"),
            temp_dir / Path("logs/"))

    for d_ in dirs:
        try:
            d_.mkdir(parents=True)
        except IOError as ose:
            print(f"The directory '{d_}' could not be created: {ose}"
                  "Cancelling delivery. ")

            if temp_dir.exists() and not isinstance(ose, FileExistsError):
                print("Deleting temporary directory.")
                try:
                    # Remove all prev created folders
                    shutil.rmtree(temp_dir)
                    sys.exit(f"Temporary directory deleted. \n\n"
                             "----DELIVERY CANCELLED---\n")  # and quit
                except IOError as ose:
                    sys.exit(f"Could not delete directory {temp_dir}: "
                             f"{ose}\n\n ----DELIVERY CANCELLED---\n")

                    return False, ()
            else:
                pass  # create log file here

    return True, dirs


def config_logger(filename: str):
    '''Creates log file

    Args:
        filename:           Path to wished log file

    Returns:
        Logger:     Configured logger

    Raises:
        Exception:   Logging to file or console failed
    '''

    logger = logging.getLogger(__name__)

    # Config file logger
    try:
        file_handler = logging.FileHandler(filename=filename)
        file_handler.setLevel(logging.DEBUG)
        fh_formatter = logging.Formatter("%(asctime)s::%(levelname)s::" +
                                         "%(name)s::%(lineno)d::%(message)s")
        file_handler.setFormatter(fh_formatter)
        logger.addHandler(file_handler)
    except Exception as ex:
        sys.exit(f"Logging to file failed: {ex}")

    # Config file logger
    try:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.CRITICAL)
        sh_formatter = logging.Formatter("%(levelname)s::%(name)s::" +
                                         "%(lineno)d::%(message)s")
        stream_handler.setFormatter(sh_formatter)
        logger.addHandler(stream_handler)
    except Exception as ex:
        sys.exit(f"Logging to console failed: {ex}")

    return logger

###############################################################################
# START - CREATE ############################################# START - CREATE #
###############################################################################


created, DIRS = create_directories()
if not created:
    raise OSError("Temporary directory could not be created. "
                  "Unable to continue delivery. Aborting. ")

LOG_FILE = str(DIRS[-1] / Path("ds.log"))   # Get log file name
LOG = config_logger(filename=LOG_FILE)

API_BASE = "http://127.0.0.1:5000/api/v1"