"""File encryptor module"""

import pathlib
import traceback
import os
import logging
import sys
from cryptography.hazmat.primitives.asymmetric import x25519
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_encrypt

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

    def __init__(self):
        self.keys = x25519.X25519PrivateKey.generate()
        self.max_nonce = 2 ** (12 * 8)  # Max mumber of nonces

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            return False  # uncomment to pass exception through

        return True

    def encrypt_filechunks(
        self,
        chunks,
        outfile: pathlib.Path,
    ) -> (bytes, bytes):
        """Encrypts the file in chunks.

        Encrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
        construction described in RFC7539.

        Args:
            gen (Generator):    Generator object, stream of file chunks
            key (bytes):        Data encryption key
            iv (bytes):         Initial nonce

        Yields:
            tuple:  The nonce for each data chunk and ciphertext

                bytes:  Nonce -- number only used once
                bytes:  Ciphertext
        """

        aad = None
        # key = self.generate_shared_key()

        with outfile.open(mode="wb") as out:
            iv_bytes = os.urandom(12)
            out.write(iv_bytes)

            iv_int = int.from_bytes(iv_bytes, "little")
            nonce = b""
            for chunk in chunks:

                nonce = (
                    iv_int if iv_int < self.max_nonce else iv_int % self.max_nonce
                ).to_bytes(length=12, byteorder="little")
                iv_int += 1

                # do encryption here
                # encrypted_chunk = crypto_aead_chacha20poly1305_ietf_encrypt(
                #     message=chunk, aad=aad, nonce=nonce, key=key
                # )

                out.write(chunk)

            out.write(nonce)

    def generate_shared_key(self):

        salt = os.urandom(16)

        # loaded_peer_pub = x25519.X25519PublicKey.from_public_bytes()