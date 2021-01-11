"""Data Delivery System

This package allows SciLifeLab facilities to deliver data to their users in
a secure way.

Any type of file or folder can be delivered. Compressed files or archives will
not be compressed, all other files will (with Zstandard). All files will be
encrypted with ChaCha20-Poly1305.

"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime
import logging
import pathlib
import shutil
import sys

###############################################################################
# PROJECT SPEC ################################################# PROJECT SPEC #
###############################################################################

__title__ = "SciLifeLab Data Delivery System"
__version__ = "0.1"
__author__ = "SciLifeLab Data Centre"
__author_email__ = ""
__license__ = "MIT"

PROG = "ds_deliver"

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
DS_MAGIC = b"DelSys"                        # DS signature in encrypted key

API_BASE = "http://127.0.0.1:5000/api/v1"
# API_BASE = "https://dds.dckube.scilifelab.se/api/v1"
ENDPOINTS = {"u_login": API_BASE + "/user/login",
             "project_files": API_BASE + "/project/",
             "update_file": API_BASE + "/updatefile",
             "key": API_BASE + "/project/",
             "delivery_date": API_BASE + "/delivery/date/",
             "s3info": API_BASE + "/s3info"}

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class Format:
    """Formats strings"""

    HEADER = '\033[95m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################


def timestamp(folder: bool = False) -> (str):
    """Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    """

    sep_date_time = "_" if folder else " "
    sep_time = "-" if folder else ":"

    now = datetime.datetime.now()
    t_s = ""

    for t in (now.year, "-", now.month, "-", now.day, sep_date_time,
              now.hour, sep_time, now.minute, sep_time, now.second):
        if len(str(t)) == 1 and isinstance(t, int):
            t_s += f"0{t}"
        else:
            t_s += f"{t}"

    return t_s


def create_directories():
    """Creates all temporary directories.

    Returns:
        tuple:  Directories created and all paths

            bool:   True if directories created
            tuple:  All created directories

    Raises:
        IOError:    Temporary folder failure
    """

    # Create temporary folder with timestamp and all subfolders

    for d_i in DIRS:
        try:
            d_i.mkdir(parents=True)
        except IOError as ose:
            print(f"The directory '{d_i}' could not be created: {ose}"
                  "Cancelling delivery. ")

            if TEMP_DIR.exists() and not isinstance(ose, FileExistsError):
                print("Deleting temporary directory.")
                try:
                    # Remove all prev created folders
                    shutil.rmtree(TEMP_DIR)
                    sys.exit("Temporary directory deleted. \n\n"
                             "----DELIVERY CANCELLED---\n")  # and quit
                except IOError as ose:
                    sys.exit(f"Could not delete directory {TEMP_DIR}: "
                             f"{ose}\n\n ----DELIVERY CANCELLED---\n")

                    return False, ()
            else:
                pass  # create log file here

    return True


def config_logger(filename: str):
    """Creates log file

    Args:
        filename:           Path to wished log file

    Returns:
        Logger:     Configured logger

    Raises:
        Exception:   Logging to file or console failed
    """

    logger = logging.getLogger(__name__)

    # Config file logger
    try:
        file_handler = logging.FileHandler(filename=filename)
        file_handler.setLevel(logging.DEBUG)
        fh_formatter = logging.Formatter("%(asctime)s::%(levelname)s::" +
                                         "%(name)s::%(lineno)d::%(message)s")
        file_handler.setFormatter(fh_formatter)
        logger.addHandler(file_handler)
    except OSError as ose:
        sys.exit(f"Logging to file failed: {ose}")

    # Config file logger
    try:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.CRITICAL)
        sh_formatter = logging.Formatter("%(levelname)s::%(name)s::" +
                                         "%(lineno)d::%(message)s")
        stream_handler.setFormatter(sh_formatter)
        logger.addHandler(stream_handler)
    except OSError as ose:
        sys.exit(f"Logging to console failed: {ose}")

    return logger

###############################################################################
# START - CREATE ############################################# START - CREATE #
###############################################################################


# Get current timestamp and delivery temporary folder name
TS = timestamp(folder=True)    # Timestamp
TEMP_DIR = pathlib.Path.cwd() / pathlib.Path(f"DataDelivery_{TS}")

# Subfolders
DIRS = tuple(TEMP_DIR / pathlib.Path(x)
             for x in ["", "files/", "meta/", "logs/"])

# Log file name
LOG_FILE = str(DIRS[-1] / pathlib.Path("ds.log"))
