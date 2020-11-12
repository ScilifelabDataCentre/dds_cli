# import csv
# from code_api.data_deliverer import timestamp
# import unittest
# import subprocess
# import sys
# import os
# import time
# from code_api.dp_exceptions import *
# from pathlib import Path

# correct_researcher_config = "configfile_researcher1.json"
# false_researcher_config = "configfile_researcher2.json"
# correct_facility_config = "configfile_facility1.json"
# false_facility_config = "configfile_facility2.json"

# any_username = "anyusername"
# correct_researcher = "researcher1"
# false_researcher = "researcher2"
# correct_facility = "facility1"
# false_facility = "facility2"

# any_password = "anypassword"
# correct_researcher_password = "Researcher1"
# false_researcher_password = "Researcher2"
# correct_facility_password = "Facility1"
# false_facility_password = "Facility2"

# any_project = "anyproject"
# correct_project = "0372838e2cf1f4a2b869974723002bb7"
# false_project = "0372838e2cf1f4a2b869974723002bb72"

# any_project_owner = "anyprojectowner"
# correct_project_owner = "1116e4785a1877d84c7c7e6e86008c1c"
# false_project_owner = "1116e4785a1877d84c7c7e6e86008c1c2"

# files_checksums = {
#     Path("../files/testfolder/testfile_05.fna"): "a255a94e1ec8309aff7321cc63f74c5f8a72a372a29fb3a70a3befcd84e95214",
#     Path("../files/testfolder/testfile_109.fna"): "b6e5f41561a44eb91c664461e1bd9ddd2332a3daa9ce619f08286d5f9f694370",
#     Path("../files/testfolder/testfile_1200.fna"): "700ef052c60dbc156965a1891111141ebf4c4c92ee09fadf5d3cccea688c1ecd",
#     Path("../files/testfolder/testfile_33000.fna"): "e661bd31be7096b1b240165b288601ce2c171221bf6108f3dd7f0d1a760bfaaa"
# }

# equal_files = {Path("../files/testfolder/testfile_33000_2.fna"): "e661bd31be7096b1b240165b288601ce2c171221bf6108f3dd7f0d1a760bfaaa",
#                Path("../files/testfolder/testfile_33000_3.fna"): "e661bd31be7096b1b240165b288601ce2c171221bf6108f3dd7f0d1a760bfaaa"}

# all_files = {**files_checksums, **equal_files}

# logfile = f"tests/test_{timestamp()}.csv"

# with open(logfile, 'w+') as csvfile:
#     writer = csv.writer(csvfile, delimiter=',')
#     writer.writerow(["Function", "One/multiple file(s)",
#                      "Size (MB)", "Time", "Speed (MB/s)"])


# class TimerError(Exception):
#     """A custom exception used to report errors in use of Timer class"""


# class Timer:

#     def __init__(self):
#         self._start_time = None

#     def start(self):
#         """Start a new timer"""

#         if self._start_time is not None:
#             raise TimerError(f"Timer is running. Use .stop() to stop it")

#         self._start_time = time.perf_counter()

#     def stop(self):
#         """Stop the timer, and report the elapsed time"""

#         if self._start_time is None:
#             raise TimerError(f"Timer is not running. Use .start() to start it")

#         elapsed_time = time.perf_counter() - self._start_time
#         self._start_time = None

#         return elapsed_time


# class PrintBlocker:

#     def __init__(self):
#         self._print_enabled = True

#     def blockPrint(self):
#         sys.stdout = open(os.devnull, 'w')
#         self._print_enabled = False

#     def enablePrint(self):
#         sys.stdout = sys.__stdout__


# class TestDpCli(unittest.TestCase):
#     '''Tests the different aspects of the Data Delivery Portal, 
#     including correct/false credentials, upload & download (with one, 
#     multiple files, and using the --data and --pathfile option), checksum
#     generation and verification. '''

#     def test_a_credentials(self):
#         '''Tries to log in to the DP with different credentials'''
#         print("Testing credentials...")

