#!/usr/bin/env python3
"""Exceptions"""

# IMPORTS ############################################################ IMPORTS #
# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #
# CLASSES ############################################################ CLASSES #

class AuthenticationError(Exception):
    """Custom exception class. Handles errors regarding delivery portal authentications."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


class CouchDBException(Exception):
    """Custom exception class. Handles errors in database operations."""

    def __init__(self, msg: str):
        """Passes message from exception call to the base class __init__."""

        super().__init__(msg)


class DeliveryPortalException(Exception):
    """Custom exception class. Handles errors regarding Delivery Portal 
    access etc"""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)


class DeliveryOptionException(Exception):
    """Custom exception class. Handles errors regarding data delivery 
    options (s3 delivery) etc."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)
        

class SecurePasswordException(Exception):
    """Custom exception class. Handles errors regarding password retrieval and handling."""

    def __init__(self, msg: str):
        """Passes message from exception call to base class __init__."""
        super().__init__(msg)