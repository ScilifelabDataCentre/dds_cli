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
        # LOG.info(f"path_base = {path_base} "
        #          "--> root path is from chosen folder.")
        fileparts = file.parts
        start_ind = fileparts.index(path_base)
        return Path(*fileparts[start_ind:-1])
    else:
        # LOG.info(f"path_base = {path_base} "
        #          "--> root path is . (user specified file)")
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
        LOG.debug(f"file: {file}\tfile start: {file_start}"
                  f"\ttype: {type(file_start)}")
        for magic, filetype in magic_dict.items():
            # LOG.debug(f"magic: {magic}, filetype: {filetype}")
            if file_start.startswith(magic):
                return True, filetype

    return False, ""

# CRYPTO ############################################################# CRYPTO #


def file_reader(file: Path, chunk_size: int = 65536):
    for chunk in iter(lambda: file.read(chunk_size), b''):
        yield chunk


def aead_encrypt_chacha(gen, key, iv):
    '''Encrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
    construction described in RFC7539'''

    iv_int = int.from_bytes(iv, 'little')
    aad = None  # Associated data, unencrypted but authenticated
    for chunk in gen:
        nonce = (iv_int).to_bytes(length=12, byteorder='little')
        yield nonce, crypto_aead_chacha20poly1305_ietf_encrypt(message=chunk,
                                                               aad=aad,
                                                               nonce=nonce,
                                                               key=key)
        iv_int += 1


# PREP AND FINISH ########################################### PREP AND FINISH #


def process_file(file: Path, file_info: dict, filedir):

    LOG.debug(f"Processing {file}....")
    # Checking for errors first
    if not isinstance(file, Path):
        LOG.exception(f"Wrong format! {file} is not a 'Path' object.")
        return file, 0, "Error", "The file is not a Path", None

    if not file.exists():
        LOG.exception(f"The path {file} does not exist!")
        return file, 0, "Error", "The file does not exist", None

    key = os.urandom(32)
    LOG.debug(f"Data encryption key: {key}")

    outfile = filedir / file_info['new_file']
    LOG.debug(f"Processed file will be saved in location: '{outfile}'")

    new_dir = filedir / file_info['directory_path']
    LOG.debug(f"new_dir: {new_dir}")
    if not new_dir.exists():
        LOG.debug(f"The temporary directory '{new_dir}' did not exist, "
                  "creating it.")
        new_dir.mkdir(parents=True)

    # Read file
    try:
        original_umask = os.umask(0)
        with file.open(mode='rb') as f:
            # Compress if not compressed
            chunk_stream = file_reader(f) if file_info['compressed'] \
                else compress_file(f)
            # Encrypt
            LOG.info(f"Beginning encryption of file '{file}'.")
            with outfile.open(mode='ab+') as of:
                iv_bytes = os.urandom(12)
                # LOG.debug(f"Initial nonce -- bytes: {iv_bytes}\n"
                #           f"\tint: {int.from_bytes(iv_bytes, 'little')}")
                of.write(iv_bytes)
                saved_bytes = (0).to_bytes(length=12, byteorder='little')
                of.write(saved_bytes)
                nonce = b''
                for nonce, ciphertext in aead_encrypt_chacha(gen=chunk_stream,
                                                             key=key,
                                                             iv=iv_bytes):
                    # of.write(nonce)
                    # LOG.debug(f"Nonce: {nonce}, "
                    #           f"int: {int.from_bytes(nonce, 'little')}")
                    of.write(ciphertext)
                of.seek(12)
                # LOG.debug(f"last nonce: {nonce}")
                of.write(nonce)
    except Exception as ee:  # FIX EXCEPTION
        LOG.exception(f"Processig failed! {ee}")
        return False, file, "Error", ee, False
    else:
        LOG.info(f"Encryption of '{file}' -- completed!")
        compressed = True
    finally:
        os.umask(original_umask)

    # Check encrypted file size
    e_size = outfile.stat().st_size  # Encrypted size in bytes
    LOG.info(f"Encrypted file size: {e_size} ({outfile})")

    return True, file, outfile, e_size, compressed


def process_folder(folder_contents: dict, filedir):

    for file in folder_contents:
        LOG.debug(f"Processing file in folder: {file}")
        success, *info = process_file(file, folder_contents[file], filedir)
        LOG.debug(f"{success}: {info}")
        if not success:
            return success, info

    return success, info


def prep_upload(path: Path, path_info: dict, filedir):
    '''Prepares the files for upload'''

    LOG.debug(f"\nProcessing {path}, path_info: {path_info}\n")

    if path_info['directory']:
        success, process_info = process_folder(path_info['contents'], filedir)
    elif path_info['file']:
        success, (*process_info) = process_file(path, path_info, filedir)

    return success, process_info
