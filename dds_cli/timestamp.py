""""""


###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime
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


class TimeStamp:
    def __init__(self):

        self.sep_date_time = "_"
        self.sep_time = "-"

        now = datetime.datetime.now()
        self.timestamp = ""

        for t in (
            now.year,
            self.sep_time,
            now.month,
            self.sep_time,
            now.day,
            self.sep_date_time,
            now.hour,
            self.sep_time,
            now.minute,
            self.sep_time,
            now.second,
        ):
            if len(str(t)) == 1 and isinstance(t, int):
                self.timestamp += f"0{t}"
            else:
                self.timestamp += f"{t}"
