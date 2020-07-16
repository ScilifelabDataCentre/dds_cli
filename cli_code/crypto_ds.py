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
from cli_code import LOG_FILE, DS_MAGIC
from cli_code.exceptions_ds import DeliverySystemException, printout_error
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

    def __init__(self, keys=()):
        '''Generate public key pair'''

        # If put -> keys will be empty tuple -> Generate new key pair
        # If get -> keys will be project public & private from db
        if not keys:
            # Generate private key
            self.private = X25519PrivateKey.generate()

            # Generate public
            self.public = self.private.public_key()
        else:
            public, private = keys
            # X25519PrivateKey from project private key
            self.private = X25519PrivateKey.from_private_bytes(private)

            # X25519PublicKey from project public key
            self.public = X25519PublicKey.from_public_bytes(public)

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

    # def generate_ecdh_keypair(self):
    #     private = X25519PrivateKey.generate()
    #     public = private.public_key()
    #     return private, public

    def public_to_hex(self):
        return self.public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ).hex().upper()

    def generate_encryption_key(self, peer_public: bytes, salt_=""):
        '''Generate shared symmetric encryption key using peer public key
        and own public and private key'''

        # Put -> salt will be empty string -> generate new salt
        # Get -> salt will be hex string from db -> get as bytes
        salt = os.urandom(16) if salt_ == "" else bytes.fromhex(salt_)

        # X25519PublicKey from peer public key (from db)
        loaded_peer_pub = X25519PublicKey.from_public_bytes(peer_public)

        # Generate shared key
        shared = (self.private).exchange(peer_public_key=loaded_peer_pub)

        # Generate derived key from shared key - used for data encryption
        # Guarantees enough entropy in key
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b'handshake data',
            backend=default_backend()
        ).derive(shared)

        return derived_key, salt

    def del_priv_key(self):
        self.private = None


def get_project_private(proj_id: str, user):
    '''Gets the project private key from the database - only while downloading.

    -------------------------Format in database:-------------------------------
    len(magic) + magic + len(projID) + projID + len(privateKey) + privateKey
    ---------------------------------------------------------------------------

    Args:
        proj_id (str):      Project ID
        user (_DSUser):     User object with info on username, password, etc

    Returns:
        bytes:  Private key belonging to current project

    '''

    # NOTE: Solution to import issue?
    # Import here due to import issues.
    from cli_code.database_connector import DatabaseConnector

    with DatabaseConnector() as couch:
        # User DB specific ################################# User DB specific #
        user_db = couch['user_db']

        # Salt for deriving key used to encrypt/decrypt secret key
        key_salt = bytes.fromhex(user_db[user.id]['password']['key_salt'])

        # Derive key-encryption-key
        kdf = Scrypt(salt=key_salt, length=32, n=2**14,
                     r=8, p=1, backend=default_backend())
        key = kdf.derive(user.password.encode('utf-8'))

        user_db = None  # "Remove" user_db --> save space
        # --------------------------------------------------------------------#

        # Project DB specific ########################### Project DB specific #
        project_db = couch['project_db']

        # Get encrypted private key and nonce from DB
        encrypted_key = bytes.fromhex(
            project_db[proj_id]['project_keys']['secret']
        )
        nonce = bytes.fromhex(project_db[proj_id]['project_keys']['nonce'])

        # Decrypt key
        decrypted_key = crypto_aead_chacha20poly1305_ietf_decrypt(
            ciphertext=encrypted_key, aad=None, nonce=nonce, key=key
        )
        project_db = None   # "Remove" project_db --> save space
        # --------------------------------------------------------------------#

        # Verify key ############################################# Verify key #
        # Get length of magic id
        start = 0
        to_read = 2
        magic_id_len = int.from_bytes(
            decrypted_key[start:start+to_read], 'big')

        # Read magic_id_len bytes -> magic id - should be b'DelSys'
        start += to_read
        to_read = magic_id_len
        magic_id = decrypted_key[start:start+to_read]
        if magic_id != DS_MAGIC:
            sys.exit(printout_error("Error in private key! Signature should be"
                                    f"{DS_MAGIC} but found {magic_id}"))

        # Get length of project id
        start += to_read
        to_read = 2
        proj_len = int.from_bytes(decrypted_key[start:start+to_read], 'big')

        # Read proj_len bytes -> project id - should be equal to current proj
        start += to_read
        to_read = proj_len
        project_id = decrypted_key[start:start+to_read]
        if project_id != bytes(proj_id, encoding='utf-8'):
            sys.exit(printout_error("Error in private key! "
                                    "Project ID incorrect!"))

        # Get length of private key
        start += to_read
        to_read = 2
        key_len = int.from_bytes(decrypted_key[start:start+to_read], 'big')

        # Read key_len bytes -> key
        start += to_read
        to_read = key_len
        key = decrypted_key[start:start+to_read]

        # Error if there are bytes left after read key
        if decrypted_key[start+to_read::] != b'':
            sys.exit(printout_error("Error in private key! Extra bytes after"
                                    "key -- parsing failed or key corrupted!"))
        # --------------------------------------------------------------------#
        
        return key


def get_project_public(proj_id) -> (bytes):
    '''Gets the projects public key from the database

    Args:
        proj_id (str):  Project ID

    Returns:
        bytes:  ECDH Public key belonging to specific project.

    '''

    # NOTE: Solution to import issue?
    # Import here due to import issues.
    from cli_code.database_connector import DatabaseConnector

    try:
        # Get project public key - same for both put and get
        # and convert to bytes
        with DatabaseConnector('project_db') as project_db:
            public_key = bytes.fromhex(
                project_db[proj_id]['project_keys']['public']
            )
    except DeliverySystemException as dse:
        sys.exit(printout_error(dse))
    else:
        return public_key


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
