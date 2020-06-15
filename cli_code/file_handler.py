"""
File handler.
Responsible for IO related operations, including compression, encryption, etc.
"""

# IMPORTS

import zstandard as zstd
import sys
import os
import shutil
import datetime
import collections
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from nacl.bindings import (crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.exceptions import CryptoError


# IO
def create_directories():
    '''Creates all temporary directories.

    Returns:
        tuple:  Directories created and all paths

            bool:   True if directories created
            tuple:  All created directories

    Raises:
        IOError:    Temporary folder failure
    '''

    # Create temporary folder with timestamp and all subfolders
    timestamp_ = timestamp()
    temp_dir = Path.cwd() / Path(f"DataDelivery_{timestamp_}")

    TemporaryDirectories = collections.namedtuple('TemporaryDirectories',
                                                  'root files meta logs')
    dirs = TemporaryDirectories(root=temp_dir / Path(""),
                                files=temp_dir / Path("files/"),
                                meta=temp_dir / Path("meta/"),
                                logs=temp_dir / Path("logs/"))

    for d_ in dirs:
        try:
            d_.mkdir(parents=True)
        except IOError as ose:
            print(f"The directory '{d_}' could not be created: {ose}"
                  "Cancelling delivery. ")

            if temp_dir.exists() and not isinstance(ose, FileExistsError):
                print("Deleting temporary directory.")
                try:
                    # Remove all prev created folders
                    shutil.rmtree(temp_dir)
                    sys.exit(f"Temporary directory deleted. \n\n"
                             "----DELIVERY CANCELLED---\n")  # and quit
                except IOError as ose:
                    sys.exit(f"Could not delete directory {temp_dir}: "
                             f"{ose}\n\n ----DELIVERY CANCELLED---\n")

                    return False, ()
            else:
                pass  # create log file here

    return True, dirs


def update_dir(old_dir, new_dir):
    '''Update file directory and create folder'''

    try:
        original_umask = os.umask(0)
        updated_dir = old_dir / new_dir
        if not updated_dir.exists():
            updated_dir.mkdir(parents=True)
    except IOError as ioe:
        sys.exit(f"Could not create folder: {ioe}")
    finally:
        os.umask(original_umask)

    return updated_dir


def get_root_path(file: Path, path_base: str = None):
    '''Gets the path to the file, from the entered folder. '''

    if path_base is not None:
        fileparts = file.parts
        start_ind = fileparts.index(path_base)
        return Path(*fileparts[start_ind:-1])
    else:
        return Path("")


def timestamp() -> (str):
    '''Gets the current time. Formats timestamp.

    Returns:
        str:    Timestamp in format 'YY-MM-DD_HH-MM-SS'

    '''

    now = datetime.datetime.now()
    timestamp = ""

    for t in (now.year, "-", now.month, "-", now.day, " ",
              now.hour, ":", now.minute, ":", now.second):
        if len(str(t)) == 1 and isinstance(t, int):
            timestamp += f"0{t}"
        else:
            timestamp += f"{t}"

    return timestamp.replace(" ", "_").replace(":", "-")

# CRYPTO ############################################################# CRYPTO #


def compress_file(file: Path, chunk_size: int = 65536):
    cctzx = zstd.ZstdCompressor(write_checksum=True, level=4)
    with cctzx.stream_reader(file) as reader:
        for chunk in iter(lambda: reader.read(chunk_size), b''):
            yield chunk


def file_reader(file: Path, chunk_size: int = 65536):
    for chunk in iter(lambda: file.read(chunk_size), b''):
        yield chunk


def aead_encrypt_chacha(gen, key):
    '''Encrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
    construction described in RFC7539'''

    aad = None  # Associated data, unencrypted but authenticated
    for chunk in gen:
        nonce = os.urandom(12)
        yield nonce, crypto_aead_chacha20poly1305_ietf_encrypt(message=chunk,
                                                               aad=aad,
                                                               nonce=nonce,
                                                               key=key)

# PREP AND FINISH ########################################### PREP AND FINISH #


def prep_upload(file: Path, filedir: Path = Path(""),
                bucket_path: Path = Path(""), chunk_size: int = 65536):
    '''Prepares the files for upload'''

    proc_suff = ""  # Suffix after file processed
    key = os.urandom(32)

    # Original file size
    if not isinstance(file, Path):
        return file, 0, "Error", "The file is not a Path", None

    if not file.exists():
        return file, 0, "Error", "The file does not exist", None

    o_size = file.stat().st_size  # Original size in bytes

    # Check if compressed and save algorithm info if yes
    compressed = False
    if compressed:
        proc_suff += ".zstd"
    proc_suff += ".ccp"
    outfile = filedir / Path(file.name + proc_suff)
    # Read file
    try:
        original_umask = os.umask(0)
        with file.open(mode='rb') as f:
            # Should we hash the file and save to file before comp and enc?
            # Compress if not compressed
            chunk_stream = file_reader(f) if compressed else compress_file(f)
            # Encrypt
            with outfile.open(mode='ab+') as of:
                for nonce, ciphertext in aead_encrypt_chacha(chunk_stream, key):
                    of.write(nonce)
                    of.write(ciphertext)
    except Exception as ee:  # FIX EXCEPTION
        return file, o_size, "Error", ee, False
    else:
        compressed = True
    finally:
        os.umask(original_umask)

    # Check encrypted file size
    e_size = outfile.stat().st_size  # Encrypted size in bytes

    return file, o_size, outfile, e_size, compressed
