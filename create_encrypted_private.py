# Standard library
import logging
import os
import sys
import traceback

# Installed
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (X25519PrivateKey,
                                                              X25519PublicKey)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from nacl.bindings import (crypto_aead_chacha20poly1305_ietf_decrypt,
                           crypto_aead_chacha20poly1305_ietf_encrypt)

DS_MAGIC = b'DelSys'
proj_id = 1
proj_id_bytes = (proj_id).to_bytes(2, byteorder='big')

password = "password1"

# Generate keys
private = X25519PrivateKey.generate()
print(f"private key: {private}")
private_bytes = private.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption()
)
print(f"private bytes: {private_bytes}")
public = private.public_key()
print(f"public key: {public}")

# Salt
salt = os.urandom(16)
print(f"salt: {salt}")

# Derive key-encryption-key
kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1,
             backend=default_backend())
derived_key = kdf.derive(password.encode('utf-8'))
print(f"derived key-encryption-key: {derived_key}")

decrypted_key = len(DS_MAGIC).to_bytes(2, byteorder='big') + DS_MAGIC + \
    len(proj_id_bytes).to_bytes(2, byteorder='big') + proj_id_bytes + \
    len(private_bytes).to_bytes(2, byteorder='big') + private_bytes
print(f"key for db: {decrypted_key}")

# Verify key ############################################# Verify key #
# Get length of magic id
start = 0
to_read = 2
magic_id_len = int.from_bytes(
    decrypted_key[start:start+to_read], 'big')
print(f"magic_id_len: {magic_id_len}")

# Read magic_id_len bytes -> magic id - should be b'DelSys'
start += to_read
to_read = magic_id_len
magic_id = decrypted_key[start:start+to_read]
if magic_id != DS_MAGIC:
    sys.exit("Error in private key! Signature should be"
             f"{DS_MAGIC} but found {magic_id}")
print(f"magic id: {magic_id}")

# Get length of project id
start += to_read
to_read = 2
proj_len = int.from_bytes(decrypted_key[start:start+to_read], 'big')
print(f"project id len: {proj_len}")

# Read proj_len bytes -> project id - should be equal to current proj
start += to_read
to_read = proj_len
project_id = decrypted_key[start:start+to_read]
if project_id != proj_id_bytes:
    sys.exit("Error in private key! "
             "Project ID incorrect!")
print(f"project id: {project_id}")

# Get length of private key
start += to_read
to_read = 2
key_len = int.from_bytes(decrypted_key[start:start+to_read], 'big')
print(f"key length: {key_len}")

# Read key_len bytes -> key
start += to_read
to_read = key_len
key = decrypted_key[start:start+to_read]
print(f"key: {key}")

# Error if there are bytes left after read key
if decrypted_key[start+to_read::] != b'':
    sys.exit("Error in private key! Extra bytes after"
             "key -- parsing failed or key corrupted!")

print(f"\nTo encrypt:\n{decrypted_key}")

nonce = os.urandom(12)
print(f"nonce: {nonce}")

encrypted_key = crypto_aead_chacha20poly1305_ietf_encrypt(
    message=decrypted_key, aad=None, nonce=nonce, key=derived_key
)
print(f"encrypted key: {encrypted_key}")

hex_private_encrypted = encrypted_key.hex().upper()
print(f"to add to db: {hex_private_encrypted}")
print(f"salt: {salt.hex().upper()}")
print(f"nonce: {nonce.hex().upper()}")

# decrypted_key = crypto_aead_chacha20poly1305_ietf_decrypt(ciphertext=encrypted_key, aad=None, nonce=nonce, key=)