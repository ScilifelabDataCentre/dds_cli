"""File encryptor module"""

import pathlib
import traceback
import os
import logging
import sys
from cryptography.hazmat import backends
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf import hkdf
from cryptography.hazmat.primitives import hashes
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_encrypt
from cryptography.hazmat.primitives import serialization


from cli_code import FileSegment

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class Encryptor:
    """Handles the encryption of the files."""

    def __init__(self, proj_priv_key=None):
        self.max_nonce = 2 ** (12 * 8)  # Max mumber of nonces
        self.private = (
            x25519.X25519PrivateKey.generate()
            if proj_priv_key is None
            else x25519.X25519PrivateKey.from_private_bytes(
                bytes.fromhex(proj_priv_key)
            )
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def encrypt_filechunks(
        self, chunks, outfile: pathlib.Path, key: bytes, progress: tuple = None
    ) -> (bytes, bytes):
        """Encrypts the file in chunks.

        Encrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
        construction described in RFC7539.
        """

        # Additional data
        aad = None

        # Save encryption output to file
        with outfile.open(mode="wb") as out:
            # Create and save first IV/nonce
            iv_bytes = os.urandom(12)
            out.write(iv_bytes)

            # Get first iv/nonce as integer
            iv_int = int.from_bytes(iv_bytes, "little")
            nonce = b""  # Catch last nonce
            for chunk in chunks:
                # Restart at 0 if nonce number at maximum number of chunks per key
                nonce = (
                    iv_int if iv_int < self.max_nonce else iv_int % self.max_nonce
                ).to_bytes(length=12, byteorder="little")

                # Encrypt chunk
                encrypted_chunk = crypto_aead_chacha20poly1305_ietf_encrypt(
                    message=chunk, aad=aad, nonce=nonce, key=key
                )
                out.write(encrypted_chunk)

                progress[0].advance(progress[1], FileSegment.SEGMENT_SIZE_RAW)
                iv_int += 1  # Increment nonce

            # Save last nonce
            out.write(nonce)

    def decrypt_file(self, infile: pathlib.Path, outfile: pathlib.Path, key: bytes):
        """Decryptes the file."""

        pass

    def generate_shared_key(self, peer_public: str, key_salt: str = None):
        """Derive the shared key for file encryption."""

        # Generate or from db
        salt = os.urandom(16) if key_salt is None else bytes.fromhex(key_salt)

        # Project public key
        peer_public_bytes = bytes.fromhex(peer_public)
        loaded_peer_public = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)

        # Generate shared key and derive encryption key with salt
        shared_key = (self.private).exchange(peer_public_key=loaded_peer_public)
        derived_shared_key = hkdf.HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b"",
            backend=backends.default_backend(),
        ).derive(shared_key)

        LOG.debug("Salt: %s", salt)
        LOG.debug("Derived shared key: %s", derived_shared_key)
        return derived_shared_key, salt.hex().upper()

    def public_to_hex(self):
        """Converts public key to hexstring."""

        public = self.private.public_key()
        public_bytes = public.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        return public_bytes.hex().upper()
