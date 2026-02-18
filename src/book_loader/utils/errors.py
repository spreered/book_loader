"""
Custom exception classes for book-loader.
"""


class BookLoaderError(Exception):
    """Base exception class for all book-loader errors."""

    pass


class AuthorizationError(BookLoaderError):
    """Raised when Adobe authorization fails."""

    pass


class ACSMFulfillmentError(BookLoaderError):
    """Raised when ACSM fulfillment fails."""

    pass


class DRMRemovalError(BookLoaderError):
    """Raised when DRM removal fails."""

    pass


class CalibreNotFoundError(BookLoaderError):
    """Raised when Calibre is not installed."""

    pass


class WorkflowError(BookLoaderError):
    """Raised when workflow processing encounters an error."""

    pass


class KoboLibraryNotFoundError(BookLoaderError):
    """Raised when the Kobo Desktop Edition library or database cannot be found."""

    pass


class KoboDecryptionError(BookLoaderError):
    """Raised when Kobo KEPUB decryption fails."""

    pass
