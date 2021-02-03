""""""
###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard Library
import logging
import sys

# Installed

# Own modules


def log_to_file(logger, filename: str):
    """"""
    
    # Config file logger
    try:
        file_handler = logging.FileHandler(filename=filename)
        fh_formatter = logging.Formatter("%(asctime)s::%(levelname)s::" +
                                         "%(name)s::%(lineno)d::%(message)s")
        file_handler.setFormatter(fh_formatter)
        logger.addHandler(file_handler)
    except OSError as ose:
        sys.exit(f"Logging to file failed: {ose}")
    
    return logger

def log_to_terminal(logger):
    """"""

    # Config file logger
    try:
        stream_handler = logging.StreamHandler()
        sh_formatter = logging.Formatter("%(levelname)s::%(name)s::" +
                                         "%(lineno)d::%(message)s")
        stream_handler.setFormatter(sh_formatter)
        logger.addHandler(stream_handler)
    except OSError as ose:
        sys.exit(f"Logging to console failed: {ose}")

    return logger
