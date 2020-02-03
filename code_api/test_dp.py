"""Test script to assert that different values are correct"""

import os
import sys
import gzip
import shutil
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend


def compress_file(original: str, compressed: str) -> None:
    """Compresses file using gzip"""

    with open(original, 'rb') as pathin:
        with gzip.open(compressed, 'wb') as pathout:
            shutil.copyfileobj(pathin, pathout)


def gen_hmac(filepath: str) -> str:
    """Generates HMAC for file"""

    key = b"ina"
    h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(16384), b''):
            h.update(chunk)

    return h.finalize().hex()
