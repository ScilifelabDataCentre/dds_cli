import couchdb
import traceback


class DatabaseConnector():

    def __init__(self, db_name=None):
        '''Initializes the db connection'''

        self.db_name = db_name
        try:
            self.conn = couchdb.Server(
                f'http://delport:delport@localhost:5984/')
        except CouchDBException as cdbe:
            sys.exit(f"Database login failed. {cdbe}")

    def __enter__(self):
        '''Connects to database.
        Currently hard-coded. '''

        if self.db_name is None:
            return self.conn

        if self.db_name not in self.conn:
            raise CouchDBException(f"The database {self.db_name} does "
                                    "not exist in the couchDB instance.")
        return self.conn[self.db_name]

    def __exit__(self, exc_type, exc_value, tb):
        '''Allows for implementation using "with" statement.
        Tear it down. Delete class.'''

        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through
        else:
            self.conn = None

        return True
