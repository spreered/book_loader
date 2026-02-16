"""
Command-line interface.
"""

import sys
import click
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError
from .core.workflow import BookLoader
from .utils.config import Config
from .utils.errors import BookLoaderError


def get_version() -> str:
    """Get package version from metadata."""
    try:
        return version("book-loader")
    except PackageNotFoundError:
        return "0.1.0"  # Fallback for development


@click.group()
@click.version_option(version=get_version())
def cli():
    """book-loader - Adobe ACSM ebook DRM removal tool

    Supports anonymous and Adobe ID authorization without Adobe Digital Editions.
    """
    pass


@cli.command()
@click.argument("acsm_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output directory (default: current directory)",
)
@click.option(
    "--auth-dir",
    type=click.Path(exists=True, path_type=Path),
    help="Authorization directory path (e.g., ADE authorization directory)",
)
@click.option("--optimize/--no-optimize", default=False, help="Optimize EPUB (not yet implemented)")
@click.option("--to-pdf", is_flag=True, help="Convert to PDF")
@click.option(
    "--convert-engine",
    type=click.Choice(["python", "calibre"]),
    default="python",
    help="PDF conversion engine: python (default) or calibre",
)
@click.option("--keep-encrypted", is_flag=True, help="Keep encrypted file")
def process(acsm_file, output, auth_dir, optimize, to_pdf, convert_engine, keep_encrypted):
    """Process ACSM file and output DRM-free EPUB or PDF

    Examples:

        book-loader process book.acsm

        book-loader process book.acsm -o ~/Books/

        book-loader process book.acsm --optimize --to-pdf
    """
    try:
        config = Config(auth_dir=auth_dir)
        loader = BookLoader(config)

        output_dir = output or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        result_path = loader.process_acsm(
            acsm_path=acsm_file,
            output_dir=output_dir,
            optimize=optimize,
            to_pdf=to_pdf,
            convert_engine=convert_engine,
            keep_encrypted=keep_encrypted,
        )

        click.secho(f"\n✓ Success! Output file: {result_path}", fg="green", bold=True)

    except BookLoaderError as e:
        click.secho(f"\n✗ Error: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"\n✗ Unexpected error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.group()
def auth():
    """Authorization management commands"""
    pass


@auth.command("create")
@click.option(
    "--anonymous",
    "auth_type",
    flag_value="anonymous",
    default=True,
    help="Use anonymous authorization (default)",
)
@click.option("--adobe-id", "auth_type", flag_value="adobe_id", help="Use Adobe ID authorization")
@click.option("--email", help="Adobe ID account (email)")
@click.option("--password", help="Adobe ID password")
def create_auth(auth_type, email, password):
    """Create authorization

    Examples:

        book-loader auth create --anonymous

        book-loader auth create --adobe-id --email your@email.com
    """
    try:
        config = Config()
        loader = BookLoader(config)

        if loader.account.is_authorized():
            click.secho(
                "⚠ Authorization already exists, please run 'book-loader auth reset' first", fg="yellow"
            )
            return

        if auth_type == "anonymous":
            click.echo("Creating anonymous authorization...")
            loader.account.authorize_anonymous()
            click.secho("✓ Anonymous authorization completed", fg="green", bold=True)
        else:  # adobe_id
            if not email:
                email = click.prompt("Adobe ID (email)")
            if not password:
                password = click.prompt("Password", hide_input=True)

            click.echo(f"Creating Adobe ID authorization: {email}...")
            loader.account.authorize_adobe_id(email, password)
            click.secho(f"✓ Adobe ID authorization completed: {email}", fg="green", bold=True)

    except BookLoaderError as e:
        click.secho(f"✗ Authorization failed: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg="red", err=True)
        sys.exit(1)


@auth.command("info")
def auth_info():
    """Display authorization information

    Examples:

        book-loader auth info
    """
    try:
        config = Config()
        loader = BookLoader(config)

        click.echo(f"Authorization directory: {config.auth_dir}")

        if loader.account.is_authorized():
            auth_type = loader.account.get_auth_type()
            auth_type_display = {
                "anonymous": "Anonymous",
                "AdobeID": "Adobe ID",
            }.get(auth_type, auth_type)

            click.secho(f"Authorization status: Authorized ✓", fg="green")
            click.echo(f"Authorization type: {auth_type_display}")
        else:
            click.secho(f"Authorization status: Not authorized", fg="yellow")
            click.echo("\nHint: Run 'book-loader auth create' to create authorization")

    except Exception as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        sys.exit(1)


@auth.command("reset")
@click.confirmation_option(prompt="Are you sure you want to reset authorization? This will delete all authorization files")
def reset_auth():
    """Reset authorization (delete authorization files)

    Examples:

        book-loader auth reset
    """
    try:
        config = Config()
        loader = BookLoader(config)

        loader.account.reset()
        click.secho("✓ Authorization reset", fg="green", bold=True)

    except Exception as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.argument("epub_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output PDF file path",
)
@click.option(
    "--convert-engine",
    type=click.Choice(["python", "calibre"]),
    default="python",
    help="Conversion engine: python (default) or calibre",
)
def convert(epub_file, output, convert_engine):
    """Convert EPUB to PDF

    Examples:

        book-loader convert book.epub

        book-loader convert book.epub -o output.pdf

        book-loader convert book.epub --convert-engine calibre
    """
    try:
        from .core.conversion import ConversionEngine

        # Determine output path
        if output:
            pdf_path = output
        else:
            pdf_path = epub_file.with_suffix(".pdf")

        # Convert
        engine = ConversionEngine(engine=convert_engine)
        engine.convert_epub_to_pdf(epub_file, pdf_path)

        click.secho(f"\n✓ Success! Output file: {pdf_path}", fg="green", bold=True)

    except Exception as e:
        click.secho(f"\n✗ Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
def info():
    """Display system information

    Examples:

        book-loader info
    """
    try:
        config = Config()
        loader = BookLoader(config)

        click.echo("=== Book Loader System Information ===\n")
        click.echo(f"Version: {get_version()}")
        click.echo(f"Authorization directory: {config.auth_dir}")

        if loader.account.is_authorized():
            auth_type = loader.account.get_auth_type()
            click.secho(f"Authorization status: Authorized ✓", fg="green")
            click.echo(f"Authorization type: {auth_type}")
        else:
            click.secho(f"Authorization status: Not authorized", fg="yellow")

        # Check if Calibre is available
        from .core.conversion.calibre_wrapper import CalibreConverter
        calibre = CalibreConverter()
        if calibre.is_available():
            click.secho(f"Calibre: Available ✓", fg="green")
        else:
            click.echo(f"Calibre: Not installed")

    except Exception as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
