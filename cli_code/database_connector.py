"""
Establishes database connection for Data Delivery System
"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging

# Installed
import couchdb

# Own modules
from cli_code.exceptions_ds import CouchDBException

###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################

DB_LOG = logging.getLogger(__name__)
DB_LOG.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class DatabaseConnector():
    '''Performs database-related operations

    Args:
            db_name (str):  Name of database to connect to. If None connect
                            to entire instance.

    Attributes:
        db_name:    DB connected to

    Raises:
        CouchDBException:   Database login failed

    '''

    def __init__(self, db_name=None):
        '''Initializes the db connection.


        '''

        self.db_name = db_name  # DB name to connect to
        # DB_LOG.debug(f"Connecting to database {self.db_name}")

        try:
            self.conn = couchdb.Server(
                f'http://delport:delport@localhost:5984/'
            )
        except CouchDBException as cdbe:
            DB_LOG.exception(f"Database login failed. {cdbe}")

        # DB_LOG.info("Database connection successful.")

    def __enter__(self):
        '''Connects to database.

        Returns:
            Connection to database - entire instance or specific db

        '''

        # Connect to entire instance
        if self.db_name is None:
            # DB_LOG.debug("Connecting to CouchDB. No specific DB name.")
            return self.conn

        # Error if db doesn't exist
        if self.db_name not in self.conn:
            raise CouchDBException(f"The database {self.db_name} does "
                                   "not exist in the couchDB instance.")

        # Connect to specific DB
        return self.conn[self.db_name]

    def __exit__(self, exc_type, exc_value, tb):
        '''Allows for implementation using "with" statement.
        Tear it down. Delete class.'''

        if exc_type is not None:
            # traceback.print_exception(exc_type, exc_value, tb)
            DB_LOG.warning("DatabaseConnector error!"
                           f"{exc_type, exc_value, tb}")
            return False  # uncomment to pass exception through
        else:
            self.conn = None

        # DB_LOG.debug(f"DatabaseConnector teared down: {self.conn == None}")
        return True
