"""Shared constants used in the DDS CLI.

Using this will avoid e.g. circular imports and 
make it easier to maintain.

TODO: Move other constants here from __init__.py.
"""

# Timeout settings for upload and download
READ_TIMEOUT = 300
CONNECT_TIMEOUT = 60

# Retry settings for download
DOWNLOAD_MAX_RETRIES = 5
DOWNLOAD_BACKOFF_FACTOR = 2
DOWNLOAD_INITIAL_WAIT = 1  # seconds

# Import these constants when using '*'
__all__ = [
    "READ_TIMEOUT",
    "CONNECT_TIMEOUT",
    "DOWNLOAD_MAX_RETRIES",
    "DOWNLOAD_BACKOFF_FACTOR",
    "DOWNLOAD_INITIAL_WAIT",
]
