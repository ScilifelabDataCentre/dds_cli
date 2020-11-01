"""Data Handler, used by the Data Delivery System CLI.

Handles the login of users, and either lists or deletes data delivered with
the Data Delivery System.
"""


class DataHandler:

    def __init__(self, creds=None, username=None, password=None,
                 project_id=None, level=None):
        pass
    
    def list_projects(self):
        pass

    def list_files(self, project):
        pass

    def delete_files(self, project, files):
        pass 