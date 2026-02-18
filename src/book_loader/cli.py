"""
Command-line interface.
"""

import sys
import click
import tarfile
from datetime import datetime
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


def backup_auth(auth_dir: Path, backup_path: Path) -> Path:
    """
    Backup authorization files to a tar.gz archive.

    Args:
        auth_dir: Authorization directory to backup
        backup_path: Target backup file path

    Returns:
        Path to the created backup file
    """
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(auth_dir, arcname=auth_dir.name)

    return backup_path


def list_backups(backup_dir: Path) -> list[Path]:
    """List all backup files in the backup directory, sorted by modification time (newest first)."""
    if not backup_dir.exists():
        return []

    backups = list(backup_dir.glob("*.tar.gz"))
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return backups


def restore_auth(backup_file: Path, auth_dir: Path):
    """
    Restore authorization files from a tar.gz archive.

    Args:
        backup_file: Backup file path
        auth_dir: Target authorization directory
    """
    # Remove existing auth directory if it exists
    if auth_dir.exists():
        import shutil
        shutil.rmtree(auth_dir)

    # Extract backup
    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(auth_dir.parent)


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

            # Show Adobe ID email if applicable
            if auth_type == "AdobeID":
                email = loader.account.get_adobe_id_email()
                if email:
                    click.echo(f"Adobe ID: {email}")
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

    Before resetting, a backup will be automatically created.

    Examples:

        book-loader auth reset
    """
    try:
        config = Config()
        loader = BookLoader(config)

        # Auto-backup before reset
        if loader.account.is_authorized():
            default_backup_dir = Path.home() / "adobe-ade-auth-bk"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"auth_backup_{timestamp}.tar.gz"
            backup_path = default_backup_dir / backup_filename

            click.echo(f"Creating backup before reset: {backup_path}")
            backup_auth(config.auth_dir, backup_path)
            click.secho(f"✓ Backup created: {backup_path}", fg="green")

        loader.account.reset()
        click.secho("✓ Authorization reset", fg="green", bold=True)

    except Exception as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        sys.exit(1)


@auth.command("backup")
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Backup directory path (default: ~/adobe-ade-auth-bk/)",
)
def backup_auth_cmd(output):
    """Backup authorization to tar.gz archive

    Examples:

        book-loader auth backup

        book-loader auth backup -o ~/my-backups/
    """
    try:
        config = Config()
        loader = BookLoader(config)

        if not loader.account.is_authorized():
            click.secho("✗ No authorization found to backup", fg="red", err=True)
            sys.exit(1)

        # Determine backup directory
        default_backup_dir = Path.home() / "adobe-ade-auth-bk"
        if output:
            backup_dir = output
        else:
            backup_dir_input = click.prompt(
                "Backup directory",
                default=str(default_backup_dir),
                type=str,
            )
            backup_dir = Path(backup_dir_input).expanduser()

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        auth_type = loader.account.get_auth_type()
        backup_filename = f"auth_{auth_type}_{timestamp}.tar.gz"
        backup_path = backup_dir / backup_filename

        # Create backup
        click.echo(f"Backing up authorization to: {backup_path}")
        backup_auth(config.auth_dir, backup_path)

        click.secho(f"\n✓ Backup created successfully!", fg="green", bold=True)
        click.echo(f"Backup file: {backup_path}")
        click.echo(f"File size: {backup_path.stat().st_size / 1024:.1f} KB")

    except Exception as e:
        click.secho(f"✗ Backup failed: {e}", fg="red", err=True)
        sys.exit(1)


@auth.command("restore")
@click.option(
    "--file",
    "backup_file",
    type=click.Path(exists=True, path_type=Path),
    help="Backup file to restore from",
)
@click.option(
    "--backup-dir",
    type=click.Path(path_type=Path),
    help="Backup directory to search (default: ~/adobe-ade-auth-bk/)",
)
def restore_auth_cmd(backup_file, backup_dir):
    """Restore authorization from backup

    Examples:

        book-loader auth restore

        book-loader auth restore --file ~/backups/auth_backup.tar.gz

        book-loader auth restore --backup-dir ~/my-backups/
    """
    try:
        config = Config()
        loader = BookLoader(config)

        # Warn if existing authorization will be overwritten
        if loader.account.is_authorized():
            click.secho("⚠ Warning: Existing authorization will be overwritten", fg="yellow")
            if not click.confirm("Continue?"):
                click.echo("Restore cancelled")
                return

        # If --file is provided, use it directly
        if backup_file:
            selected_backup = backup_file
        else:
            # List available backups
            default_backup_dir = Path.home() / "adobe-ade-auth-bk"
            search_dir = Path(backup_dir).expanduser() if backup_dir else default_backup_dir

            backups = list_backups(search_dir)

            if not backups:
                click.secho(f"✗ No backup files found in {search_dir}", fg="red", err=True)
                click.echo("\nHint: Use '--file' to specify a backup file directly")
                sys.exit(1)

            # Display available backups
            click.echo(f"\nAvailable backups in {search_dir}:\n")
            for i, backup in enumerate(backups, 1):
                size_kb = backup.stat().st_size / 1024
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                click.echo(f"  {i}. {backup.name}")
                click.echo(f"     Size: {size_kb:.1f} KB  |  Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

            # Let user select a backup
            choice = click.prompt(
                f"\nSelect backup to restore (1-{len(backups)})",
                type=click.IntRange(1, len(backups)),
            )
            selected_backup = backups[choice - 1]

        # Restore authorization
        click.echo(f"\nRestoring authorization from: {selected_backup}")
        restore_auth(selected_backup, config.auth_dir)

        click.secho(f"\n✓ Authorization restored successfully!", fg="green", bold=True)
        click.echo(f"Authorization directory: {config.auth_dir}")

        # Display restored auth info
        click.echo("\nRestored authorization info:")
        loader = BookLoader(config)  # Reload to get new auth
        if loader.account.is_authorized():
            auth_type = loader.account.get_auth_type()
            auth_type_display = {
                "anonymous": "Anonymous",
                "AdobeID": "Adobe ID",
            }.get(auth_type, auth_type)
            click.echo(f"  Type: {auth_type_display}")

            if auth_type == "AdobeID":
                email = loader.account.get_adobe_id_email()
                if email:
                    click.echo(f"  Adobe ID: {email}")

    except Exception as e:
        click.secho(f"✗ Restore failed: {e}", fg="red", err=True)
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


@cli.group()
def kobo():
    """Kobo Desktop Edition book management"""
    pass


@kobo.command("list")
def kobo_list():
    """List all books in Kobo Desktop library

    Examples:

        book-loader kobo list
    """
    try:
        from .core.kobo import KoboLibrary

        lib = KoboLibrary()
        books = lib.books

        if not books:
            click.echo("No books found in Kobo library.")
            lib.close()
            return

        click.echo(f"\nFound {len(books)} book(s) in Kobo library:\n")
        click.echo(f"{'#':<4} {'Title':<48} {'Author':<28} DRM")
        click.echo("-" * 88)

        for i, book in enumerate(books, 1):
            title = (book.title[:45] + "...") if len(book.title) > 48 else book.title
            author = book.author or ""
            author = (author[:25] + "...") if len(author) > 28 else author
            if book.has_drm:
                drm_label = click.style("Protected", fg="yellow")
            else:
                drm_label = click.style("DRM-free", fg="green")
            click.echo(f"{i:<4} {title:<48} {author:<28} {drm_label}")

        lib.close()

    except BookLoaderError as e:
        click.secho(f"\n✗ Error: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"\n✗ Unexpected error: {e}", fg="red", err=True)
        sys.exit(1)


@kobo.command("dedrm")
@click.option("--all", "all_books", is_flag=True, help="Decrypt all books")
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output directory (default: current directory)",
)
def kobo_dedrm(all_books, output):
    """Remove DRM from Kobo books

    Without --all: show interactive menu to select books.
    With --all: decrypt all books.

    Examples:

        book-loader kobo dedrm

        book-loader kobo dedrm --all

        book-loader kobo dedrm -o ~/Books/
    """
    try:
        from .core.kobo import KoboLibrary, KoboDecryptor

        lib = KoboLibrary()
        books = lib.books

        if not books:
            click.echo("No books found in Kobo library.")
            lib.close()
            return

        if all_books:
            selected_books = books
        else:
            import questionary

            choices = [
                questionary.Choice(
                    title="{title}{author} [{drm}]".format(
                        title=book.title,
                        author=f" ({book.author})" if book.author else "",
                        drm="DRM" if book.has_drm else "Free",
                    ),
                    value=book,
                )
                for book in books
            ]

            selected_books = questionary.checkbox(
                "Select books to decrypt (Space: select/deselect, Enter: confirm):",
                choices=choices,
            ).ask()

            if not selected_books:
                click.echo("No books selected.")
                lib.close()
                return

        output_dir = output or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        decryptor = KoboDecryptor()
        userkeys = lib.userkeys

        success_count = 0
        fail_count = 0

        for book in selected_books:
            click.echo(f"\nProcessing: {book.title}")
            try:
                if not book.filename.exists():
                    click.secho(f"  ✗ Book file not found (not downloaded?): {book.filename}", fg="red")
                    fail_count += 1
                    continue

                output_path = decryptor.decrypt_book(book, userkeys, output_dir)
                click.secho(f"  ✓ Saved: {output_path}", fg="green")
                success_count += 1
            except BookLoaderError as e:
                click.secho(f"  ✗ Failed: {e}", fg="red")
                fail_count += 1

        lib.close()

        click.echo(f"\n--- Summary ---")
        click.secho(f"Success: {success_count}", fg="green" if success_count > 0 else "white")
        if fail_count > 0:
            click.secho(f"Failed:  {fail_count}", fg="red")
            sys.exit(1)

    except BookLoaderError as e:
        click.secho(f"\n✗ Error: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"\n✗ Unexpected error: {e}", fg="red", err=True)
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
