"""Shared constants used in the DDS CLI.

Using this will avoid e.g. circular imports and
make it easier to maintain.

TODO: Move other constants here from __init__.py.
"""

# perform_request_with_retry retries once on an answer with one of these status codes
# AND without a JSON body (NonJsonResponseError). Such an answer comes from the proxy
# (Traefik), not from the DDS API: a 502 there usually means the backend closed an idle
# connection, i.e. the request did not reach the backend.
# The status code alone is not enough: a 503 WITH a JSON body comes from the DDS API
# (maintenance, ServiceUnavailableError) and must never be retried.
API_NON_JSON_RETRY_STATUS_CODES = (502, 503)
API_RETRY_WAIT = 1  # seconds

# Timeout settings for upload and download
READ_TIMEOUT = 300
CONNECT_TIMEOUT = 60

# Retry settings for download.
# DOWNLOAD_MAX_RETRIES counts only attempts in a row without progress: an attempt that
# received new data starts the count (and the wait) again, so a file can be resumed
# any number of times. With these values a server that does not answer at all is
# given up after 7 attempts and 1 + 2 + 4 + 8 + 16 + 32 = 63 seconds of waiting,
# enough to ride out a short restart of the storage or the proxy.
DOWNLOAD_MAX_RETRIES = 7
DOWNLOAD_BACKOFF_FACTOR = 2
DOWNLOAD_INITIAL_WAIT = 1  # seconds

# Import these constants when using '*'
__all__ = [
    "API_NON_JSON_RETRY_STATUS_CODES",
    "API_RETRY_WAIT",
    "READ_TIMEOUT",
    "CONNECT_TIMEOUT",
    "DOWNLOAD_MAX_RETRIES",
    "DOWNLOAD_BACKOFF_FACTOR",
    "DOWNLOAD_INITIAL_WAIT",
]
