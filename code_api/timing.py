"""Script used for timing different parts of the dp api."""

import os
import code_api.dp_cli as dp_cli
import time 
import csv


def main():
	"""Main function, executes timing operations."""

	if not os.path.exists("chunk_timings.csv"):
		with open("chunk_timings.csv", mode="w") as csvfile: 
			writer = csv.writer(csvfile)
			headers = ["Chunk_kibibytes", "File_size_MB", "Checksum", "Checksum_MB/s", "Encryption", "Encryption_MB/s"]
			writer.writerow(headers)

	# TODO: Time different chunk sizes used in hash generation
	filename = "testfile1.fna"
	filesize_mb = dp_cli.get_filesize(filename)/1e6
	chunk_size = [1]
	while chunk_size[-1] <= 1e3:
		if chunk_size[-1] < 16: 
			chunk_size.append(chunk_size[-1]*2)
		elif 16 <= chunk_size[-1] < 1e2:
			chunk_size.append(chunk_size[-1]+16)
		else: 
			chunk_size.append(chunk_size[-1]+96)
	
	print(chunk_size)

	kibibytes = 1024

	for kb_ in chunk_size: 
		hash_t = time.process_time_ns()
		hash = dp_cli.gen_sha512(filename=filename, chunk_size=kb_*kibibytes)
		hash_elapsed_time_ns = time.process_time_ns() - hash_t

		with open("chunk_timings.csv", mode="a") as csvfile:
			writer = csv.writer(csvfile)
			hash_elapsed_time_s = hash_elapsed_time_ns/1e9
			row = [kb_, filesize_mb, hash_elapsed_time_s, filesize_mb/hash_elapsed_time_s]
			writer.writerow(row)

if __name__ == "__main__":
	main()