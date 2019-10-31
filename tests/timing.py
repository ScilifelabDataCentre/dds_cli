"""Script used for timing different parts of the dp api."""

# IMPORTS ########################################################### IMPORTS #

import os
import sys
import dp_cli as dp_cli
import time
import datetime
import csv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import queue
import threading

import paramiko


# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

FILESDIR = "/Volumes/Seagate_Backup_Plus_Drive/Delivery_Portal/api/Files/"
TESTDIR = "/Users/inaod568/repos/dp_api/tests/"
FIGDIR = "/Volumes/Seagate_Backup_Plus_Drive/Delivery_Portal/api/Figures/"
kibibytes = 1024

hostname = ""
port = 22
username = ""
password = ""

# CLASSES ########################################################### CLASSES #


class FileException(Exception):
    """Custom exception class for handling file-related errors such as
    deleting files, creating files, etc."""

    def __init__(self, msg: str):
        """Passes message from exception call to the base class __init__."""

        super().__init__(msg)


class TimingException(Exception):
    """Custom exception class for handling errors occurring during
    timing of operations and handling of timing variables."""

    def __init__(self, msg: str):
        """Passes message from exception call to the base class __init__."""

        super().__init__(msg)


# FUNCTIONS ####################################################### FUNCTIONS #

def remove_files(encrypted: str, decrypted: str):
    """Remove encrypted and decrypted files if they exist"""

    for file in [encrypted, decrypted]:
        try:
            if os.path.exists(file):
                os.remove(file)
        except FileException:
            print(f"Could not remove file: {file}")


def create_csv_file(filename: str, *args, **kwargs):
    """Create timings file if doesn't exist"""

    if not os.path.exists(filename):
        try:
            with open(filename, mode="w") as cf:
                writer = csv.writer(cf)
                headers = ["Chunk_kibibytes", "File_size_MB",
                           "Checksum", "Checksum_MB/s",
                           "Encryption", "Encryption_MB/s",
                           "Decryption", "Decryption_MB/s",
                           "Upload", "Upload_MB/s",
                           "Download", "Download_MB/s"]
                writer.writerow(headers)
        except FileException:
            print("The csv file could not be created.")
    else:
        try:
            hash_elapsed_time_ns = kwargs.get('hashtime', None)
            encryption_elapsed_time_ns = kwargs.get('enctime', None)
            decryption_elapsed_time_ns = kwargs.get('dectime', None)
            upload_elapsed_time_ns = kwargs.get('uptime', None)
            download_elapsed_time_ns = kwargs.get('downtime', None)
            chunk_size = kwargs.get('chunk', None)
            filesize_mb = kwargs.get('size', None)
        except TimingException:
            print("Could not save operation timing values to file, "
                  "Variables not available.")

        with open(filename, mode="a") as csvfile:
            writer = csv.writer(csvfile)
            hash_elapsed_time_s = hash_elapsed_time_ns/1e9
            encryption_elapsed_time_s = encryption_elapsed_time_ns/1e9
            decryption_elapsed_time_s = decryption_elapsed_time_ns/1e9
            upload_elapsed_time_s = upload_elapsed_time_ns/1e9
            download_elapsed_time_s = download_elapsed_time_ns/1e9
            row = [chunk_size,
                   filesize_mb,
                   hash_elapsed_time_s,
                   filesize_mb/hash_elapsed_time_s,
                   encryption_elapsed_time_s,
                   filesize_mb/encryption_elapsed_time_s,
                   decryption_elapsed_time_s,
                   filesize_mb/decryption_elapsed_time_s,
                   upload_elapsed_time_s,
                   filesize_mb/upload_elapsed_time_s,
                   download_elapsed_time_s,
                   filesize_mb/download_elapsed_time_s]
            writer.writerow(row)


def time_upload(filename: str, chunk: int) -> int:
    """Time transfer to server"""

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(hostname=hostname,
                   port=port, username=username,
                   password=password)

    upload_t = time.process_time_ns()

    sftp = client.open_sftp()
    # lägg till buffer?
    # TRY "SETTIMEOUT?"
    with open(filename, "rb") as f:
        with sftp.file("testing.txt", "ab") as nf:
            for chunk in iter(lambda: f.read(chunk*kibibytes), b''):
                nf.write(chunk)
                nf.flush()

    # sftp = client.open_sftp()
    # result = sftp.put(localpath=filename,remotepath="testing.txt") # Reads 32768 bytes at a time 
    # print(result)

    return (time.process_time_ns() - upload_t), client


def time_download(chunk: int) -> int:
    """Time transfer from server"""

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(hostname=hostname,
                   port=port, username=username,
                   password=password)

    download_t = time.process_time_ns()

    # lägg till buffer?
    with open("downloaded.txt", "ab") as f:
        with client.open_sftp().file("testing.txt", "rb") as nf:
            for chunk in iter(lambda: nf.read(chunk*kibibytes), b''):
                f.write(chunk)
                f.flush()

    return (time.process_time_ns() - download_t), client


def time_hashing(filename: str, chunk: int) -> int:
    """Time checksum generation"""

    hash_t = time.process_time_ns()
    checksum = dp_cli.gen_sha512(filename=filename,
                                 chunk_size=chunk*kibibytes)

    return time.process_time_ns() - hash_t, checksum


