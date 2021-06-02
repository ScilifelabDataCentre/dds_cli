"""Custom Exception classes"""


class AuthenticationError(Exception):
    """Errors due to user authentication.

    Return the message with Rich no-entry-sign emoji either side.
    """
    def __str__(self):
        return f"\n:no_entry_sign: {self.message} :no_entry_sign:\n"

class UploadError(Exception):
    """Errores relating to file uploads"""
    pass
