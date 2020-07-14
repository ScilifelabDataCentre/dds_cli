import sys
import os
from pathlib import Path
import io
from base64 import b64decode, b64encode
import logging
import traceback
import hashlib

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.x25519 import (X25519PrivateKey,
                                                              X25519PublicKey)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from nacl.bindings import (crypto_kx_client_session_keys,
                           crypto_kx_server_session_keys,
                           crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.public import PrivateKey

from cli_code.crypt4gh.crypt4gh import lib
from cli_code.exceptions_ds import HashException, EncryptionError
from cli_code import LOG_FILE
# from cli_code.file_handler import config_logger
# from cli_code.database_connector import DatabaseConnector

SEGMENT_SIZE = 65536
MAGIC_NUMBER = b'crypt4gh'
VERSION = 1

# CRYPTO_LOG = logging.getLogger(__name__)
# CRYPTO_LOG.setLevel(logging.DEBUG)

# CRYPTO_LOG = config_logger(
#     logger=CRYPTO_LOG, filename=LOG_FILE,
#     file=True, file_setlevel=logging.DEBUG,
#     fh_format="%(asctime)s::%(levelname)s::" +
#     "%(name)s::%(lineno)d::%(message)s",
#     stream=True, stream_setlevel=logging.DEBUG,
#     sh_format="%(levelname)s::%(name)s::" +
#     "%(lineno)d::%(message)s"
# )


class Encryptor():

    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        '''Allows for implementation using "with" statement.
        Tear it down. Delete class.'''

        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True


class ECDHKey:

    def __init__(self, peer_public):
        '''Generate public key pair'''

        # Generate private key
        self.private = X25519PrivateKey.generate()
        # CRYPTO_LOG.log(private_key)
        # self.private = private_key.private_bytes(
        #     encoding=serialization.Encoding.Raw,
        #     format=serialization.PrivateFormat.Raw,
        #     encryption_algorithm=serialization.NoEncryption()
        # )
        # self.private = private_bytes.hex().upper()

        # Generate public
        self.public = self.private.public_key()
        # self.public = public_key.public_bytes(
        #     encoding=serialization.Encoding.Raw,
        #     format=serialization.PublicFormat.Raw
        # )
        # self.public = public_bytes.hex().upper()

        # Save peer public key
        self.peerpub = peer_public

        # Get shared, derived key
        self.derived = self._generate_encryption_key()

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

    def _generate_encryption_key(self):
        # Generate shared key
        shared = (self.private).exchange(peer_public_key=self.peerpub)

        # Generate derived key - used for data encryption
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'handshake data',
            backend=default_backend()
        ).derive(shared)

        return derived_key


def get_project_key(proj_id):
    from cli_code.database_connector import DatabaseConnector
    with DatabaseConnector('project_db') as project_db:
        public_bytes = bytes.fromhex(
            project_db[proj_id]['project_keys']['public'])
        return X25519PublicKey.from_public_bytes(public_bytes)


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

    # Split scrypt settings into parts
    settings = password_settings.split("$")
    for i in [1, 2, 3, 4]:
        settings[i] = int(settings[i])  # Set settings as int, not str

    # Create cryptographically secure password hash
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
