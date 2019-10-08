"""Script used for timing different parts of the dp api."""

import os
import code_api.dp_cli as dp_cli
import time
import csv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def main():
    """Main function, executes timing operations."""

    # File to use
    filename = "testfile_109.fna"							# Filename
    filesize_mb = dp_cli.get_filesize(filename)/1e6		# Filesize in MB

    # Variables
    kibibytes = 1024

    # Create timings file if doesn't exist
    if not os.path.exists("chunk_timings.csv"):
        with open("chunk_timings.csv", mode="w") as csvfile:
            writer = csv.writer(csvfile)
            headers = ["Chunk_kibibytes", "File_size_MB", "Checksum",
                       "Checksum_MB/s", "Encryption", "Encryption_MB/s", "Decryption", "Decryption_MB/s"]
            writer.writerow(headers)

    # Time operations and save to csv file
    chunk_size = 1				# Number of kibibytes in chunk
    while chunk_size <= 1e3:
        # Time hash generation
        hash_t = time.process_time_ns()
        checksum = dp_cli.gen_sha512(
            filename=filename, chunk_size=chunk_size*kibibytes)
        hash_elapsed_time_ns = time.process_time_ns() - hash_t

        if os.path.exists(f"encrypted_{filename}"):
                os.remove(f"encrypted_{filename}")

        if os.path.exists(f"decrypted_encrypted_{filename}"):
                os.remove(f"decrypted_encrypted_{filename}")

        time.sleep(60)
        
        # Time encryption
        aeskey = dp_cli.EncryptionKey()
        encryption_t = time.process_time_ns()
        dp_cli.encrypt_file(file=filename, key=aeskey.key,
                            chunk=chunk_size*kibibytes)
        encryption_elapsed_time_ns = time.process_time_ns() - encryption_t
        
        time.sleep(60)

        # Time decryption
        decryption_t = time.process_time_ns()
        dp_cli.decrypt_file(
            file=f"encrypted_{filename}", key=aeskey.key, chunk=chunk_size*kibibytes)
        decryption_elapsed_time_ns = time.process_time_ns() - decryption_t

        # Save measurements to file
        with open("chunk_timings.csv", mode="a") as csvfile:
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

        if chunk_size < 16:
            chunk_size *= 2
        elif 16 <= chunk_size < 1e2:
            chunk_size += 16
        else:
            chunk_size += 96

    speed = pd.read_csv("chunk_timings.csv", usecols=['Chunk_kibibytes', 'Checksum_MB/s', 'Encryption_MB/s', 'Decryption_MB/s'], index_col=0)
    print(speed)

    plot = speed.plot(title="Cryptographic speed", lw=2, colormap='jet', marker='.', markersize=10)
    plot.set_xlabel("Chunk size (kibibytes)")
    plot.set_ylabel("Speed (MB/s)")
    plt.savefig(f'cryptspeed_{filename}.png')

if __name__ == "__main__":
    main()
