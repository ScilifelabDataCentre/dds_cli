import gzip
import zstandard as zstd
import sys
import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from nacl.bindings import (crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.exceptions import CryptoError


def compress_file_gzip(file: Path, chunk_size: int = 65536):
    print("chunk size --- ", chunk_size)
    for chunk in iter(lambda: file.read(chunk_size), b''):
        yield gzip.compress(data=chunk, compresslevel=9)


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


def prep_upload(file: Path, filedir: Path = Path(""), chunk_size: int = 65536):
    '''Prepares the files for upload'''

    proc_suff = ""  # Suffix after file processed
    key = os.urandom(32)

    # Original file size
    # if not isinstance(file, Path):
    #     pass  # update dict with error

    # if not file.exists():
    #     pass  # update dict with error

    # o_size = file.stat().st_size  # Bytes

    # Check if compressed
    compressed = False
    print(chunk_size)
    # if compressed:
    #     proc_suff += ".gzip"
    # proc_suff += ".ccp1"
    # outfile = filedir / Path(file.name + proc_suff)
    outfile = Path("test_encrypted.xxx")

    # Read file
    with file.open(mode='rb') as f:
        chunk_stream = file_reader(f) if compressed else compress_file(
            f, chunk_size=chunk_size)
        with outfile.open(mode='ab+') as outfile:
            for nonce, ciphertext in aead_encrypt_chacha(chunk_stream, key):
                outfile.write(nonce)
                outfile.write(ciphertext)

    # Compress

    # Check compressed file size

    # Encrypt

    # Check encrypted file size

    # hash
    # _, checksum = gen_hmac(file=file)

    # encrypt
    # encrypted_file = self.tempdir.files / Path(file.name + ".c4gh")
    # try:
    #     original_umask = os.umask(0)
    #     with file.open(mode='rb') as orig:

    # except Exception as ee:
    #     return file, "Error", ee
    # finally:
    #     os.umask(original_umask)

    # return file, encrypted_file, checksum
