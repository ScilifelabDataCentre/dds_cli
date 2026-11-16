"""Shared constants used in the DDS CLI.

Using this will avoid e.g. circular imports and
make it easier to maintain.

TODO: Move other constants here from __init__.py.
"""

# Retry once on these API status codes, but only if the answer came from the proxy
# (Traefik, no JSON body). A 502 there usually means the backend closed an idle
# connection, i.e. the request did not reach the backend, so a retry is safe.
# A 503 from the DDS backend (maintenance) is never retried.
API_TRANSIENT_STATUS_CODES = (502, 503)
API_RETRY_WAIT = 1  # seconds

# Timeout settings for upload and download
READ_TIMEOUT = 300
CONNECT_TIMEOUT = 60

# Retry settings for download
DOWNLOAD_MAX_RETRIES = 5
DOWNLOAD_BACKOFF_FACTOR = 2
DOWNLOAD_INITIAL_WAIT = 1  # seconds

# Import these constants when using '*'
__all__ = [
    "API_TRANSIENT_STATUS_CODES",
    "API_RETRY_WAIT",
    "READ_TIMEOUT",
    "CONNECT_TIMEOUT",
    "DOWNLOAD_MAX_RETRIES",
    "DOWNLOAD_BACKOFF_FACTOR",
    "DOWNLOAD_INITIAL_WAIT",
]
