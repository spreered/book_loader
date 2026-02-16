"""
Calibre conversion engine wrapper.
"""

import subprocess
import shutil
from pathlib import Path


class CalibreConverter:
    """Calibre conversion engine wrapper."""

    def is_available(self) -> bool:
        """Check if Calibre is available."""
        return shutil.which("ebook-convert") is not None

    def convert(self, epub_path: Path, pdf_path: Path) -> None:
        """
        Convert EPUB to PDF using Calibre.

        Args:
            epub_path: EPUB file path
            pdf_path: Output PDF path

        Raises:
            FileNotFoundError: Calibre not installed
            subprocess.CalledProcessError: Conversion failed
        """
        if not self.is_available():
            raise FileNotFoundError(
                "Calibre not installed. Please run: brew install calibre\n"
                "Or download from https://calibre-ebook.com/download"
            )

        # Execute ebook-convert (using Calibre default settings)
        # Users can customize parameters through Calibre's config files
        cmd = [
            "ebook-convert",
            str(epub_path),
            str(pdf_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                output=result.stdout,
                stderr=result.stderr
            )