#         from code_api.data_deliverer import DataDeliverer

#         # Nothing
#         with self.assertRaises(DeliveryPortalException) as dpe:
#             DataDeliverer()
#         self.assertTrue("Delivery Portal login credentials not specified"
#                         in str(dpe.exception))

#         # Any username, only username
#         with self.assertRaises(DeliveryOptionException) as doe:
#             DataDeliverer(username=any_username)
#         self.assertTrue("Delivery Portal login credentials not specified"
#                         in str(doe.exception))

#         # Any password, only password
#         with self.assertRaises(DeliveryOptionException) as doe:
#             DataDeliverer(password=any_password)
#         self.assertTrue("Delivery Portal login credentials not specified"
#                         in str(doe.exception))

#         # Any project, only project
#         with self.assertRaises(DeliveryPortalException) as dpe:
#             DataDeliverer(project_id=any_project)
#         self.assertTrue("Delivery Portal login credentials not specified"
#                         in str(dpe.exception))

#         # Any owner, only owner
#         with self.assertRaises(DeliveryPortalException) as dpe:
#             DataDeliverer(project_owner=any_project_owner)
#         self.assertTrue("Delivery Portal login credentials not specified"
#                         in str(dpe.exception))

#         # Any username and password
#         with self.assertRaises(DeliveryOptionException) as doe:
#             DataDeliverer(username=any_username,
#                           password=any_password)
#         self.assertTrue("Project not specified" in str(doe.exception))

#         # Correct facility username and password
#         with self.assertRaises(DeliveryOptionException) as doe:
#             DataDeliverer(username=correct_facility,
#                           password=correct_facility_password)
#         self.assertTrue("Project not specified" in str(doe.exception))

#         # Correct facility username, password and project
#         with self.assertRaises(DeliveryOptionException) as doe:
#             def put():
#                 DataDeliverer(username=correct_facility,
#                               password=correct_facility_password,
#                               project_id=correct_project)
#             put()
#         self.assertTrue("Incorrect data owner" in str(doe.exception))

#         # Correct facility username, password and project. Incorrect owner.
#         with self.assertRaises(DeliveryOptionException) as doe:
#             def put():
#                 DataDeliverer(username=correct_facility,
#                               password=correct_facility_password,
#                               project_id=correct_project,
#                               project_owner=false_project_owner)
#             put()
#         self.assertTrue("Incorrect data owner" in str(doe.exception))

#         # Correct facility
#         with self.assertRaises(DeliveryPortalException) as dpe:
#             def put():
#                 DataDeliverer(username=correct_facility,
#                               password=correct_facility_password,
#                               project_id=correct_project,
#                               project_owner=correct_project_owner)
#             put()
#         self.assertTrue("No data to be uploaded" in str(dpe.exception))

#         # Correct researcher
#         with self.assertRaises(DeliveryPortalException) as dpe:
#             def get():
#                 DataDeliverer(username=correct_researcher,
#                               password=correct_researcher_password,
#                               project_id=correct_project)
#             get()
#         self.assertTrue("No data to be uploaded" in str(dpe.exception))

#         # Correct facility config
#         with self.assertRaises(DeliveryPortalException) as dpe:
#             def put():
#                 DataDeliverer(config=correct_facility_config)
#             put()
#         self.assertTrue("No data to be uploaded" in str(dpe.exception))

#         # Correct researcher config
#         with self.assertRaises(DeliveryPortalException) as dpe:
#             def get():
#                 DataDeliverer(config=correct_researcher_config)
#             get()
#         self.assertTrue("No data to be uploaded" in str(dpe.exception))

#         print("\tCredentials tested!")

#     def test_b_data(self):
#         '''Logs in and specifies data'''

#         print("Testing data collection...")

#         from code_api.data_deliverer import DataDeliverer
#         one_file = (str(list(files_checksums.keys())[0]), )
#         multiple_files = tuple(str(f) for f in files_checksums)

