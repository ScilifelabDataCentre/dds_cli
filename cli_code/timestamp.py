""""""


###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import datetime


class TimeStamp:

    def __init__(self):
        
        sep_date_time = "_"
        sep_time = "-"

        now = datetime.datetime.now()
        self.timestamp = ""

        for t in (now.year, "-", now.month, "-", now.day, sep_date_time,
                  now.hour, sep_time, now.minute, sep_time, now.second):
            if len(str(t)) == 1 and isinstance(t, int):
                self.timestamp += f"0{t}"
            else:
                self.timestamp += f"{t}"
            
# print(TimeStamp())