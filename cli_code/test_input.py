"""Test script for the Data Delivery System CLI."""

# Imports
import pytest
import subprocess
import sys
import os

# Credentials
abs_path = os.getcwd() + "/tests/testing_october_2020/creds_files"

# Facilities
# Credential files
true_facility_creds = f"{abs_path}/creds_facility1_all_correct.json"
true_facility_uname = f"{abs_path}/creds_facility1_u.json"
true_facility_pw = f"{abs_path}/creds_facility1_p.json"
true_facility_uname_pw = f"{abs_path}/creds_facility1_u_p.json"
true_facility_uname_pw_proj = f"{abs_path}/creds_facility1_u_p_p.json"

# Credential options
true_facility_lc = {
    "username": "fac1_username",
    "password": "fac1_password",
    "project": "1",
    "owner": "1"
}

false_facility_lc = {
    "username": "fac1_usernaame",
    "password": "fac1_paassword",
    "project": "2",
    "owner": "2"
}

# Users
# Credential files
true_user_creds = f"{abs_path}/creds_user1_all_correct.json"
true_user_creds_wo = f"{abs_path}/creds_user1_all_correct_w_owner.json"
true_user_uname = f"{abs_path}/creds_user1_u.json"
true_user_pw = f"{abs_path}/creds_user1_p.json"
true_user_uname_pw = f"{abs_path}/creds_user1_u_p.json"

# Credentials options
true_user_lc = {
    "username": "username1",
    "password": "password1",
    "project": "1"
}

false_user_lc = {
    "username": "usernaame1",
    "password": "paasswoord1",
    "project": "2"
}

# Data
# Pathfiles
pathfile_path = os.getcwd() + "/tests/testing_october_2020/pathfiles"
pathfile_allfiles = f"{pathfile_path}/all_files.txt"

# Files - options
testfiles_path = "/Volumes/Seagate_Backup_Plus_Drive/Data_Delivery_System/Test-files"
file_17MB = f"{testfiles_path}/homo_sapiens_17MB.fna"
file_675MB = f"{testfiles_path}/homo_sapiens_675MB.fna"

# Tests


def test_no_creds():
    """Delivery should be cancelled if no creds."""

    # Delivery should quit if none of username, passwords, or creds are set
    test_proc_put = subprocess.run(["ds_deliver", "put"], capture_output=True)
    assert b"Delivery System login credentials not specified" in test_proc_put.stderr

    test_proc_get = subprocess.run(["ds_deliver", "get"], capture_output=True)
    assert b"Delivery System login credentials not specified" in test_proc_get.stderr


def test_creds_loose():
    """Delivery should be cancelled with the incorrect creds.

    Using --username, --password etc.
    """

    # Only username with put
    test_proc_put = subprocess.run(
        ["ds_deliver", "put", "--username", true_facility_lc["username"]],
        capture_output=True
    )
    assert b"Delivery System login credentials not specified" in test_proc_put.stderr

    # Only password with put
    test_proc_put = subprocess.run(
        ["ds_deliver", "put", "--password", true_facility_lc["password"]],
        capture_output=True
    )
    assert b"Delivery System login credentials not specified" in test_proc_put.stderr

    # No project id with put
    test_proc_put = subprocess.run(
        ["ds_deliver", "put", "--username", true_facility_lc["username"],
         "--password", true_facility_lc["password"]],
        capture_output=True
    )
    assert b"Project not specified" in test_proc_put.stderr

    # No project owner
    test_proc_put = subprocess.run(
        ["ds_deliver", "put", "--username", true_facility_lc["username"],
         "--password", true_facility_lc["password"], "--project",
         true_facility_lc["project"]], capture_output=True
    )
    assert b"You have not specified the project owner" in test_proc_put.stderr

    # Only username with get
    test_proc_get = subprocess.run(
        ["ds_deliver", "get", "--username", true_user_lc["username"]],
        capture_output=True
    )
    assert b"Delivery System login credentials not specified" in test_proc_get.stderr

    # Only password with get
    test_proc_get = subprocess.run(
        ["ds_deliver", "get", "--password", true_user_lc["password"]],
        capture_output=True
    )
    assert b"Delivery System login credentials not specified" in test_proc_get.stderr

    # No project id with get
    test_proc_get = subprocess.run(
        ["ds_deliver", "get", "--username", true_user_lc["username"],
         "--password", true_user_lc["password"]], capture_output=True
    )
    assert b"Project not specified" in test_proc_get.stderr


