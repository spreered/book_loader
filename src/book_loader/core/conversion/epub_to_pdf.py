"""
EPUB to PDF converter.
"""

import tempfile
import shutil
from pathlib import Path
from ebooklib import epub
from weasyprint import HTML, CSS
from io import BytesIO


class EpubToPdfConverter:
    """EPUB to PDF converter (pure Python implementation)."""

    def convert(self, epub_path: Path, pdf_path: Path) -> None:
        """
        Convert EPUB to PDF.

        Args:
            epub_path: EPUB file path
            pdf_path: Output PDF path
        """
        # Read EPUB
        book = epub.read_epub(str(epub_path))

        # Extract all documents
        html_content = self._extract_content(book)

        # Process images
        images = self._extract_images(book)

        # Use temporary directory for resources
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write images
            for img_name, img_data in images.items():
                img_path = temp_path / img_name
                img_path.parent.mkdir(parents=True, exist_ok=True)
                img_path.write_bytes(img_data)

            # Write HTML
            html_file = temp_path / "book.html"
            html_file.write_text(html_content, encoding="utf-8")

            # Convert to PDF
            HTML(filename=str(html_file), base_url=str(temp_path)).write_pdf(
                str(pdf_path)
            )

    def _extract_content(self, book) -> str:
        """Extract HTML content from EPUB."""
        content_parts = []

        # Add basic CSS
        content_parts.append(
            """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: "Noto Serif TC", "Microsoft JhengHei", serif;
                    line-height: 1.8;
                    margin: 2cm;
                    font-size: 12pt;
                }
                h1 { font-size: 24pt; margin-top: 2cm; }
                h2 { font-size: 20pt; margin-top: 1.5cm; }
                h3 { font-size: 16pt; margin-top: 1cm; }
                p { text-align: justify; margin: 0.5cm 0; text-indent: 2em; }
                img { max-width: 100%; height: auto; }
                @page {
                    size: A4;
                    margin: 2cm;
                }
            </style>
        </head>
        <body>
        """
        )

        # Get book title
        title = book.get_metadata("DC", "title")
        if title:
            content_parts.append(f"<h1>{title[0][0]}</h1>")

        # Get author
        creator = book.get_metadata("DC", "creator")
        if creator:
            content_parts.append(f"<p><strong>Author: {creator[0][0]}</strong></p>")

        content_parts.append("<hr/>")

        # Extract all document content
        for item in book.get_items():
            if item.get_type() == 9:  # EBOOKLIB.ITEM_DOCUMENT
                try:
                    content = item.get_content().decode("utf-8")
                    # Remove HTML and body tags, keep only content
                    content = self._clean_html(content)
                    content_parts.append(content)
                except Exception as e:
                    print(f"Warning: Failed to extract content from {item.get_name()}: {e}")

        content_parts.append("</body></html>")

        return "\n".join(content_parts)

    def _clean_html(self, html: str) -> str:
        """Clean HTML, remove outer tags."""
        # Simple cleaning: remove <?xml>, <!DOCTYPE>, <html>, <head>, <body> tags
        import re

        # Remove XML declaration
        html = re.sub(r"<\?xml[^>]*\?>", "", html)
        # Remove DOCTYPE
        html = re.sub(r"<!DOCTYPE[^>]*>", "", html)
        # Extract body content
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
        if body_match:
            html = body_match.group(1)
        # Remove html tags
        html = re.sub(r"</?html[^>]*>", "", html, flags=re.IGNORECASE)
        # Remove head tags and content
        html = re.sub(r"<head[^>]*>.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE)

        return html

    def _extract_images(self, book) -> dict:
        """Extract images from EPUB."""
        images = {}

        for item in book.get_items():
            if item.get_type() == 6:  # EBOOKLIB.ITEM_IMAGE
                images[item.get_name()] = item.get_content()

        return images