def time_encryption(filename: str, enc_name: str, chunk: int, key) -> int:
    """Times encryption of file"""

    encryption_t = time.process_time_ns()
    dp_cli.encrypt_file(file=filename, newfile=enc_name,
                        key=key, chunk=chunk*kibibytes)

    return time.process_time_ns() - encryption_t


def time_decryption(filename: str, dec_name: str, key, chunk: int) -> int:
    """Times decryption of file"""

    decryption_t = time.process_time_ns()
    dp_cli.decrypt_file(file=filename, newfile=dec_name,
                        key=key, chunk=chunk*kibibytes)

    return time.process_time_ns() - decryption_t


def create_plot(speed, filename, timestamp):
    """Generates plot from timing operations"""

    plot = speed.plot(title="Cryptographic speed", lw=2,
                      colormap='jet', marker='.', markersize=10)
    plot.set_xlabel("Chunk size (kibibytes)")
    plot.set_ylabel("Speed (MB/s)")
    plt.savefig(f'{FIGDIR}cryptspeed_{filename}_{timestamp}.png')


# MAIN ################################################################# MAIN #


def main(files: list):
    """Main function, executes timing operations."""

    now = datetime.datetime.now()
    TIMESTAMP = f"{now.year}-{now.month}-{now.day}_{now.hour}" \
                f"-{now.minute}-{now.second}"

    # File to use
    for f_ in files:
        print("file: ", f_)

        # Files
        filename = f_.split('/')[-1]						# Filename
        filesize_mb = dp_cli.get_filesize(f_)/1e6		# Filesize in MB
        csv_file = f"chunk_timings-{TIMESTAMP}.csv"         # Csv file
        enc_file = f"{FILESDIR}encrypted_{filename}"        # Encrypted file
        dec_file = f"{FILESDIR}decrypted_{filename}"        # Decrypted file

        create_csv_file(csv_file)

        # Time operations and save to csv file
        chunk_size = 1				    # Number of kibibytes in chunk
        while chunk_size <= 1000:
            print("Chunk: ", chunk_size)

            # Time transfer
            print("Uploading...")
            upload_elapsed_time_ns, client = time_upload(filename=f_,
                                                         chunk=chunk_size)
            print(upload_elapsed_time_ns/1e9)

            print("Resting...")
            time.sleep(60)

            print("Downloading...")
            download_elapsed_time_ns, client = time_download(chunk=chunk_size)

            print("Deleting file...")
            try:
                stdin, stdout, stderr = client.exec_command('ls -lh')
                print(stdout.read())
                client.exec_command('rm testing.txt')
                client.close()
            except:
                sys.exit("could not delete file on server")

            print("Resting...")
            time.sleep(60)                      # Rest

            # Time hash generation
            print("Hashing original file...")
            hash_elapsed_time_ns, origin_hash = time_hashing(filename=f_,
                                                             chunk=chunk_size)

            remove_files(enc_file, dec_file)    # Remove files if the exist

            print("Hashing downloaded file...")
            down_hash = dp_cli.gen_sha512(filename=f_,
                                          chunk_size=chunk_size*kibibytes)
            if os.path.exists(f"downloaded.txt"):
                os.remove(f"downloaded.txt")

            print("Checking hashes...")
            if origin_hash != down_hash:
                sys.exit("Uploaded and downloaded file not identical!")
            else:
                print("Files identical!")

            print("Resting...")
            time.sleep(60)                      # Rest

            # Time encryption
            print("Encrypting...")
            aeskey = dp_cli.EncryptionKey()
            encryption_elapsed_time_ns = time_encryption(filename=f_,
                                                         enc_name=enc_file,
                                                         chunk=chunk_size,
                                                         key=aeskey.key)

            print("Resting...")
            time.sleep(60)      # Rest

            # Time decryption
            print("Decrypting...")
            decryption_elapsed_time_ns = time_decryption(filename=enc_file,
                                                         dec_name=dec_file,
                                                         key=aeskey.key,
                                                         chunk=chunk_size)

            remove_files(enc_file, dec_file)    # Remove files

            # Save measurements to file
            try:
                create_csv_file(filename=csv_file,
                                hashtime=hash_elapsed_time_ns,
                                enctime=encryption_elapsed_time_ns,
                                dectime=decryption_elapsed_time_ns,
                                uptime=upload_elapsed_time_ns,
                                downtime=download_elapsed_time_ns,
                                chunk=chunk_size,
                                size=filesize_mb)
            except:
                sys.exit("Could not save elapsed time to file.")

            if chunk_size < 16:
                chunk_size *= 2
            elif 16 <= chunk_size < 1e2:
                chunk_size += 16
            else:
                chunk_size += 96

        print("Plotting...")
        speed_table = pd.read_csv(csv_file, usecols=['Chunk_kibibytes',
                                                     'Checksum_MB/s',
                                                     'Encryption_MB/s',
                                                     'Decryption_MB/s',
                                                     'Upload_MB/s',
                                                     'Download_MB/s'],
                                  index_col=0)

        create_plot(speed=speed_table, filename=f_, timestamp=TIMESTAMP)


if __name__ == "__main__":
    files = [f"{FILESDIR}testfile_109.fna"]

    hostname = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    main(files)
