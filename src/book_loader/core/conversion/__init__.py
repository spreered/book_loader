"""
Format conversion module.
"""

from pathlib import Path
from .epub_to_pdf import EpubToPdfConverter
from .calibre_wrapper import CalibreConverter


class ConversionEngine:
    """Unified conversion engine interface."""

    def __init__(self, engine: str = "python"):
        """
        Args:
            engine: Conversion engine, 'python' or 'calibre'
        """
        self.engine = engine

        if engine == "python":
            self.converter = EpubToPdfConverter()
        elif engine == "calibre":
            self.converter = CalibreConverter()
        else:
            raise ValueError(f"Unsupported conversion engine: {engine}")

    def convert_epub_to_pdf(self, epub_path: Path, pdf_path: Path) -> None:
        """
        Convert EPUB to PDF.

        Args:
            epub_path: EPUB file path
            pdf_path: Output PDF path
        """
        print(f"Converting using {self.engine} engine...")
        self.converter.convert(epub_path, pdf_path)
        print(f"✓ Conversion complete: {pdf_path}")


__all__ = ["ConversionEngine", "EpubToPdfConverter", "CalibreConverter"]
