from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

import sys

from code_api.dp_exceptions import HashException


def secure_password_hash(password_settings: str, password_entered: str) -> (str):
    '''Generates secure password hash.

    Args:
            password_settings:  String containing the salt, length of hash, n-exponential,
                                                    r and p variables. Taken from database. Separated by '$'.
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


def gen_hmac(file, upload: bool = True):
    '''Generates a HMAC for a file'''

    file_hash = hmac.HMAC(
        key=b'testing', algorithm=hashes.SHA256(), backend=default_backend())
    try:
        with file.open(mode='rb') as f:
            for chunk in iter(lambda: f.read(8388608), b''):
                file_hash.update(chunk)
    except HashException as he:
        sys.exit(f"HMAC for file {str(file)} could not be generated.")
    else:
        finalized = file_hash.finalize().hex()
        if upload:
            try:
                with open(file="checksum.txt", mode='w') as cf:
                    cf.write(finalized)
            except IOError as ioe:
                sys.exit("Could not save hash to file.")
        else:
            try:
                with open(file="checksum.txt", mode='r') as cf:
                    original = cf.read()
                    [print("SUCCESS!" if original == finalized
                           else print("FAILED CHECKSUM VERIFICATION!"))]
            except IOError as ioe2:
                sys.exit("Could not read hash from file.")
