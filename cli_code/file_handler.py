import gzip
import sys
import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


def compress_file(file: Path, chunk_size: int = 65536):
    for chunk in iter(lambda: file.read(chunk_size), b''):
        yield gzip.compress(data=chunk, compresslevel=9)


def file_reader(file: Path, chunk_size: int = 65536):
    for chunk in iter(lambda: file.read(chunk_size), b''):
        yield chunk


def prep_upload(file: Path, filedir: Path):
    '''Prepares the files for upload'''

    proc_suff = ""  # Suffix after file processed
    aad = b"authenticated but unencrypted data"  # Associated data
    key = ChaCha20Poly1305.generate_key()  # 32 bytes, fix own key later
    chacha = ChaCha20Poly1305(key=key)  # Initialize cipher
    nonce = os.urandom(12)

    # Original file size
    if not isinstance(file, Path):
        pass  # update dict with error

    if not file.exists():
        pass  # update dict with error

    o_size = file.stat().st_size  # Bytes

    # Check if compressed
    compressed = False
    if compressed:
        proc_suff += ".gzip"
    proc_suff += ".ccp1"
    outfile = filedir / Path(file.name + proc_suff)

    # Read file
    with file.open(mode='rb') as f:
        chunk_stream = file_reader(f) if compressed else compress_file(f)
        with outfile.open(mode='wb') as o_f:
            for chunk in chunk_stream:
                print("compressed : ", chunk)
                print("encrypted : ", chacha.encrypt(nonce, chunk, aad)) 
                o_f.write(chacha.encrypt(nonce, chunk, aad))
                print("decrypted : ", chacha.decrypt(nonce, chacha.encrypt(nonce, chunk, aad), aad))

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
