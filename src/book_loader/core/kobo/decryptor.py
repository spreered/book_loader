"""
Kobo KEPUB decryption engine.
"""

import re
import shutil
import zipfile
from pathlib import Path

from Crypto.Cipher import AES

from ...utils.errors import KoboDecryptionError
from .library import KoboBook


def _unpad(data: bytes) -> bytes:
    """Remove PKCS#7 padding."""
    pad_len = data[-1]
    return data[:-pad_len]


def _check_decrypted_content(filename: str, contents: bytes) -> None:
    """
    Verify decrypted content looks valid based on file extension.
    Raises ValueError if the content appears to be incorrectly decrypted.
    """
    lower = filename.lower()
    if lower.endswith(".xhtml") or lower.endswith(".html") or lower.endswith(".htm"):
        # First few bytes should be printable ASCII
        for i in range(min(5, len(contents))):
            if contents[i] < 32 or contents[i] > 127:
                raise ValueError(f"Non-ASCII byte at position {i}: {contents[i]}")
    elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
        if len(contents) >= 3 and contents[:3] != b"\xff\xd8\xff":
            raise ValueError("Invalid JPEG magic bytes")


def _safe_filename(title: str) -> str:
    """Convert a book title to a safe filename."""
    return re.sub(r"[^\s\w]", "_", title, flags=re.UNICODE).strip() + ".epub"


class KoboDecryptor:
    """Decrypts Kobo KEPUB files by removing KDRM."""

    def decrypt_book(self, book: KoboBook, userkeys: list[bytes], output_dir: Path) -> Path:
        """
        Decrypt a Kobo book and save it as a standard EPUB.

        Args:
            book: The KoboBook to decrypt.
            userkeys: List of candidate user keys to try.
            output_dir: Directory where the output EPUB will be saved.

        Returns:
            Path to the output EPUB file.

        Raises:
            KoboDecryptionError: If decryption fails with all available keys.
        """
        output_path = output_dir / _safe_filename(book.title)

        if not book.has_drm:
            shutil.copyfile(book.filename, output_path)
            return output_path

        zin = zipfile.ZipFile(book.filename, "r")

        for userkey in userkeys:
            try:
                zout = zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED)
                for entry_name in zin.namelist():
                    contents = zin.read(entry_name)
                    if entry_name in book.encrypted_files:
                        encrypted_page_key = book.encrypted_files[entry_name]
                        # Layer 1: decrypt page key using userkey (AES-ECB)
                        page_key = AES.new(userkey, AES.MODE_ECB).decrypt(encrypted_page_key)
                        # Layer 2: decrypt content using page key (AES-ECB, PKCS#7)
                        contents = _unpad(AES.new(page_key, AES.MODE_ECB).decrypt(contents))
                        # Validate result looks correct (raises ValueError if wrong key)
                        _check_decrypted_content(entry_name, contents)
                    zout.writestr(entry_name, contents)
                zout.close()
                zin.close()
                return output_path
            except ValueError:
                zout.close()
                if output_path.exists():
                    output_path.unlink()

        zin.close()
        raise KoboDecryptionError(
            f"Failed to decrypt '{book.title}' — no valid key found. "
            "Make sure you are logged in to Kobo Desktop with the account that purchased the book."
        )