def test_creds_file():
    """Delivery should be cancelled if too few creds.

    Using --creds.
    """

    # Only username with put
    test_proc_put = subprocess.run(
        ["ds_deliver", "put", "--creds", true_facility_uname],
        capture_output=True
    )
    assert b"does not contain all required" in test_proc_put.stderr

    # Only password with put
    test_proc_put = subprocess.run(
        ["ds_deliver", "put", "--creds", true_facility_pw],
        capture_output=True
    )
    assert b"does not contain all required" in test_proc_put.stderr

    # No project id with put
    test_proc_put = subprocess.run(
        ["ds_deliver", "put", "--creds", true_facility_uname_pw],
        capture_output=True
    )
    assert b"does not contain all required" in test_proc_put.stderr

    # No project owner
    test_proc_put = subprocess.run(
        ["ds_deliver", "put", "--creds", true_facility_uname_pw_proj],
        capture_output=True
    )
    assert b"Project owner not specified" in test_proc_put.stderr

    # Only username with get
    test_proc_put = subprocess.run(
        ["ds_deliver", "get", "--creds", true_user_uname],
        capture_output=True
    )
    assert b"does not contain all required" in test_proc_put.stderr

    # Only password with get
    test_proc_put = subprocess.run(
        ["ds_deliver", "get", "--creds", true_user_pw],
        capture_output=True
    )
    assert b"does not contain all required" in test_proc_put.stderr

    # No project id with get
    test_proc_put = subprocess.run(
        ["ds_deliver", "get", "--creds", true_user_uname_pw],
        capture_output=True
    )
    assert b"does not contain all required" in test_proc_put.stderr


def test_incorrect_creds():
    """Facility should deny access if incorrect creds"""

    # put with user creds
    test_put = subprocess.run(
        ["ds_deliver", "put", "--creds", true_user_creds_wo],
        capture_output=True
    )
    assert b"Delivery System access denied" in test_put.stderr
    assert b"The user does not exist" in test_put.stderr

    # put with loose user creds
    test_put = subprocess.run(
        ["ds_deliver", "put", "--username", true_user_lc["username"],
         "--password", true_user_lc["password"], "--project",
         true_user_lc["project"], "--owner", true_user_lc["username"]],
        capture_output=True
    )
    assert b"Delivery System access denied" in test_put.stderr
    assert b"The user does not exist" in test_put.stderr

    # put with loose user creds and data
    test_put = subprocess.run(
        ["ds_deliver", "put", "--username", true_user_lc["username"],
         "--password", true_user_lc["password"], "--project",
         true_user_lc["project"], "--owner", true_user_lc["username"],
         "--data", file_17MB],
        capture_output=True
    )
    assert b"Delivery System access denied" in test_put.stderr
    assert b"The user does not exist" in test_put.stderr

    # get with facility creds
    test_get = subprocess.run(
        ["ds_deliver", "get", "--creds", true_facility_creds],
        capture_output=True
    )
    assert b"Delivery System access denied" in test_get.stderr
    assert b"The user does not exist" in test_get.stderr

    # get with loose facility creds
    test_get = subprocess.run(
        ["ds_deliver", "get", "--username", true_facility_lc["username"],
         "--password", true_facility_lc["password"], "--project",
         true_facility_lc["project"]],
        capture_output=True
    )
    assert b"Delivery System access denied" in test_get.stderr
    assert b"The user does not exist" in test_get.stderr


def test_data_file():
    """Use a file containing file paths to specify files and folders"""

    # Multiple files in pathfile
    test_put = subprocess.run(
        ["ds_deliver", "put", "--creds", true_facility_creds,
         "--pathfile", f"{pathfile_path}/all_files.txt"],
        capture_output=True
    )
    print(test_put.stderr, flush=True)
    assert test_put.stderr == b""

    # Multiple files defined in option
    test_put = subprocess.run(
        ["ds_deliver", "put", "--creds", true_facility_creds,
         "--data", file_17MB, "--data", file_675MB], capture_output=True
    )
    print(test_put.stderr, flush=True)
    assert test_put.stderr == b""


def textfile_put():
    import pathlib
    from time import process_time_ns, sleep
    import csv

    test_dir = pathlib.Path(testfiles_path)
    print(test_dir)

    file_dict = {}
    test_dir_files = list(test_dir.glob("testfile_1.txt"))
    print(sorted(test_dir_files))

    for f in sorted(test_dir_files):
        fsize = f.stat().st_size
        start = process_time_ns()
        put_process = subprocess.run(
            ["ds_deliver", "put", "--creds", true_facility_creds,
             "--data", str(f)], capture_output=True
        )
        stop = process_time_ns()
        file_dict[fsize] = stop-start
        sleep(10)

    # import matplotlib.pylab as plt
    print(file_dict)
    # x, y = zip(*sorted(file_dict.items()))
    # print(x)
    # print(y)
    # with open("textfile_timings.csv", mode="w") as csv_file:
    #     csv_writer = csv.writer(csv_file, delimiter=",",
    #                             quotechar="'", quoting=csv.QUOTE_MINIMAL)
    #     csv_writer.writerow(x)
    #     csv_writer.writerow(y)
    # plt.plot(x, y)
    # plt.show()


