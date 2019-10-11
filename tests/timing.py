"""Script used for timing different parts of the dp api."""

# IMPORTS ########################################################### IMPORTS #

import os
import sys
import code_api.dp_cli as dp_cli
import time
import datetime
import csv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #

FILESDIR = "/Volumes/Seagate_Backup_Plus_Drive/Delivery_Portal/api/Files/"
TESTDIR = "/Users/inaod568/repos/dp_api/tests/"
FIGDIR = "/Volumes/Seagate_Backup_Plus_Drive/Delivery_Portal/api/Figures/"
kibibytes = 1024

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
                           "Decryption", "Decryption_MB/s"]
                writer.writerow(headers)
        except FileException:
            print("The csv file could not be created.")
    else:
        try:
            hash_elapsed_time_ns = kwargs.get('hashtime', None)
            encryption_elapsed_time_ns = kwargs.get('enctime', None)
            decryption_elapsed_time_ns = kwargs.get('dectime', None)
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
            row = [chunk_size,
                   filesize_mb,
                   hash_elapsed_time_s,
                   filesize_mb/hash_elapsed_time_s,
                   encryption_elapsed_time_s,
                   filesize_mb/encryption_elapsed_time_s,
                   decryption_elapsed_time_s,
                   filesize_mb/decryption_elapsed_time_s]
            writer.writerow(row)


def time_hashing(filename: str, chunk: int) -> int:
    """Time checksum generation"""

    hash_t = time.process_time_ns()
    checksum = dp_cli.gen_sha512(filename=filename,
                                 chunk_size=chunk*kibibytes)

    return time.process_time_ns() - hash_t


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
        chunk_size = 1000				    # Number of kibibytes in chunk
        while chunk_size <= 1000:
            # Time hash generation
            hash_elapsed_time_ns = time_hashing(filename=f_,
                                                chunk=chunk_size)

            remove_files(enc_file, dec_file)    # Remove files if the exist
            time.sleep(60)                      # Rest

            # Time encryption
            aeskey = dp_cli.EncryptionKey()
            encryption_elapsed_time_ns = time_encryption(filename=f_,
                                                         enc_name=enc_file,
                                                         chunk=chunk_size,
                                                         key=aeskey.key)

            time.sleep(60)      # Rest

            # Time decryption
            decryption_elapsed_time_ns = time_decryption(filename=enc_file,
                                                         dec_name=dec_file,
                                                         key=aeskey.key,
                                                         chunk=chunk_size)

            remove_files(enc_file, dec_file)    # Remove files

            # Save measurements to file
            create_csv_file(filename=f_,
                            hashtime=hash_elapsed_time_ns,
                            enctime=encryption_elapsed_time_ns,
                            dectime=decryption_elapsed_time_ns,
                            chunk=chunk_size,
                            size=filesize_mb)

            if chunk_size < 16:
                chunk_size *= 2
            elif 16 <= chunk_size < 1e2:
                chunk_size += 16
            else:
                chunk_size += 96

        speed_table = pd.read_csv(csv_file, usecols=['Chunk_kibibytes',
                                                     'Checksum_MB/s',
                                                     'Encryption_MB/s',
                                                     'Decryption_MB/s'],
                                  index_col=0)

        create_plot(speed=speed_table, filename=f_, timestamp=TIMESTAMP)


if __name__ == "__main__":
    files = [f"{FILESDIR}testfile_109.fna"]

    main(files)
