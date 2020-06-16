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
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from nacl.bindings import (crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.exceptions import CryptoError

from cli_code import LOG_FILE

# IO FUNCTIONS ################################################# IO FUNCTIONS #


def config_logger(logger, filename: str = LOG_FILE, file: bool = False,
                  file_setlevel=logging.WARNING, fh_format: str = "",
                  stream: bool = False, stream_setlevel=logging.WARNING,
                  sh_format: str = ""):
    '''Creates log file '''

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

# CONFIG ############################################################# CONFIG #


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
LOG = config_logger(
    logger=LOG, filename=LOG_FILE,
    file=True, file_setlevel=logging.DEBUG,
    fh_format="%(asctime)s::%(levelname)s::" +
    "%(name)s::%(lineno)d::%(message)s",
    stream=True, stream_setlevel=logging.DEBUG,
    sh_format="%(asctime)s::%(levelname)s::%(name)s::" +
    "%(lineno)d::%(message)s"
)
LOG.debug("5. debug")