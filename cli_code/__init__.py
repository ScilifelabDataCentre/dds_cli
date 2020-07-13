import collections
import datetime
import logging
import shutil
import sys

from pathlib import Path

__title__ = 'SciLifeLab Data Delivery System'
__version__ = '0.1'
__author__ = 'Ina Odén Österbo'
__author_email__ = 'ina.oden.osterbo@scilifelab.uu.se'
__license__ = 'MIT'
__all__ = ['DIRS', 'LOG_FILE']

PROG = 'ds_deliver'

LOG = logging.getLogger(__name__)
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

VERSION = 1
SEGMENT_SIZE = 65536
CIPHER_SEGMENT_SIZE = SEGMENT_SIZE + 16
MAX_CTR = (2**48) - 1

PRINT_ERR_S = "\nx x x x x x x x x x x x x x x x x x x x x x x x\n\n"
PRINT_ERR_E = "\n\nx x x x x x x x x x x x x x x x x x x x x x x x\n"
PRINT_ATT = "\n* * * * * * * * * * * * * * * * * * * * * * * *\n"

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


created, DIRS = create_directories()
if not created:
    raise OSError("Temporary directory could not be created. "
                  "Unable to continue delivery. Aborting. ")

LOG_FILE = str(DIRS[-1] / Path("ds.log"))
