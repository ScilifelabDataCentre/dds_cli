import sys
import os
from pathlib import Path
import io
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from nacl.bindings import (crypto_kx_client_session_keys,
                           crypto_kx_server_session_keys,
                           crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.exceptions import CryptoError
from nacl.public import PrivateKey

# from cli_code.crypt4gh_altered.crypt4gh import lib, header
# import cli_code.crypt4gh_altered.crypt4gh.keys.c4gh as keys
# from cli_code.crypt4gh_altered.crypt4gh.keys.c4gh import MAGIC_WORD, parse_private_key
from cli_code.crypt4gh.crypt4gh import lib, header, keys

from cli_code.exceptions_ds import HashException, EncryptionError

SEGMENT_SIZE = 65536
MAGIC_NUMBER = b'crypt4gh'
VERSION = 1
CIPHER_DIFF = 28
CIPHER_SEGMENT_SIZE = SEGMENT_SIZE + CIPHER_DIFF


class Crypt4GHKey:

    def __init__(self):
        '''Generate public key pair'''

        sk = PrivateKey.generate()
        self.seckey = bytes(sk)
        self.pubkey = bytes(sk.public_key)

    def __enter__(self):
        '''Allows for implementation using "with" statement.
        Building.'''

        return self

    def __exit__(self, exc_type, exc_value, tb):
        '''Allows for implementation using "with" statement.
        Tear it down. Delete class.'''

        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True
        
    def prep_upload(self, file: str, recip_pub, filedir, path_from_base):
        '''Prepares the files for upload'''

        # hash
        _, checksum = gen_hmac(file=file)

        # encrypt
        encrypted_file = filedir / Path(file.name + ".c4gh")
        print("encrypted file", encrypted_file)
        try:
            original_umask = os.umask(0)
            with file.open(mode='rb') as infile:
                with encrypted_file.open(mode='ab+') as outfile:
                    lib.encrypt(keys=[(0, self.seckey, recip_pub)],
                                infile=infile,
                                outfile=outfile)
        except EncryptionError as ee:
            return file, "Error", ee
        finally:
            os.umask(original_umask)
        
        return file, encrypted_file, checksum


def secure_password_hash(password_settings: str,
                         password_entered: str) -> (str):
    '''Generates secure password hash.

    Args:
            password_settings:  String containing the salt, length of hash,
                                n-exponential, r and p variables.
                                Taken from database. Separated by '$'.
            password_entered:   The user-specified password.

    Returns:
            str:    The derived hash from the user-specified password.

    '''

    settings = password_settings.split("$")
    for i in [1, 2, 3, 4]:
        settings[i] = int(settings[i])

    kdf = Scrypt(salt=bytes.fromhex(settings[0]),
                 length=settings[1],
                 n=2**settings[2],
                 r=settings[3],
                 p=settings[4],
                 backend=default_backend())

    return (kdf.derive(password_entered.encode('utf-8'))).hex()


def gen_hmac(file) -> (Path, str):
    '''Generates a HMAC for a file

    Args:
        file: Path to hash

    Returns:
        tuple: File and path

            Path:   Path to file
            str:    HMAC generated for file
    '''

    file_hash = hmac.HMAC(key=b'SuperSecureChecksumKey',
                          algorithm=hashes.SHA256(),
                          backend=default_backend())
    try:
        with file.open(mode='rb') as f:
            for chunk in iter(lambda: f.read(8388608), b''):
                file_hash.update(chunk)
    except HashException as he:
        sys.exit(f"HMAC for file {str(file)} could not be generated: {he}")
    else:
        return file, file_hash.finalize().hex()


def gen_hmac_streamed(file) -> (Path, str):
    '''Generates a HMAC for a file

    Args:
        file: Path to hash

    Returns:
        tuple: File and path

            Path:   Path to file
            str:    HMAC generated for file
    '''

    try:
        with file.open(mode='rb') as f:
            for chunk in iter(lambda: f.read(8388608), b''):
                file_hash.update(chunk)
    except HashException as he:
        sys.exit(f"HMAC for file {str(file)} could not be generated: {he}")
    else:
        return file, file_hash.finalize().hex()
