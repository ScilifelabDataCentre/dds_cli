"""
File handler.
Responsible for IO related operations, including compression, encryption, etc.
"""

# IMPORTS ########################################################### IMPORTS #

import zstandard as zstd
import sys
import os
import shutil
import datetime
import collections
import logging
from pathlib import Path
import tarfile

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from nacl.bindings import (crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.exceptions import CryptoError
from bitstring import BitArray

from cli_code import LOG_FILE, MAX_CTR

max_nonce = 2**(12*8)


###############################################################################
# Logging ########################################################### Logging #
###############################################################################


def config_logger(logger, filename: str = LOG_FILE, file: bool = False,
                  file_setlevel=logging.WARNING, fh_format: str = "",
                  stream: bool = False, stream_setlevel=logging.WARNING,
                  sh_format: str = ""):
    '''Creates log file

    Args:
        logger:             Logger to be configured
        filename:           Path to wished log file
        file:               True if to create log file
        file_setlevel:      The lowest level of logging in log file
        fh_format:          Format of file logs
        stream:             True if logs to be printed in console
        stream_setlevel:    The lowest level of logging in console
        sh_format:          Format of console logs

    Returns: 
        Logger:     Configured logger
    '''

    # Save logs to file
    if file:
        file_handler = logging.FileHandler(filename=filename)
        file_handler.setLevel(file_setlevel)
        fh_formatter = logging.Formatter(fh_format)
        file_handler.setFormatter(fh_formatter)
        logger.addHandler(file_handler)

    # Display logs in console
    if stream:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(stream_setlevel)
        sh_formatter = logging.Formatter(sh_format)
        stream_handler.setFormatter(sh_formatter)
        logger.addHandler(stream_handler)

    return logger


# Set up logger
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
LOG = config_logger(
    logger=LOG, filename=LOG_FILE,
    file=True, file_setlevel=logging.DEBUG,
    fh_format="%(asctime)s::%(levelname)s::" +
    "%(name)s::%(lineno)d::%(message)s",
    stream=True, stream_setlevel=logging.DEBUG,
    sh_format="%(levelname)s::%(name)s::" +
    "%(lineno)d::%(message)s"
)

###############################################################################
# IO FUNCTIONS ################################################# IO FUNCTIONS #
###############################################################################


def del_from_temp(file: Path) -> (bool):
    '''Deletes temporary files'''

    if file.exists():
        try:
            os.remove(file)
        except Exception as e:  # FIX EXCEPTION HERE
            LOG.exception("Failed deletion of temporary file "
                          f"{file}: {e}")
        else:
            LOG.info(f"Encrypted temporary file '{file}'"
                     "successfully deleted.")
    else:
        LOG.warning(f"The file '{file}' does not exist, but was recently "
                    "uploaded to S3 -- Error in delivery system! ")
    return


def get_root_path(file: Path, path_base: str = None) -> (Path):
    '''Gets the path to the file, from the entered folder.

    Args:
        file:       Path to file
        path_base:  None if single file, folder name if in folder

    Returns:
        Path:   Path from folder to file
    '''

    if path_base is not None:
        # LOG.info(f"path_base = {path_base} "
        #          "--> root path is from chosen folder.")
        fileparts = file.parts
        start_ind = fileparts.index(path_base)
        return Path(*fileparts[start_ind:-1])
    else:
        # LOG.info(f"path_base = {path_base} "
        #          "--> root path is . (user specified file)")
        return Path("")


def file_reader(file: Path, chunk_size: int = 65536) -> (bytes):
    '''Yields the file chunk by chunk.

    Args:
        file:           Path to file
        chunk_size:     Number of bytes to read from file at a time

    Yields:
        bytes:  Data chunk of size chunk_size
    '''

    for chunk in iter(lambda: file.read(chunk_size), b''):
        yield chunk

###############################################################################
# COMPRESSION ################################################### COMPRESSION #
###############################################################################


# Compression formats and their file signatures
magic_dict = {
    b'\x913HF': "hap",
    b'ustar': "tar",
    b'`\xea': "arj",
    b"_\'\xa8\x89": "jar",
    b'ZOO ': "zoo",
    b'PK\x03\x04': "zip",
    b'UFA\xc6\xd2\xc1': "ufa",
    b'StuffIt ': "sit",
    b'Rar!\x1a\x07\x00': "rar v4.x",
    b'Rar!\x1a\x07\x01\x00': "rar v5",
    b'MAr0\x00': "mar",
    b'DMS!': "dms",
    b'CRUSH v': "cru",
    b'BZh': "bz2",
    b'-lh': "lha",
    b'(This fi': "hqx",
    b'!\x12': "ain",
    b'\x1a\x0b': "pak",
    b'(\xb5/\xfd': "zst"
}
MAX_FMT = max(len(x) for x in magic_dict)   # Longest signature


def compress_file(file: Path, chunk_size: int = 65536) -> (bytes):
    '''Compresses file

    Args:
        file:           Path to file
        chunk_size:     Number of bytes to compress at a time

    Yields:
        bytes:  Compressed data chunk

    '''

    # Initiate a Zstandard compressor
    cctzx = zstd.ZstdCompressor(write_checksum=True, level=4)
    with cctzx.stream_reader(file) as reader:  # Compress while reading
        for chunk in iter(lambda: reader.read(chunk_size), b''):
            yield chunk


def is_compressed(file: Path) -> (bool, str):
    '''Checks for file signatures in common compression formats.

    Args:
        file:   Path object to be checked.

    Returns:
        tuple:      Info on if compressed format or not.

            bool:   True if file is compressed format.
            str:    Format abbreviation, empty string if not compressed.
    '''

    try:
        with file.open(mode='rb') as f:
            file_start = f.read(MAX_FMT)    # Read the first x bytes
            LOG.debug(f"file: {file}\tfile start: {file_start}")
            for magic, _ in magic_dict.items():
                if file_start.startswith(magic):    # If file signature found
                    return True                     # File is compressed
    except Exception as e:  # EDIT EXCEPTION HERE
        LOG.warning(e)      # Log warning, do not cancel all

    return False    # File not compressed


###############################################################################
# CRYPTO ############################################################# CRYPTO #
###############################################################################


def aead_encrypt_chacha(gen, key, iv) -> (bytes, bytes):
    '''Encrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
    construction described in RFC7539.

    Args:
        gen:    Generator object, stream of file chunks
        key:    Data encryption key
        iv:     Initial nonce

    Yields:
        tuple:  The nonce for each data chunk and ciphertext

            bytes:  Nonce -- number only used once
            bytes:  Ciphertext
    '''

    iv_int = int.from_bytes(iv, 'little')   # Transform nonce to int
    aad = None  # Associated data, unencrypted but authenticated
    for chunk in gen:
        # Get nonce as bytes for encryption
        nonce = (iv_int if iv_int < max_nonce
                 else iv_int % max_nonce).to_bytes(length=12,
                                                   byteorder='little')

        # Encrypt and yield nonce and ciphertext
        yield nonce, crypto_aead_chacha20poly1305_ietf_encrypt(message=chunk,
                                                               aad=aad,
                                                               nonce=nonce,
                                                               key=key)

        iv_int += 1  # Increment nonce - begin at 0 again if reaches max value


###############################################################################
# PREP AND FINISH ########################################### PREP AND FINISH #
###############################################################################


def process_file(file: Path, file_info: dict, filedir: Path) \
        -> (bool, Path, Path, int, bool, str):
    '''Processes the files incl compression, encryption

    Args:
        file:           Path to file
        file_info:      Info about file
        filedir:        Temporary file directory

    Returns:
        tuple: Information about finished processing

            bool:   True if processing successful -- compression+encryption
            Path:   Original file, pre-processing
            Path:   Path to processed file
            int:    Size (in bytes) of processd file
            bool:   True if compressed
            str:    Error message, empty string if no error

    '''

    LOG.debug(f"Processing {file}....")
    # Checking for errors first
    if not isinstance(file, Path):
        emessage = f"Wrong format! {file} is not a 'Path' object."
        raise Exception(emessage)  # Bug somewhere in code FIX EXCEPTION HERE

    if not file.exists():
        emessage = f"The path {file} does not exist!"
        raise Exception(emessage)  # Bug somewhere in code FIX EXCEPTION HERE

    # Path to save processed file
    outfile = filedir / file_info['new_file']
    LOG.debug(f"Processed file will be saved in location: '{outfile}'")

    # Check that temporary subdirectory exists
    new_dir = filedir / file_info['directory_path']
    # LOG.debug(f"new_dir: {new_dir}")
    if not new_dir.exists():
        LOG.debug(f"File: {file}\tThe temporary directory '{new_dir}' did "
                  "not exist, creating it.")
        new_dir.mkdir(parents=True)

    # Begin processing
    try:
        original_umask = os.umask(0)  # user file-creation mode mask
        with file.open(mode='rb') as f:

            # Compress if not compressed
            chunk_stream = file_reader(f) if file_info['compressed'] \
                else compress_file(f)

            LOG.info(f"Beginning encryption of file '{file}'.")
            # Begin encryption
            with outfile.open(mode='ab+') as of:
                key = os.urandom(32)     # Data encryption key
                iv_bytes = os.urandom(12)    # Initial nonce/value
                LOG.debug(f"Data encryption key: {key}\n"
                          "Initial nonce: {iv_bytes}")

                # Write nonce to file and save 12 bytes for last nonce
                of.write(iv_bytes)
                saved_bytes = (0).to_bytes(length=12, byteorder='little')
                of.write(saved_bytes)

                nonce = b''     # Catches the nonces
                for nonce, ciphertext in aead_encrypt_chacha(gen=chunk_stream,
                                                             key=key,
                                                             iv=iv_bytes):
                    of.write(ciphertext)    # Write the ciphertext to the file

                of.seek(12)         # Find the saved bytes
                of.write(nonce)     # Write the last nonce to file
    except Exception as ee:  # FIX EXCEPTION HERE
        LOG.exception(f"Processig failed! {ee}")
        return False, file, outfile, 0, False, ee
    else:
        LOG.info(f"Processing of '{file}' -- completed!")
        # Info on if delivery system compressed or not
        ds_compressed = False if file_info['compressed'] else True
    finally:
        os.umask(original_umask)    # Remove mask

    e_size = outfile.stat().st_size  # Encrypted size in bytes
    LOG.info(f"Encrypted file size: {e_size} ({outfile})")

    # success, original_file, processed_file, processed_size, compressed, error
    return True, file, outfile, e_size, ds_compressed, None


def prep_upload(path: Path, path_info: dict, filedir) \
        -> (bool, Path, list, str):
    '''Prepares the files for upload.

    Args:
        path:           Path to file
        path_info:      Info on file

    Returns:
        tuple:  Info on success and file after processing

            bool:   True if processing successful
            Path:   Path to original file
            list:   Processed file info
            str:    Message if paths don't match
    '''

    LOG.debug(f"\nProcessing {path}, path_info: {path_info}\n")

    # Begin processing incl encryption
    success, path_, *info = process_file(file=path,
                                         file_info=path_info,
                                         filedir=filedir)
    if path != path_:
        emessage = ("The processing did not return the same file as "
                    f"was input -- cannot continue delivery.")
        LOG.warning(emessage)
        return False, path, info, emessage

    # success, original_file, processed_file, processed_size, compressed, error
    return success, path, info, None