#         # Facility, single creds and --data option
#         try:
#             def put():
#                 DataDeliverer(username=correct_facility,
#                               password=correct_facility_password,
#                               project_id=correct_project,
#                               project_owner=correct_project_owner,
#                               data=one_file)
#             put()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Researcher, single creds and --data option
#         try:
#             def get():
#                 DataDeliverer(username=correct_researcher,
#                               password=correct_researcher_password,
#                               project_id=correct_project,
#                               data=one_file)
#             get()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Facility, config and --data option
#         try:
#             def put():
#                 DataDeliverer(config=correct_facility_config,
#                               data=one_file)
#             put()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Researcher, config and --data option
#         try:
#             def get():
#                 DataDeliverer(config=correct_researcher_config,
#                               data=one_file)
#             get()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Facility, single creds and multiple files in --data option
#         try:
#             def put():
#                 DataDeliverer(username=correct_facility,
#                               password=correct_facility_password,
#                               project_id=correct_project,
#                               project_owner=correct_project_owner,
#                               data=multiple_files)
#             put()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Researcher, single creds and multiple files in --data option
#         try:
#             def get():
#                 DataDeliverer(username=correct_researcher,
#                               password=correct_researcher_password,
#                               project_id=correct_project,
#                               data=multiple_files)
#             get()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Facility, config and multiple files in --data option
#         try:
#             def put():
#                 DataDeliverer(config=correct_facility_config,
#                               data=multiple_files)
#             put()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Researcher, config and multiple files in --data option
#         try:
#             def get():
#                 DataDeliverer(config=correct_researcher_config,
#                               data=multiple_files)
#             get()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Facility, single creds and --pathfile option
#         try:
#             def put():
#                 DataDeliverer(username=correct_facility,
#                               password=correct_facility_password,
#                               project_id=correct_project,
#                               project_owner=correct_project_owner,
#                               pathfile="test_pathfile.txt")
#             put()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Researcher, single creds and --pathfile option
#         try:
#             def get():
#                 DataDeliverer(username=correct_researcher,
#                               password=correct_researcher_password,
#                               project_id=correct_project,
#                               pathfile="test_pathfile.txt")
#             get()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Facility, config and --pathfile option
#         try:
#             def put():
#                 DataDeliverer(config=correct_facility_config,
#                               pathfile="test_pathfile.txt")
#             put()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         # Researcher, config and --pathfile option
#         try:
#             def get():
#                 DataDeliverer(config=correct_researcher_config,
#                               pathfile="test_pathfile.txt")
#             get()
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         print("\tData collection tested!")

#     def test_c_checksum(self):
#         '''Generates checksum and saves to file'''

#         print("Testing checksum generation...")

#         try:
#             from code_api.dp_crypto import gen_hmac
#             for f in files_checksums:
#                 test_timer = Timer()
#                 test_timer.start()
#                 checksum = gen_hmac(f)
#                 print_result(function="test_c_checksum",
#                              file=[f], stoptime=test_timer.stop())
#                 assert checksum == files_checksums[f]
#         except HashException as he:
#             self.fail(he)

#         print("\tChecksum generation tested!")

#     def test_d_upload(self):
#         '''Uploads to S3'''

#         print("Testing separate upload...")

#         for f in files_checksums:
#             test_timer2 = Timer()
#             test_timer2.start()
#             subprocess.run(["dp_cli", "put",
#                             "--username", f"{correct_facility}",
#                             "--password", f"{correct_facility_password}",
#                             "--project", f"{correct_project}",
#                             "--owner", f"{correct_project_owner}",
#                             "--data", f"{str(f)}"],
#                            stdout=subprocess.DEVNULL)
#             print_result(function="test_d_upload",
#                          file=[f], stoptime=test_timer2.stop())

#         print("\tUpload tested!")

#     def test_e_threaded_upload(self):
#         '''Uploads all files using threadpool'''

#         print("Testing threaded upload...")

#         from code_api.data_deliverer import DataDeliverer

