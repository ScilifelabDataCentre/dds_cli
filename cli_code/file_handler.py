"""
File handler.
Responsible for IO related operations, including compression, encryption, etc.
"""

# IMPORTS ########################################################### IMPORTS #

import zstandard as zstd
import sys
import os
# import shutil
# import collections
import logging
from pathlib import Path
import hashlib
import textwrap

# from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from prettytable import PrettyTable
from nacl.bindings import (crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.public import PrivateKey
# from nacl.exceptions import CryptoError
# from bitstring import BitArray

from cli_code import (LOG_FILE, DIRS, SEGMENT_SIZE,
                      CIPHER_SEGMENT_SIZE)  # , MAX_CTR
from cli_code.exceptions_ds import (DeliverySystemException, LoggingError,
                                    CompressionError)
# from cli_code.crypto_ds import gen_md5

# VARIABLES ####################################################### VARIABLES #

MAX_NONCE = 2**(12*8)


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

    Raises:
        LoggingError:   Logging to file or console failed
    '''

    # Save logs to file
    try:
        if file:
            file_handler = logging.FileHandler(filename=filename)
            file_handler.setLevel(file_setlevel)
            fh_formatter = logging.Formatter(fh_format)
            file_handler.setFormatter(fh_formatter)
            logger.addHandler(file_handler)
    except LoggingError as le:
        sys.exit(f"Logging to file failed: {le}")

    # Display logs in console
    try:
        if stream:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(stream_setlevel)
            sh_formatter = logging.Formatter(sh_format)
            stream_handler.setFormatter(sh_formatter)
            logger.addHandler(stream_handler)
    except LoggingError as le:
        sys.exit(f"Logging to console failed: {le}")

    return logger


# Set up logger ############## Needs to be here ############### Set up logger #
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
# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #
###############################################################################
# Compression formats and their file signatures
MAGIC_DICT = {
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
MAX_FMT = max(len(x) for x in MAGIC_DICT)   # Longest signature

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


def file_reader(file, chunk_size: int = SEGMENT_SIZE) -> (bytes):
    '''Yields the file chunk by chunk.

    Args:
        file:           Path to file
        chunk_size:     Number of bytes to read from file at a time

    Yields:
        bytes:  Data chunk of size chunk_size
    '''

    for chunk in iter(lambda: file.read(chunk_size), b''):
        yield chunk


def file_writer(filehandler, gen, last_nonce):

    nonce = b''

    # Save chunks to file
    for nonce, chunk in gen:
        filehandler.write(chunk)

    # If reached end of file but nonces don't match - the entire file has not
    # been delivered
    nonce_ok, error = check_last_nonce(filehandler.name, last_nonce, nonce)

    return nonce_ok, error


def file_deleter(file):

    if not file.exists():
        return

    try:
        file.unlink()
    except OSError as ose:
        LOG.warning(f"Failed deleting file {file}: {ose}.\nTrying again.")
        try:
            os.remove(file)
        except OSError as ose:
            LOG.warning(f"Failed deleting file {file}: {ose}.")
        else:
            LOG.info(f"Deleted file {file}")
    else:
        LOG.info(f"Deleted file {file}")

###############################################################################
# COMPRESSION ################################################### COMPRESSION #
###############################################################################


def compress_file(filehandler, chunk_size: int = SEGMENT_SIZE) -> (bytes):
    '''Compresses file

    Args:
        file:           Path to file
        chunk_size:     Number of bytes to compress at a time

    Yields:
        bytes:  Compressed data chunk

    '''

    # Initiate a Zstandard compressor
    cctzx = zstd.ZstdCompressor(write_checksum=True, level=4)
    with cctzx.stream_reader(filehandler) as compressor:  # Compress while reading
        for chunk in iter(lambda: compressor.read(chunk_size), b''):
            yield chunk


def decompress_file(filehandler, gen, last_nonce) -> (bytes):
    '''Decompresses file

    Args:
        file:           Path to file
        chunk_size:     Number of bytes to compress at a time

    Yields:
        bytes:  Compressed data chunk

    '''

    nonce = b''

    # Initiate a Zstandard decompressor
    dctx = zstd.ZstdDecompressor()
    with dctx.stream_writer(filehandler) as decompressor:
        for nonce, chunk in gen:
            decompressor.write(chunk)   # Write decompressed chunks to file

    # If reached end of file but nonces don't match - the entire file has not
    # been delivered
    nonce_ok, error = check_last_nonce(filehandler.name, last_nonce, nonce)

    return nonce_ok, error


def is_compressed(file: Path) -> (bool, str):
    '''Checks for file signatures in common compression formats.

    Args:
        file (Path):   Path object to be checked.

    Returns:
        tuple:      Info on if compressed format or not.

            bool:   True if file is compressed format.
            str:    Error message, "" if no error
    '''

    error = ""  # Error message

    try:
        # Check for file signature in beginning of file
        with file.open(mode='rb') as f:
            file_start = f.read(MAX_FMT)    # Read the first x bytes
            # LOG.debug(f"file: {file}\tfile start: {file_start}")
            for magic, _ in MAGIC_DICT.items():
                if file_start.startswith(magic):    # If file signature found
                    return True, error              # File is compressed
    except OSError as e:
        LOG.warning(e)      # Log warning, do not cancel all
        error = e           # Save error message

    return False, error    # File not compressed


###############################################################################
# CRYPTO ############################################################# CRYPTO #
###############################################################################


def aead_decrypt_chacha(file, key: bytes, iv: bytes) -> (bytes, bytes):
    '''Decrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
    construction described in RFC7539.

    '''

    # If position not directly after first nonce, then error - fail
    if file.tell() != 12:
        raise DeliverySystemException(f"Reading encrypted file {file.name} "
                                      "failed!")

    # Variables ################################################### Variables #
    iv_int = int.from_bytes(iv, 'little')   # Transform nonce to int
    aad = None  # Associated data, unencrypted but authenticated
    # ----------------------------------------------------------------------- #

    for enc_chunk in iter(lambda: file.read(CIPHER_SEGMENT_SIZE), b''):
        # Get nonce as bytes for decryption: if the nonce is larger than the
        # max number of chunks allowed to be encrypted (safely) -- begin at 0
        nonce = (iv_int if iv_int < MAX_NONCE
                 else iv_int % MAX_NONCE).to_bytes(length=12,
                                                   byteorder='little')

        iv_int += 1  # Increment nonce

        # Encrypt and yield nonce and ciphertext
        yield nonce, crypto_aead_chacha20poly1305_ietf_decrypt(ciphertext=enc_chunk,
                                                               aad=aad,
                                                               nonce=nonce,
                                                               key=key)


def aead_encrypt_chacha(gen, key: bytes, iv: bytes) -> (bytes, bytes):
    '''Encrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
    construction described in RFC7539.

    Args:
        gen (Generator):    Generator object, stream of file chunks
        key (bytes):        Data encryption key
        iv (bytes):         Initial nonce

    Yields:
        tuple:  The nonce for each data chunk and ciphertext

            bytes:  Nonce -- number only used once
            bytes:  Ciphertext
    '''

    # Variables ################################################### Variables #
    iv_int = int.from_bytes(iv, 'little')   # Transform nonce to int
    aad = None  # Associated data, unencrypted but authenticated
    # ----------------------------------------------------------------------- #

    for chunk in gen:
        # Get nonce as bytes for encryption: if the nonce is larger than the
        # max number of chunks allowed to be encrypted (safely) -- begin at 0
        nonce = (iv_int if iv_int < MAX_NONCE
                 else iv_int % MAX_NONCE).to_bytes(length=12,
                                                   byteorder='little')
        LOG.debug(f"\nnonce in encryption: \t{nonce}\n")

        iv_int += 1  # Increment nonce

        # Encrypt and yield nonce and ciphertext
        yield nonce, crypto_aead_chacha20poly1305_ietf_encrypt(message=chunk,
                                                               aad=aad,
                                                               nonce=nonce,
                                                               key=key)


def check_last_nonce(filename, last_nonce, nonce) -> (bool, str):

    # If reached end of file but nonces don't match - the entire file has not
    # been delivered
    if nonce != last_nonce:
        error = f"File {filename} is missing chunks!"
        LOG.exception(error)
        return False, error
    else:
        return True, ""


###############################################################################
# PREP AND FINISH ########################################### PREP AND FINISH #
###############################################################################


def reverse_processing(file: str, file_info: dict):
    '''Decrypts and decompresses file'''

    LOG.debug(f"\n{file}: {file_info}\n")

    # Variables ################################################### Variables #
    infile = file_info['new_file']  # Downloaded file
    # Decrypted and decompressed file
    outfile = infile.parent / Path(infile.stem).stem
    nonce = b''
    error = ""
    # ----------------------------------------------------------------------- #
    # LOG.debug(f"Infile: {infile}, Outfile: {outfile}")

    # START ##################################### START #
    try:
        original_umask = os.umask(0)  # User file-creation mode mask
        with infile.open(mode='rb+') as f:
            # Get last nonce
            f.seek(-12, os.SEEK_END)
            last_nonce = f.read(12)

            # Remove last nonce from file
            f.seek(-12, os.SEEK_END)
            f.truncate()

            # Jump back to beginning and get first nonce
            f.seek(0)
            first_nonce = f.read(12)

            # Get key for decryption
            key = bytes.fromhex(file_info['key'])

            # Decrypt file
            chunk_stream = aead_decrypt_chacha(file=f, key=key, iv=first_nonce)

            # Save decrypted file
            with outfile.open(mode='ab+') as of:
                # Decompress and save if compressed by DS, otherwise just save
                saved, error = decompress_file(filehandler=of,
                                               gen=chunk_stream,
                                               last_nonce=last_nonce) \
                    if file_info['ds_compressed'] \
                    else file_writer(filehandler=of,
                                     gen=chunk_stream,
                                     last_nonce=last_nonce)

                if not saved:
                    return False, outfile, error

    except DeliverySystemException as ee:
        error = f"Finalizing of file failed! {ee}"
        LOG.exception(error)
        return False, outfile, error
    else:
        LOG.info(f"File: '{file}' -- Finalizing completed! Decrypted file "
                 f"saved at {outfile}")
    finally:
        os.umask(original_umask)    # Remove mask

    # FINISHED ############################### FINISHED #
    return True, outfile, ""


def process_file(file: Path, file_info: dict) \
        -> (bool, Path, int, bool, str):
    '''Processes the files incl compression, encryption

    Args:
        file (Path):           Path to file
        file_info (dict):      Info about file

    Returns:
        tuple: Information about finished processing

            bool:   True if processing successful -- compression+encryption
            Path:   Path to processed file
            int:    Size (in bytes) of processd file
            bool:   True if compressed
            str:    Error message, empty string if no error

    Raises:
        DeliverySystemException:    Failed processing or wrong argument format
        OSError:                    File not found or could not create tempdir

    '''

    # If file path not Path type --> quit whole exception, something wrong
    if not isinstance(file, Path):
        emessage = f"Wrong format! {file} is not a 'Path' object."
        raise DeliverySystemException(emessage)   # Bug somewhere in code

    # If file doesn't exist --> quit whole exception, something wrong
    if not file.exists():
        emessage = f"The path {file} does not exist!"
        raise OSError(emessage)  # Bug somewhere in code

    # Variables ################################################### Variables #
    outfile = DIRS[1] / file_info['new_file']   # Path to save processed file
    new_dir = DIRS[1] / file_info['directory_path']     # New temp subdir
    checksum = ""
    key = b''
    # ----------------------------------------------------------------------- #
    # LOG.debug(f"Infile: {file}, Outfile: {outfile}")

    # Hasher
    enc_file_hash = hashlib.md5()

    # If new temporary subdir doesn't exist -- create it
    if not new_dir.exists():
        try:
            new_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            error = f"File: {file} -- Creating tempdir {new_dir} failed! :: {e}"
            LOG.exception(error)
            return False, Path(""), 0, False, "", "", error
        # LOG.debug(f"File: {file}, Tempdir: {new_dir}")

    # PROCESSING START ##################################### PROCESSING START #
    try:
        original_umask = os.umask(0)  # User file-creation mode mask
        with file.open(mode='rb') as f:

            # Compression ###### If not already compressed ###### Compression #
            chunk_stream = file_reader(f) if file_info['compressed'] \
                else compress_file(f)

            # Encryption ######################################### Encryption #
            with outfile.open(mode='wb+') as of:
                keypair = PrivateKey.generate()
                

                key = os.urandom(32)            # Data encryption key
                iv_bytes = os.urandom(12)       # Initial nonce/value
                LOG.debug(f"File: {file}, Data encryption key: {key},a"
                          f"Initial nonce: {iv_bytes}")

                # Write nonce to file and save 12 bytes for last nonce
                of.write(iv_bytes)
                enc_file_hash.update(iv_bytes)
                # saved_bytes = (0).to_bytes(length=12, byteorder='little')
                # LOG.debug(f"saved bytes: {saved_bytes}")
                # of.write(saved_bytes)

                nonce = b''     # Catches the nonces
                for nonce, ciphertext in aead_encrypt_chacha(gen=chunk_stream,
                                                             key=key,
                                                             iv=iv_bytes):
                    LOG.debug(
                        f"\nnonce: {nonce}, \nciphertext: {ciphertext[0:100]}\n")
                    of.write(ciphertext)    # Write the ciphertext to the file
                    enc_file_hash.update(ciphertext)

                LOG.debug(f"\nlast nonce:\t{nonce}\n")
                # of.seek(12)
                # LOG.debug(f"\nposition (12):\t{of.tell()}\n")
                of.write(nonce)
                enc_file_hash.update(nonce)

    except DeliverySystemException as ee:  # FIX EXCEPTION HERE
        error = f"Processig failed! {ee}"
        LOG.exception(error)
        return False, outfile, 0, False, "", "", error
    else:
        LOG.info(f"File: '{file}' -- Processing completed! Encrypted file "
                 f"saved at {outfile}")
        # Info on if delivery system compressed or not
        ds_compressed = False if file_info['compressed'] else True
    finally:
        os.umask(original_umask)    # Remove mask

    # PROCESSING FINISHED ############################### PROCESSING FINISHED #
    LOG.debug(f"\nlast nonce:\t{nonce}\n")
    return (True, outfile, outfile.stat().st_size, ds_compressed,
            key.hex(), enc_file_hash.hexdigest(), "")
