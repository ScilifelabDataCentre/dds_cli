import unittest
import subprocess
from code_api.dp_exceptions import *


class TestDpCli(unittest.TestCase):
    '''Tests the different aspects of the Data Delivery Portal, 
    including correct/false credentials, upload & download (with one, 
    multiple files, and using the --data and --pathfile option), checksum
    generation and verification. '''

    def test_credentials(self):
        '''Tries to log in to the DP with different credentials'''

        self.correct_researcher_config = "configfile_researcher1.json"
        self.false_researcher_config = "configfile_researcher2.json"
        self.correct_facility_config = "configfile_facility1.json"
        self.false_facility_config = "configfile_facility2.json"
        self.any_username = "anyusername"
        self.correct_researcher = "researcher1"
        self.false_researcher = "researcher2"
        self.correct_facility = "facility1"
        self.false_facility = "facility2"
        self.any_password = "anypassword"
        self.correct_researcher_password = "Researcher1"
        self.false_researcher_password = "Researcher2"
        self.correct_facility_password = "Facility1"
        self.false_facility_password = "Facility2"
        self.any_project = "anyproject"
        self.correct_project = "0372838e2cf1f4a2b869974723002bb7"
        self.false_project = "0372838e2cf1f4a2b869974723002bb72"
        self.any_project_owner = "anyprojectowner"
        self.correct_project_owner = "1116e4785a1877d84c7c7e6e86008c1c"
        self.false_project_owner = "1116e4785a1877d84c7c7e6e86008c1c2"

        from code_api.data_deliverer import DataDeliverer

        # Nothing
        with self.assertRaises(DeliveryPortalException) as dpe:
            DataDeliverer()
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(dpe.exception))

        # Any username, only username
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(username=self.any_username)
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(doe.exception))

        # Any password, only password
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(password=self.any_password)
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(doe.exception))

        # Any project, only project
        with self.assertRaises(DeliveryPortalException) as dpe:
            DataDeliverer(project_id=self.any_project)
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(dpe.exception))

        # Any owner, only owner
        with self.assertRaises(DeliveryPortalException) as dpe:
            DataDeliverer(project_owner=self.any_project_owner)
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(dpe.exception))

        # Any username and password
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(username=self.any_username,
                          password=self.any_password)
        self.assertTrue("Project not specified" in str(doe.exception))

        # Correct facility username and password
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(username=self.correct_facility,
                          password=self.correct_facility_password)
        self.assertTrue("Project not specified" in str(doe.exception))

        # Correct facility username, password and project
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(username=self.correct_facility,
                          password=self.correct_facility_password,
                          project_id=self.correct_project)
        self.assertTrue("Method error." in str(doe.exception))

        # Correct facility username, password and project. Incorrect owner.
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(username=self.correct_facility,
                          password=self.correct_facility_password,
                          project_id=self.correct_project,
                          project_owner=self.false_project_owner)
        self.assertTrue("Method error." in str(doe.exception))

        # Correct facility
        with self.assertRaises(DeliveryOptionException) as dpe:
            DataDeliverer(username=self.correct_facility,
                          password=self.correct_facility_password,
                          project_id=self.correct_facility_password,
                          project_owner=self.correct_project_owner)
        self.assertTrue("Method error." in str(dpe.exception))

        # Correct researcher
        with self.assertRaises(DeliveryOptionException) as dpe:
            DataDeliverer(username=self.correct_researcher,
                          password=self.correct_researcher_password,
                          project_id=self.correct_researcher_password)
        self.assertTrue("Method error." in str(dpe.exception))

        # Correct facility config
        with self.assertRaises(DeliveryOptionException) as dpe:
            DataDeliverer(config=self.correct_facility_config)
        self.assertTrue("Method error." in str(dpe.exception))

        # Correct researcher config
        with self.assertRaises(DeliveryOptionException) as dpe:
            DataDeliverer(config=self.correct_researcher_config)
        self.assertTrue("Method error." in str(dpe.exception))

    def test_checksum(self):
        '''Generates checksum'''

        pass

    def test_upload(self):
        '''Uploads to S3'''

        pass

    def test_download(self):
        '''Downloads from S3'''

        pass

    def test_checksum_verification(self):
        '''Verifies the downloaded files checksum'''

        pass


if __name__ == "__main__":
    unittest.main()
