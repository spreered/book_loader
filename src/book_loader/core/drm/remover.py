"""
Unified DRM removal interface.
"""

from pathlib import Path
from ...utils.errors import DRMRemovalError


class DRMRemover:
    """Unified DRM removal interface."""

    def remove_drm(
        self, encrypted_path: Path, output_path: Path, user_key: bytes
    ) -> None:
        """
        Remove DRM from ebook.

        Args:
            encrypted_path: Encrypted file path
            output_path: Output file path
            user_key: RSA private key (DER format, extracted from Adobe account)

        Raises:
            DRMRemovalError: DRM removal failed
        """
        if not encrypted_path.exists():
            raise DRMRemovalError(f"Encrypted file not found: {encrypted_path}")

        suffix = encrypted_path.suffix.lower()

        try:
            if suffix == ".epub":
                self._decrypt_epub(encrypted_path, output_path, user_key)
            elif suffix == ".pdf":
                self._decrypt_pdf(encrypted_path, output_path, user_key)
            else:
                raise DRMRemovalError(f"Unsupported file format: {suffix}")

        except DRMRemovalError:
            raise
        except Exception as e:
            raise DRMRemovalError(f"DRM removal failed: {e}")

    def _decrypt_epub(
        self, encrypted_path: Path, output_path: Path, user_key: bytes
    ) -> None:
        """Decrypt EPUB file."""
        from .ineptepub import decryptBook

        result = decryptBook(user_key, str(encrypted_path), str(output_path))

        if result == 1:
            # File already has no DRM
            import shutil

            shutil.copy(str(encrypted_path), str(output_path))
        elif result != 0:
            raise DRMRemovalError(f"EPUB decryption failed, error code: {result}")

    def _decrypt_pdf(
        self, encrypted_path: Path, output_path: Path, user_key: bytes
    ) -> None:
        """Decrypt PDF file."""
        from .ineptpdf import decryptBook

        result = decryptBook(user_key, str(encrypted_path), str(output_path))

        if result == 1:
            # File already has no DRM
            import shutil

            shutil.copy(str(encrypted_path), str(output_path))
        elif result != 0:
            raise DRMRemovalError(f"PDF decryption failed, error code: {result}")
