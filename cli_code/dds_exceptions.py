"""Exceptions specific to the Data Delivery System.

Used in places where there are no other suitable Exceptions, either general or module
specific.
"""


class ChecksumError(Exception):
    """Errors regarding the generation of checksums."""