#         # Facility config
#         command = ["dp_cli", "put",
#                    "--username", f"{correct_facility}",
#                    "--password", f"{correct_facility_password}",
#                    "--project", f"{correct_project}",
#                    "--owner", f"{correct_project_owner}"]

#         command1 = list(command)
#         for f in files_checksums:
#             for x in f"--data {f}".split():
#                 command1.append(x)
#         try:
#             test_timer3 = Timer()
#             test_timer3.start()
#             subprocess.run(command1)
#             print_result(function="test_e_threaded_upload",
#                          file=[f for f in files_checksums],
#                          stoptime=test_timer3.stop())
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         print("Testing threaded upload 2...")
#         command2 = list(command)
#         for f in equal_files:
#             for x in f"--data {f}".split():
#                 command2.append(x)
#         try:
#             test_timer4 = Timer()
#             test_timer4.start()
#             subprocess.run(command2)
#             print_result(function="test_e_threaded_upload",
#                          file=[f for f in equal_files],
#                          stoptime=test_timer4.stop())
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         print("\tThreaded upload tested!")

#     def test_f_download(self):
#         #     '''Downloads from S3'''

#         print("Testing download...")

#         from code_api.data_deliverer import DataDeliverer

#     #     # Research config
#         command = ["dp_cli", "get",
#                    "--username", f"{correct_researcher}",
#                    "--password", f"{correct_researcher_password}",
#                    "--project", f"{correct_project}"]

#         command1 = list(command)
#         for f in files_checksums:
#             for x in f"--data {f.name}".split():
#                 command1.append(x)

#         try:
#             test_timer5 = Timer()
#             test_timer5.start()
#             subprocess.run(command1)
#             print_result(function="test_f_download",
#                          file=[f for f in files_checksums],
#                          stoptime=test_timer5.stop())
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         print("Testing download 2...")
#         command2 = list(command)
#         for x in ["--data", "testfile_33000_2.fna",
#                   "--data", "testfile_33000_3.fna"]:
#             command2.append(x)

#         try:
#             test_timer6 = Timer()
#             test_timer6.start()
#             subprocess.run(command2)
#             print_result(function="test_f_download",
#                          file=["testfile_33000_2.fna", "testfile_33000_3.fna"],
#                          stoptime=test_timer6.stop())
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")
#         time.sleep(1)

#         print("\tDownload tested!")

#     def test_g_checksum_verification(self):
#         '''Verifies the downloaded files checksum'''

#         print("Testing checksum verification...")

#         latest = max([x for x in Path(".").glob("**")
#                       if x.match("DataDelivery*")], key=os.path.getmtime)

#         try:
#             from code_api.dp_crypto import gen_hmac
#             for p in (latest / Path("files")).glob("*"):
#                 filename = p.name
#                 checksum = gen_hmac(p)
#                 files_checksums.update(equal_files)
#                 for f in files_checksums:
#                     if f.name == filename:
#                         assert checksum == files_checksums[f]
#         except Exception as e:
#             self.fail(f"Test failed unexpectedly: {e}")

#         print("\tChecksum verification tested!")


# def print_result(function, file, stoptime):

#     size = 0        # Bytes
#     KB = 1024
#     MB = KB * 1024
#     GB = MB * 1024

#     for f in file:
#         print(f)
#         if isinstance(f, str):
#             print("string")
#             for x in all_files:
#                 print(x)
#                 if x.name == f:
#                     print(size)
#                     size += x.stat().st_size
#                     print(size)
#         else:
#             size += f.stat().st_size

#     size = size/MB

#     import csv
#     with open(logfile, 'a+') as csvfile:
#         writer = csv.writer(csvfile, delimiter=',')
#         writer.writerow([function,
#                          "M" if len(file) > 1 else "1",
#                          f"{size}",
#                          f"{stoptime}",
#                          f"{(size/stoptime):0.4f}"])


# if __name__ == "__main__":
#     unittest.main()
