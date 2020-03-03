import unittest
import subprocess
import sys
from code_api.dp_exceptions import *
from pathlib import Path

correct_researcher_config = "configfile_researcher1.json"
false_researcher_config = "configfile_researcher2.json"
correct_facility_config = "configfile_facility1.json"
false_facility_config = "configfile_facility2.json"

any_username = "anyusername"
correct_researcher = "researcher1"
false_researcher = "researcher2"
correct_facility = "facility1"
false_facility = "facility2"

any_password = "anypassword"
correct_researcher_password = "Researcher1"
false_researcher_password = "Researcher2"
correct_facility_password = "Facility1"
false_facility_password = "Facility2"

any_project = "anyproject"
correct_project = "0372838e2cf1f4a2b869974723002bb7"
false_project = "0372838e2cf1f4a2b869974723002bb72"

any_project_owner = "anyprojectowner"
correct_project_owner = "1116e4785a1877d84c7c7e6e86008c1c"
false_project_owner = "1116e4785a1877d84c7c7e6e86008c1c2"

files_checksums = {
    Path("../files/testfolder/testfile_05.fna"): "a255a94e1ec8309aff7321cc63f74c5f8a72a372a29fb3a70a3befcd84e95214",
    Path("../files/testfolder/testfile_109.fna"): "b6e5f41561a44eb91c664461e1bd9ddd2332a3daa9ce619f08286d5f9f694370",
    Path("../files/testfolder/testfile_1200.fna"): "700ef052c60dbc156965a1891111141ebf4c4c92ee09fadf5d3cccea688c1ecd",
    Path("../files/testfolder/testfile_33000.fna"): "e661bd31be7096b1b240165b288601ce2c171221bf6108f3dd7f0d1a760bfaaa"
}


