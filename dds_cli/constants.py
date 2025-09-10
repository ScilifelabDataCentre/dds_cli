"""Shared constants used in the DDS CLI.

Using this will avoid e.g. circular imports and 
make it easier to maintain.

TODO: Move other constants here from __init__.py.
"""

# Timeout settings for upload and download
READ_TIMEOUT = 300
CONNECT_TIMEOUT = 60

# Import these constants when using '*'
__all__ = ["READ_TIMEOUT", "CONNECT_TIMEOUT"]
