import sys
import os
from pathlib import Path
import io
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from nacl.bindings import (crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.exceptions import CryptoError

from code_api.crypt4gh.crypt4gh import lib, header
import code_api.crypt4gh.crypt4gh.keys.c4gh as keys
from code_api.crypt4gh.crypt4gh.keys.c4gh import MAGIC_WORD, parse_private_key

from code_api.dp_exceptions import HashException, EncryptionError

SEGMENT_SIZE = 65536


class Crypt4GHKey:

    def __init__(self):

        self.public, self.secret = keys.generate()
        # print("public: ", self.public)
        # print("secret: ", self.secret)

        # correct private key
        lines_pub = self.public.splitlines()
        assert(b'CRYPT4GH' in lines_pub[0])
        self.public_parsed = b64decode(b''.join(lines_pub[1:-1]))
        # print(self.public_parsed)

        # correct secret key
        lines = self.secret.splitlines()
        assert(lines[0].startswith(b'-----BEGIN ') and
               lines[-1].startswith(b'-----END '))
        data = b64decode(b''.join(lines[1:-1]))

        stream = io.BytesIO(data)

        magic_word = stream.read(len(MAGIC_WORD))
        if magic_word == MAGIC_WORD:  # it's a crypt4gh key
            self.secret_decrypted = parse_private_key(stream)
            # print(self.secret_decrypted)

    def encrypt(self, recip_pubkey, infile, outfile, offset=0, span=None):
        '''Encrypt infile into outfile, using the list of keys.


        It fast-forwards to `offset` and encrypts until
        a total of `span` bytes is reached (or to EOF if `span` is None)

        This produces a Crypt4GH file without edit list.
        '''

        # Preparing the encryption engine
        encryption_method = 0  # only choice for this version
        session_key = os.urandom(32)  # we use one session key for all blocks

        # Output the header
        header_content = header.make_packet_data_enc(encryption_method,
                                                     session_key)
        header_packets = header.encrypt(header_content, self.secret_decrypted,
                                        recip_pubkey)
        header_bytes = header.serialize(header_packets)

        with outfile.open(mode='wb+') as of:
            of.write(header_bytes)

        segment = bytearray(SEGMENT_SIZE)

        print("här")
        # The whole file
        with infile.open(mode='rb') as inf:
            print("opened")
            while True:
                segment_len = inf.readinto(segment)

                if segment_len == 0:  # finito
                    break

                if segment_len < SEGMENT_SIZE:  # not a full segment
                    # to discard the bytes from the previous segments
                    data = bytes(segment[:segment_len])
                    self._encrypt_segment(data, outfile, session_key)
                    break

                data = bytes(segment)  # this is a full segment
                self._encrypt_segment(data, outfile, session_key)

        return "ues"

    def _encrypt_segment(self, data, outfile, key):
        '''Utility function to generate a nonce, encrypt data with Chacha20, and authenticate it with Poly1305.'''

        nonce = os.urandom(12)
        encrypted_data = crypto_aead_chacha20poly1305_ietf_encrypt(
            data, None, nonce, key)  # no add

        # after producing the segment, so we don't start outputing when an error occurs
        with outfile.open(mode='ab') as of:
            of.write(nonce)
            of.write(encrypted_data)

    def prep_upload(self, file: str, recip_keys, tempdir):
        '''Prepares the files for upload'''

        filesdir = tempdir[1]
        file_suffixes = "".join(file.suffixes)
        file_stem = Path(file.name.split(file_suffixes)[0])
        print("File stem: ", file_stem)
        if isinstance(filesdir, Path):
            try:
                filesdir = filesdir / file_stem
                print("filesdir: ", filesdir)
                filesdir.mkdir(parents=True)
            except IOError as ioe:
                sys.exit(f"Could not create folder {filesdir}")

        # hash
        _, checksum = gen_hmac(file=file)
        # encrypt
        encrypted_file = filesdir / Path(file.name + ".c4gh")
        # sys.exit(encrypted_file)
        try:
            self.encrypt(recip_keys, file, encrypted_file)
        except EncryptionError as ee:
            sys.exit(f"Encryption of file {file} failed: {ee}")

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
