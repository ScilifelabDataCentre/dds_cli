"""Cryptography-related functions required for the Data Delivery System.

Contains the ECDHKey class which generates a public key pair usable by
Elliptic-Curve Diffie-Hellman cryptography and transforms the keys to readable
hex strings. Also contains the function get_project_private() which gets the
project private key from the project database and parses it. This function
is only accessible by users downloading their data - not uploading.
"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import os
import sys
import traceback

# Installed
from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.kdf import hkdf
from cryptography.hazmat.primitives.kdf import scrypt
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_decrypt as decrypt
import requests

# Own modules
from cli_code import DS_MAGIC
from cli_code import ENDPOINTS
from cli_code import exceptions_ds

###############################################################################
# LOGGING ########################################################### LOGGING #
###############################################################################

CRYPTO_LOG = logging.getLogger(__name__)
CRYPTO_LOG.setLevel(logging.DEBUG)

###############################################################################
# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #
###############################################################################

SEGMENT_SIZE = 65536

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class ECDHKey:
    """
    Elliptic-Curve Diffie-Hellman key pair

    Attributes:
        private:    Private component
        public:     Public component, generated from private

    Methods:
        del_priv_key:               Deletes private key
        generate_encryption_key:    Derives shared data encryption key
        public_to_hex:              Converts public key to hex-string

    """

    #################
    # Magic Methods #
    #################
    def __init__(self, keys=()):
        """Generate ECDH key pair"""

        # If put -> keys will be empty tuple -> Generate new key pair
        # If get -> keys will be project public & private from db
        if not keys:
            # Generate private key
            self.private = x25519.X25519PrivateKey.generate()

            # Generate public
            self.public = self.private.public_key()
            # CRYPTO_LOG.debug(f"file public key: {self.public.public_bytes()}")
        else:
            public, private = keys
            # X25519PrivateKey from project private key
            self.private = x25519.X25519PrivateKey.from_private_bytes(private)

            # X25519PublicKey from project public key
            self.public = x25519.X25519PublicKey.from_public_bytes(public)

    def __enter__(self):
        """Allows for implementation using "with" statement.
        Building."""

        return self

    def __exit__(self, exc_type, exc_value, tb):
        """Allows for implementation using "with" statement.
        Tear it down. Delete class."""

        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def __repr__(self):

        return "<ECDHKey>"

    ##################
    # Public Methods #
    ##################

    def del_priv_key(self):
        """Sets private key to None - important that it's kept secret"""

        self.private = None

    def generate_encryption_key(self, peer_public: bytes, salt_: str = "") \
            -> (bytes, bytes):
        """Generate shared symmetric encryption key using peer public key
        and own public and private key

        Args:
            peer_public (bytes):    Public component of peer ECDH key pair
            salt_ (str):            Salt used for deriving shared key.
                                    '' if 'put' (default)

        Returns:
            tuple:  Derived key and salt
                bytes:   Derived shared key\n
                bytes:   Salt\n

        """

        # Put -> salt will be empty string -> generate new salt
        # Get -> salt will be hex string from db -> get as bytes
        salt = os.urandom(16) if salt_ == "" else bytes.fromhex(salt_)
        CRYPTO_LOG.debug("\nsalt:%s\t%s\n", salt, salt.hex().upper())

        # X25519PublicKey from peer public key (from db)
        loaded_peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public)
        CRYPTO_LOG.debug("\npeer public key: %s\n", peer_public)
        CRYPTO_LOG.debug("\nprivate key: %s\n",
                         self.private.private_bytes(
                             encoding=serialization.Encoding.Raw,
                             format=serialization.PrivateFormat.Raw,
                             encryption_algorithm=serialization.NoEncryption())
                         )

        # Generate shared key
        shared = (self.private).exchange(peer_public_key=loaded_peer_pub)
        CRYPTO_LOG.debug("\nshared:%s\t%s\n", shared, shared.hex().upper())

        # Generate derived key from shared key - used for data encryption
        # Guarantees enough entropy in key
        derived_key = hkdf.HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b"handshake data",
            backend=backends.default_backend()
        ).derive(shared)

        CRYPTO_LOG.debug("DERIVED: %s", derived_key)
        return derived_key, salt

    def public_to_hex(self) -> (str):
        """Converts public key to hex-string.

        Returns:
            str:    Hex representation of public key

        """

        return self.public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ).hex().upper()