class TestDpCli(unittest.TestCase):
    '''Tests the different aspects of the Data Delivery Portal, 
    including correct/false credentials, upload & download (with one, 
    multiple files, and using the --data and --pathfile option), checksum
    generation and verification. '''

    def test_credentials(self):
        '''Tries to log in to the DP with different credentials'''

        from code_api.data_deliverer import DataDeliverer

        # Nothing
        with self.assertRaises(DeliveryPortalException) as dpe:
            DataDeliverer()
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(dpe.exception))

        # Any username, only username
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(username=any_username)
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(doe.exception))

        # Any password, only password
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(password=any_password)
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(doe.exception))

        # Any project, only project
        with self.assertRaises(DeliveryPortalException) as dpe:
            DataDeliverer(project_id=any_project)
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(dpe.exception))

        # Any owner, only owner
        with self.assertRaises(DeliveryPortalException) as dpe:
            DataDeliverer(project_owner=any_project_owner)
        self.assertTrue("Delivery Portal login credentials not specified"
                        in str(dpe.exception))

        # Any username and password
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(username=any_username,
                          password=any_password)
        self.assertTrue("Project not specified" in str(doe.exception))

        # Correct facility username and password
        with self.assertRaises(DeliveryOptionException) as doe:
            DataDeliverer(username=correct_facility,
                          password=correct_facility_password)
        self.assertTrue("Project not specified" in str(doe.exception))

        # Correct facility username, password and project
        with self.assertRaises(DeliveryOptionException) as doe:
            def put():
                DataDeliverer(username=correct_facility,
                              password=correct_facility_password,
                              project_id=correct_project)
            put()
        self.assertTrue("Incorrect data owner" in str(doe.exception))

        # Correct facility username, password and project. Incorrect owner.
        with self.assertRaises(DeliveryOptionException) as doe:
            def put():
                DataDeliverer(username=correct_facility,
                              password=correct_facility_password,
                              project_id=correct_project,
                              project_owner=false_project_owner)
            put()
        self.assertTrue("Incorrect data owner" in str(doe.exception))

        # Correct facility
        with self.assertRaises(DeliveryPortalException) as dpe:
            def put():
                DataDeliverer(username=correct_facility,
                              password=correct_facility_password,
                              project_id=correct_project,
                              project_owner=correct_project_owner)
            put()
        self.assertTrue("No data to be uploaded" in str(dpe.exception))

        # Correct researcher
        with self.assertRaises(DeliveryPortalException) as dpe:
            def get():
                DataDeliverer(username=correct_researcher,
                              password=correct_researcher_password,
                              project_id=correct_project)
            get()
        self.assertTrue("No data to be uploaded" in str(dpe.exception))

        # Correct facility config
        with self.assertRaises(DeliveryPortalException) as dpe:
            def put():
                DataDeliverer(config=correct_facility_config)
            put()
        self.assertTrue("No data to be uploaded" in str(dpe.exception))

        # Correct researcher config
        with self.assertRaises(DeliveryPortalException) as dpe:
            def get():
                DataDeliverer(config=correct_researcher_config)
            get()
        self.assertTrue("No data to be uploaded" in str(dpe.exception))

    def test_data(self):
        '''Logs in and specifies data'''

        from code_api.data_deliverer import DataDeliverer
        one_file = (str(list(files_checksums.keys())[0]), )
        multiple_files = tuple(str(f) for f in files_checksums)

        print("one file: ", one_file)
        print("multiple files: ", multiple_files)

        # Facility, single creds and --data option
        try:
            def put():
                DataDeliverer(username=correct_facility,
                              password=correct_facility_password,
                              project_id=correct_project,
                              project_owner=correct_project_owner,
                              data=one_file)
            put()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Researcher, single creds and --data option
        try:
            def get():
                DataDeliverer(username=correct_researcher,
                              password=correct_researcher_password,
                              project_id=correct_project,
                              data=one_file)
            get()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Facility, config and --data option
        try:
            def put():
                DataDeliverer(config=correct_facility_config,
                              data=one_file)
            put()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Researcher, config and --data option
        try:
            def get():
                DataDeliverer(config=correct_researcher_config,
                              data=one_file)
            get()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Facility, single creds and multiple files in --data option
        try:
            def put():
                DataDeliverer(username=correct_facility,
                              password=correct_facility_password,
                              project_id=correct_project,
                              project_owner=correct_project_owner,
                              data=multiple_files)
            put()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Researcher, single creds and multiple files in --data option
        try:
            def get():
                DataDeliverer(username=correct_researcher,
                              password=correct_researcher_password,
                              project_id=correct_project,
                              data=multiple_files)
            get()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Facility, config and multiple files in --data option
        try:
            def put():
                DataDeliverer(config=correct_facility_config,
                              data=multiple_files)
            put()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Researcher, config and multiple files in --data option
        try:
            def get():
                DataDeliverer(config=correct_researcher_config,
                              data=multiple_files)
            get()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Facility, single creds and --pathfile option
        try:
            def put():
                DataDeliverer(username=correct_facility,
                              password=correct_facility_password,
                              project_id=correct_project,
                              project_owner=correct_project_owner,
                              pathfile="test_pathfile.txt")
            put()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Researcher, single creds and --pathfile option
        try:
            def get():
                DataDeliverer(username=correct_researcher,
                              password=correct_researcher_password,
                              project_id=correct_project,
                              pathfile="test_pathfile.txt")
            get()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Facility, config and --pathfile option
        try:
            def put():
                DataDeliverer(config=correct_facility_config,
                              pathfile="test_pathfile.txt")
            put()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

        # Researcher, config and --pathfile option
        try:
            def get():
                DataDeliverer(config=correct_researcher_config,
                              pathfile="test_pathfile.txt")
            get()
        except Exception as e:
            self.fail(f"Test failed unexpectedly: {e}")

    # def test_checksum(self):
    #     '''Generates checksum and saves to file'''

    #     try:
    #         from code_api.dp_crypto import gen_hmac
    #         for f in files_checksums:
    #             checksum = gen_hmac(f)
    #             print(
    #                 f"{checksum}, {files_checksums[f]}, {checksum == files_checksums[f]}")
    #             assert checksum == files_checksums[f]
    #     except HashException as he:
    #         self.fail(he)

    # def test_upload(self):
    #     '''Uploads to S3'''

    #     for f in files_checksums:
    #         subprocess.run(["dp_cli", "put",
    #                         "--username", f"{correct_facility}",
    #                         "--password", f"{correct_facility_password}",
    #                         "--project", f"{correct_project}",
    #                         "--owner", f"{correct_project_owner}",
    #                         "--data", f"{str(f)}"],
    #                         stdout=subprocess.DEVNULL)

    def test_multiple_upload(self):
        '''Uploads all files using threadpool'''

        files = tuple(f for f in files_checksums)

    def test_download(self):
        '''Downloads from S3'''

        pass

    def test_checksum_verification(self):
        '''Verifies the downloaded files checksum'''

        # finalized = file_hash.finalize().hex()
        # if upload:

        # else:
        #     try:
        #         with open(file="checksum.txt", mode='r') as cf:
        #             original = cf.read()
        #             [print("SUCCESS!" if original == finalized
        #                     else print("FAILED CHECKSUM VERIFICATION!"))]
        #     except IOError as ioe2:
        #         sys.exit("Could not read hash from file.")

        pass


if __name__ == "__main__":
    unittest.main()
