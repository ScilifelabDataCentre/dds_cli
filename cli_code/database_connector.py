import couchdb
import logging
import traceback

from cli_code import LOG_FILE
from cli_code.file_handler import config_logger
from cli_code.exceptions_ds import CouchDBException

DB_LOG = logging.getLogger(__name__)
DB_LOG.setLevel(logging.DEBUG)

DB_LOG = config_logger(
    logger=DB_LOG, filename=LOG_FILE,
    file=True, file_setlevel=logging.DEBUG,
    fh_format="%(asctime)s::%(levelname)s::" +
    "%(name)s::%(lineno)d::%(message)s",
    stream=True, stream_setlevel=logging.DEBUG,
    sh_format="%(levelname)s::%(name)s::" +
    "%(lineno)d::%(message)s"
)


class DatabaseConnector():

    def __init__(self, db_name=None):
        '''Initializes the db connection.

        Args:
            db_name (str):  Name of database to connect to. If None connect
                            to entire instance.
        '''

        self.db_name = db_name
        # DB_LOG.debug(f"Connecting to database {self.db_name}")
        try:
            self.conn = couchdb.Server(
                f'http://delport:delport@localhost:5984/'
            )
        except CouchDBException as cdbe:
            DB_LOG.exception(f"Database login failed. {cdbe}")
        else:
            pass
            # DB_LOG.info("Database connection successful.")

    def __enter__(self):
        '''Connects to database. '''

        if self.db_name is None:
            # DB_LOG.debug("Connecting to CouchDB. No specific DB name.")
            return self.conn

        if self.db_name not in self.conn:
            DB_LOG.exception(f"The database {self.db_name} does "
                             "not exist in the couchDB instance.")
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
