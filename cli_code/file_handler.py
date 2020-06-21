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

# Set up logger #


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

# Set up logger #


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
        LOG.info(f"path_base = {path_base} "
                 "--> root path is from chosen folder.")
        fileparts = file.parts
        start_ind = fileparts.index(path_base)
        return Path(*fileparts[start_ind:-1])
    else:
        LOG.info(f"path_base = {path_base} "
                 "--> root path is . (user specified file)")
        return Path("")

# COMPRESSION ################################################### COMPRESSION #


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
magic_dict
max_len = max(len(x) for x in magic_dict)


def compress_file(file: Path, chunk_size: int = 65536):
    cctzx = zstd.ZstdCompressor(write_checksum=True, level=4)
    with cctzx.stream_reader(file) as reader:
        for chunk in iter(lambda: reader.read(chunk_size), b''):
            yield chunk


def is_compressed(file: Path):
    '''Checks for file signatures in common compression formats'''

    with file.open(mode='rb') as f:
        file_start = f.read(max_len)
        LOG.debug(f"file start: {file_start}, type: {type(file_start)}")
        for magic, filetype in magic_dict.items():
            LOG.debug(f"magic: {magic}, filetype: {filetype}")
            if file_start.startswith(magic):
                return True, filetype
        
    return False, ""

# CRYPTO ############################################################# CRYPTO #


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

    LOG.debug(f"Processing {file}, filedir: {filedir}, "
              f"bucket_path: {bucket_path}, chunk_size: {chunk_size}")

    proc_suff = ""  # Suffix after file processed
    key = os.urandom(32)

    LOG.debug(f"Data encryption key: {key}")

    # Original file size
    if not isinstance(file, Path):
        LOG.exception(f"Wrong format! {file} is not a 'Path' object.")
        return file, 0, "Error", "The file is not a Path", None

    if not file.exists():
        LOG.exception(f"The file {file} does not exist!")
        return file, 0, "Error", "The file does not exist", None

    o_size = file.stat().st_size  # Original size in bytes
    LOG.info(f"Original file size: {o_size} ({file})")

    # Check if compressed and save algorithm info if yes
    compressed, alg = is_compressed(file)
    LOG.debug(f"{compressed}, {alg}")
    if not compressed:
        proc_suff += f".zst"
        LOG.debug(f"File {file.name} not compressed. "
                  f"New file suffix: {proc_suff}")
    proc_suff += ".ccp"
    LOG.debug(f"New file suffix: {proc_suff}")

    outfile = filedir / Path(file.name + proc_suff)
    LOG.debug(f"Processed file will be saved in location: {outfile}")

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
        LOG.exception(f"Processig failed! {ee}")
        return file, o_size, "Error", ee, False
    else:
        LOG.info(f"Compression of {file} -- completed!")
        compressed = True
    finally:
        os.umask(original_umask)

    # Check encrypted file size
    e_size = outfile.stat().st_size  # Encrypted size in bytes
    LOG.info(f"Encrypted file size: {e_size} ({outfile})")

    return file, o_size, outfile, e_size, compressed

# CONFIG ############################################################# CONFIG #
