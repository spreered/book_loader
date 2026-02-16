"""
Improved EPUB to PDF converter.
"""

import tempfile
import shutil
from pathlib import Path
from ebooklib import epub
from weasyprint import HTML, CSS
from io import BytesIO


class ImprovedEpubToPdfConverter:
    """Improved EPUB to PDF converter."""

    def convert(self, epub_path: Path, pdf_path: Path) -> None:
        """
        Convert EPUB to PDF (improved version).

        Args:
            epub_path: EPUB file path
            pdf_path: Output PDF path
        """
        # Read EPUB
        book = epub.read_epub(str(epub_path))

        # Use temporary directory for resources
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract all resources (images, fonts, CSS)
            self._extract_resources(book, temp_path)

            # Extract content in spine order
            html_content = self._extract_content_with_spine(book)

            # Collect all CSS
            css_content = self._extract_css(book)

            # Write HTML
            html_file = temp_path / "book.html"
            html_file.write_text(html_content, encoding="utf-8")

            # Write CSS
            css_file = temp_path / "styles.css"
            css_file.write_text(css_content, encoding="utf-8")

            # Convert to PDF
            HTML(filename=str(html_file), base_url=str(temp_path)).write_pdf(
                str(pdf_path),
                stylesheets=[CSS(filename=str(css_file))],
            )

    def _extract_resources(self, book, temp_path: Path) -> None:
        """Extract all resources (images, fonts, etc.)."""
        for item in book.get_items():
            if item.get_type() in [6, 7, 8]:  # IMAGE, FONT, STYLE
                file_path = temp_path / item.get_name()
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(item.get_content())

    def _extract_content_with_spine(self, book) -> str:
        """Extract content in spine order."""
        content_parts = []

        # Get metadata
        title = book.get_metadata("DC", "title")
        creator = book.get_metadata("DC", "creator")

        # HTML beginning
        content_parts.append(
            """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="styles.css">
</head>
<body>
"""
        )

        # Title page
        if title:
            content_parts.append(
                f'<div class="title-page">'
                f'<h1 class="book-title">{title[0][0]}</h1>'
            )
            if creator:
                content_parts.append(f'<p class="book-author">{creator[0][0]}</p>')
            content_parts.append("</div>")

        # Extract content in spine order
        spine = book.spine
        for item_id, _ in spine:
            item = book.get_item_with_id(item_id)
            if item and item.get_type() == 9:  # DOCUMENT
                try:
                    content = item.get_content().decode("utf-8")
                    # Extract body content
                    cleaned = self._extract_body_content(content)
                    if cleaned.strip():
                        content_parts.append(
                            f'<div class="chapter" id="{item_id}">{cleaned}</div>'
                        )
                except Exception as e:
                    print(f"Warning: Failed to extract {item_id}: {e}")

        content_parts.append("</body></html>")

        return "\n".join(content_parts)

    def _extract_body_content(self, html: str) -> str:
        """Extract body content, remove outer tags."""
        import re

        # Remove XML declaration and DOCTYPE
        html = re.sub(r"<\?xml[^>]*\?>", "", html)
        html = re.sub(r"<!DOCTYPE[^>]*>", "", html)

        # Extract body content
        body_match = re.search(
            r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE
        )
        if body_match:
            return body_match.group(1)

        # If no body, remove html and head tags
        html = re.sub(r"</?html[^>]*>", "", html, flags=re.IGNORECASE)
        html = re.sub(
            r"<head[^>]*>.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE
        )

        return html

    def _extract_css(self, book) -> str:
        """Extract and integrate all CSS."""
        css_parts = []

        # Base styles
        css_parts.append(
            """
/* Base settings */
@page {
    size: A4;
    margin: 2cm;
    @bottom-center {
        content: counter(page);
        font-size: 10pt;
        color: #666;
    }
}

body {
    font-family: "Noto Serif TC", "Microsoft JhengHei", "PingFang TC", "Apple LiGothic", serif;
    line-height: 1.8;
    font-size: 11pt;
    text-align: justify;
    hyphens: auto;
}

/* Title page */
.title-page {
    page-break-after: always;
    text-align: center;
    padding-top: 5cm;
}

.book-title {
    font-size: 28pt;
    font-weight: bold;
    margin-bottom: 2cm;
}

.book-author {
    font-size: 16pt;
    color: #666;
}

/* Chapters */
.chapter {
    page-break-before: always;
}

h1, h2, h3, h4, h5, h6 {
    page-break-after: avoid;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
    font-weight: bold;
}

h1 { font-size: 20pt; }
h2 { font-size: 16pt; }
h3 { font-size: 14pt; }
h4 { font-size: 12pt; }

p {
    margin: 0.5em 0;
    text-indent: 2em;
    orphans: 2;
    widows: 2;
}

/* Images */
img {
    max-width: 100%;
    height: auto;
    page-break-inside: avoid;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    page-break-inside: avoid;
}

/* Code */
pre, code {
    font-family: "Courier New", monospace;
    font-size: 10pt;
    background-color: #f5f5f5;
    padding: 0.2em 0.4em;
}

pre {
    white-space: pre-wrap;
    padding: 1em;
    margin: 1em 0;
    page-break-inside: avoid;
}

/* Blockquotes */
blockquote {
    margin: 1em 2em;
    padding-left: 1em;
    border-left: 3px solid #ccc;
    font-style: italic;
}
"""
        )

        # Extract CSS from EPUB
        for item in book.get_items():
            if item.get_type() == 8:  # STYLE
                try:
                    css = item.get_content().decode("utf-8")
                    css_parts.append(f"\n/* From {item.get_name()} */\n{css}")
                except Exception as e:
                    print(f"Warning: Failed to extract CSS from {item.get_name()}: {e}")

        return "\n".join(css_parts)