def create_csv():
    import datetime as dt

    time_dict = {1048585: (dt.datetime(2020, 10, 20, 20, 18, 17) -
                           dt.datetime(2020, 10, 20, 20, 18, 16)).total_seconds(),  # 1
                 1073750017: (dt.datetime(2020, 10, 20, 15, 45, 21) -
                              dt.datetime(2020, 10, 20, 15, 44, 3)).total_seconds(),   # 1024
                 134218753: (dt.datetime(2020, 10, 20, 15, 45, 42) -
                             dt.datetime(2020, 10, 20, 15, 45, 31)).total_seconds(),    # 128
                 16777345: (dt.datetime(2020, 10, 20, 15, 45, 56) -
                            dt.datetime(2020, 10, 20, 15, 45, 52)).total_seconds(),     # 16
                 17180000257: (dt.datetime(2020, 10, 20, 16, 6, 26) -
                               dt.datetime(2020, 10, 20, 15, 46, 7)).total_seconds(),  # 16384
                 2097169: (dt.datetime(2020, 10, 20, 16, 6, 37) -
                           dt.datetime(2020, 10, 20, 16, 6, 36)).total_seconds(),            # 2
                 2147500033: (dt.datetime(2020, 10, 20, 16, 9, 21) -
                              dt.datetime(2020, 10, 20, 16, 6, 48)).total_seconds(),   # 2048
                 268437505: (dt.datetime(2020, 10, 20, 16, 9, 52) -
                             dt.datetime(2020, 10, 20, 16, 9, 32)).total_seconds(),    # 256
                 33554689: (dt.datetime(2020, 10, 20, 16, 10, 6) -
                            dt.datetime(2020, 10, 20, 16, 10, 3)).total_seconds(),     # 32
                 34360000513: (dt.datetime(2020, 10, 20, 16, 51, 1) -
                               dt.datetime(2020, 10, 20, 16, 10, 16)).total_seconds(),  # 32768
                 4194337: (dt.datetime(2020, 10, 20, 16, 51, 14) -
                           dt.datetime(2020, 10, 20, 16, 51, 12)).total_seconds(),      # 4
                 4295000065: (dt.datetime(2020, 10, 20, 16, 56, 31) -
                              dt.datetime(2020, 10, 20, 16, 51, 24)).total_seconds(),   # 4096
                 536875009: (dt.datetime(2020, 10, 20, 16, 57, 21) -
                             dt.datetime(2020, 10, 20, 16, 56, 41)).total_seconds(),    # 512
                 67109377: (dt.datetime(2020, 10, 20, 16, 57, 37) -
                            dt.datetime(2020, 10, 20, 16, 57, 31)).total_seconds(),     # 64
                 68720001025: (dt.datetime(2020, 10, 20, 18, 19, 13) -
                               dt.datetime(2020, 10, 20, 16, 57, 47)).total_seconds(),  # 65536
                 8388673: (dt.datetime(2020, 10, 20, 18, 19, 25) -
                           dt.datetime(2020, 10, 20, 18, 19, 24)).total_seconds(),      # 8
                 8590000129: (dt.datetime(2020, 10, 20, 18, 29, 47) -
                              dt.datetime(2020, 10, 20, 18, 19, 36)).total_seconds()}   # 8192
    # x = (1048585, 2097169, 4194337, 8388673, 16777345, 33554689, 67109377,
    #      134218753, 268437505, 536875009, 1073750017, 2147500033,
    #      4295000065, 8590000129, 17180000257, 34360000513, 68720001025)
    # y = (1784000, 6578000, 7738000, 6586000, 2297000, 3164000, 3400000,
    #      6378000, 4008000, 4506000, 6449000, 2211000, 3629000, 5124000,
    #      7600000, 5573000, 7913000)
    print(sorted(time_dict.items()))
    import csv
    with open("tests/testing_october_2020/textfile_timings.csv", mode="w") \
            as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=",", quotechar="'",
                                quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(["size", "size_exact", "size_mb_exact",
                             "time_s", "mb_per_s"])
        size = 1
        for x, y in sorted(time_dict.items()):
            # size = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096,
            #         8192, 16384, 32768, 65536]
            size_mb = x/1000000
            mb_per_s = size_mb/y
            csv_writer.writerow([size, x, size_mb, y, mb_per_s])
            size = size * 2
        # csv_writer.writerow(x)
        # csv_writer.writerow(y)


# TODO (ina): Data AND wrong creds -- doesn't continue??
if __name__ == "__main__":
    # textfile_put()
    create_csv()
