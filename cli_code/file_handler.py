import gzip
import zstandard as zstd
import sys
import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from nacl.bindings import (crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.exceptions import CryptoError


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
