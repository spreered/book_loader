"""
Configuration management for book-loader.
"""

import os
from pathlib import Path


class Config:
    """Global configuration manager."""

    def __init__(self, auth_dir=None):
        """
        Args:
            auth_dir: Authorization directory path (optional)
        """
        self.auth_dir = self._get_auth_dir(auth_dir)

    @staticmethod
    def _get_auth_dir(custom_dir=None) -> Path:
        """
        Get authorization directory with priority order:
        1. Custom directory (--auth-dir parameter)
        2. Environment variable BOOK_LOADER_AUTH_DIR
        3. ~/.config/book-loader/.adobe/
        """
        if custom_dir:
            return Path(custom_dir)

        if env_dir := os.getenv("BOOK_LOADER_AUTH_DIR"):
            return Path(env_dir)

        config_dir = Path.home() / ".config" / "book-loader" / ".adobe"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
