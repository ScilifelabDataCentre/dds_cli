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

VERSION = 1
SEGMENT_SIZE = 65536


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

    TemporaryDirectories = collections.namedtuple('TemporaryDirectories',
                                                  'root files meta logs')
    dirs = TemporaryDirectories(root=temp_dir / Path(""),
                                files=temp_dir / Path("files/"),
                                meta=temp_dir / Path("meta/"),
                                logs=temp_dir / Path("logs/"))

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

LOG_FILE = str(DIRS.logs / Path("ds.log"))