###############################################################################
# FUNCTIONS ####################################################### FUNCTIONS #
###############################################################################

def get_project_private(proj_id: str, user, token):
    """Gets the project private key from the database - only while downloading.

    -------------------------Format in database:-------------------------------
    len(magic) + magic + len(projID) + projID + len(privateKey) + privateKey
    ---------------------------------------------------------------------------

    Args:
        proj_id (str):      Project ID
        user (_DSUser):     User object with info on username, password, etc

    Returns:
        bytes:  Private key belonging to current project

    """

    # Perform request to ProjectKey - get encrypted and formatted private key
    req = ENDPOINTS["key"] + f"{proj_id}/key/{token}"
    response = requests.get(req)

    # Cancel delivery if request error
    if not response.ok:
        sys.exit(
            exceptions_ds.printout_error(
                f"{response.status_code} - {response.reason}: \n{req}"
            )
        )

    # Get json response if request ok
    key_info = response.json()
    CRYPTO_LOG.debug("private key info: %s", key_info)

    # Salt for deriving key used to encrypt/decrypt secret key
    key_salt = bytes.fromhex(key_info["salt"])
    CRYPTO_LOG.debug("salt in hex: %s", key_info["salt"])
    CRYPTO_LOG.debug("salt: %s", key_salt)

    # Derive key-encryption-key
    kdf = scrypt.Scrypt(salt=key_salt, length=32, n=2**14,
                        r=8, p=1, backend=backends.default_backend())

    CRYPTO_LOG.debug("password: %s", user.password)
    key_enc_key = kdf.derive(user.password.encode("utf-8"))
    CRYPTO_LOG.debug("key: %s", key_enc_key)

    CRYPTO_LOG.debug("encrypted key in hex: %s", key_info["encrypted_key"])

    # Get encrypted private key and nonce from DB
    encrypted_key = bytes.fromhex(key_info["encrypted_key"])
    CRYPTO_LOG.debug("\nencrypted key in db: %s\n", encrypted_key)

    nonce = bytes.fromhex(key_info["nonce"])
    CRYPTO_LOG.debug("nonce: %s --  in hex: %s", nonce, key_info["nonce"])

    # Decrypt key
    decrypted_key = decrypt(
        ciphertext=encrypted_key, aad=None, nonce=nonce, key=key_enc_key
    )

    # Verify key ############################################# Verify key #
    # Get length of magic id
    start = 0
    to_read = 2
    magic_id_len = int.from_bytes(
        decrypted_key[start:start+to_read], "big")

    # Read magic_id_len bytes -> magic id - should be b"DelSys"
    start += to_read
    to_read = magic_id_len
    magic_id = decrypted_key[start:start+to_read]
    if magic_id != DS_MAGIC:
        sys.exit(exceptions_ds.printout_error(
            "Error in private key! Signature should be"
            f"{DS_MAGIC} but found {magic_id}"
        ))

    # Get length of project id
    start += to_read
    to_read = 2
    proj_len = int.from_bytes(decrypted_key[start:start+to_read], "big")

    # Read proj_len bytes -> project id - should be equal to current proj
    start += to_read
    to_read = proj_len
    project_id = decrypted_key[start:start+to_read]
    if project_id != (proj_id).to_bytes(2, byteorder="big"):
        sys.exit(exceptions_ds.printout_error("Error in private key! "
                                              "Project ID incorrect!"))

    # Get length of private key
    start += to_read
    to_read = 2
    key_len = int.from_bytes(decrypted_key[start:start+to_read], "big")

    # Read key_len bytes -> key
    start += to_read
    to_read = key_len
    key = decrypted_key[start:start+to_read]

    # Error if there are bytes left after read key
    if decrypted_key[start+to_read::] != b"":
        sys.exit(exceptions_ds.printout_error(
            "Error in private key! Extra bytes after"
            "key -- parsing failed or key corrupted!"
        ))
    # --------------------------------------------------------------------#
    CRYPTO_LOG.info("key successfully decrypted: %s", key)
    return key
