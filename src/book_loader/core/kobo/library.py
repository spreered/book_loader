"""
Kobo Desktop Edition library manager.
"""

import os
import re
import base64
import hashlib
import binascii
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ...utils.errors import KoboLibraryNotFoundError

KOBO_HASH_KEYS = ["88b3a2e13", "XzUhGYdFp", "NoCanLook", "QJhwzAtXL"]


@dataclass
class KoboBook:
    """Represents a book in the Kobo Desktop library."""

    volumeid: str
    title: str
    filename: Path
    has_drm: bool
    author: str | None = None
    encrypted_files: dict = field(default_factory=dict)  # {elementid: encrypted_page_key_bytes}


class KoboLibrary:
    """Manages access to the Kobo Desktop Edition library.

    Reads book metadata and encryption keys from the Kobo SQLite database.
    """

    DEFAULT_KOBODIR = Path.home() / "Library" / "Application Support" / "Kobo" / "Kobo Desktop Edition"

    def __init__(self, kobodir: Path | None = None):
        if kobodir is not None:
            kobodir = Path(kobodir).expanduser()
        else:
            kobodir = self.DEFAULT_KOBODIR

        if not kobodir.exists():
            raise KoboLibraryNotFoundError(
                f"Kobo Desktop Edition directory not found: {kobodir}\n"
                "Please make sure Kobo Desktop is installed and has been run at least once."
            )

        kobodb = kobodir / "Kobo.sqlite"
        if not kobodb.exists():
            raise KoboLibraryNotFoundError(
                f"Kobo database not found: {kobodb}\n"
                "Please make sure Kobo Desktop has synced your library."
            )

        self.kobodir = kobodir

        # Copy DB to a temp file with WAL mode disabled (bytes 18-19 → 0x01 0x01)
        self._tmpdb = tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".sqlite")
        with open(kobodb, "rb") as f:
            self._tmpdb.write(f.read(18))
            self._tmpdb.write(b"\x01\x01")
            f.read(2)
            self._tmpdb.write(f.read())
        self._tmpdb.close()

        self._conn = sqlite3.connect(self._tmpdb.name)
        self._conn.text_factory = lambda b: b.decode("utf-8", errors="ignore")
        self._cursor = self._conn.cursor()

        self._books: list[KoboBook] | None = None
        self._userkeys: list[bytes] | None = None

    def close(self):
        """Close database connection and clean up temp files."""
        self._cursor.close()
        self._conn.close()
        try:
            os.unlink(self._tmpdb.name)
        except OSError:
            pass

    @property
    def books(self) -> list[KoboBook]:
        """All books in the Kobo library (both DRM-protected and DRM-free)."""
        if self._books is not None:
            return self._books

        self._books = []
        volume_ids: set[str] = set()

        # Fetch all DRM-protected books first (avoid cursor reuse issues)
        drm_rows = self._cursor.execute(
            "SELECT DISTINCT volumeid, Title, Attribution "
            "FROM content_keys, content WHERE contentid = volumeid"
        ).fetchall()

        # Use a separate cursor for inner queries
        inner_cursor = self._conn.cursor()

        for row in drm_rows:
            volumeid, title, author = row
            filename = self.kobodir / "kepub" / volumeid

            # Get encrypted file keys for this book
            encrypted_files: dict[str, bytes] = {}
            for ef_row in inner_cursor.execute(
                "SELECT elementid, elementkey FROM content_keys "
                "WHERE volumeid = ?",
                (volumeid,),
            ):
                elementid, elementkey = ef_row
                encrypted_files[elementid] = base64.b64decode(elementkey)

            self._books.append(
                KoboBook(
                    volumeid=volumeid,
                    title=title or volumeid,
                    filename=filename,
                    has_drm=True,
                    author=author,
                    encrypted_files=encrypted_files,
                )
            )
            volume_ids.add(volumeid)

        # DRM-free books: scan kepub/ directory for files not in content_keys
        bookdir = self.kobodir / "kepub"
        if bookdir.exists():
            for f in bookdir.iterdir():
                if f.name not in volume_ids:
                    row = self._cursor.execute(
                        "SELECT Title, Attribution FROM content WHERE ContentID = ?",
                        (f.name,),
                    ).fetchone()
                    if row:
                        title, author = row
                        self._books.append(
                            KoboBook(
                                volumeid=f.name,
                                title=title or f.name,
                                filename=f,
                                has_drm=False,
                                author=author,
                            )
                        )
                        volume_ids.add(f.name)

        self._books.sort(key=lambda x: x.title.lower())
        return self._books

    @property
    def userkeys(self) -> list[bytes]:
        """All candidate user keys derived from MAC addresses and user IDs."""
        if self._userkeys is not None:
            return self._userkeys

        self._userkeys = []
        for macaddr in self._get_mac_addrs():
            self._userkeys.extend(self._compute_userkeys(macaddr))
        return self._userkeys

    def _get_mac_addrs(self) -> list[str]:
        """Get all MAC addresses on this machine using ifconfig."""
        macaddrs = []
        pattern = re.compile(
            r"\s(" + "[0-9a-f]{2}:" * 5 + r"[0-9a-f]{2})(\s|$)", re.IGNORECASE
        )
        try:
            output = subprocess.check_output("/sbin/ifconfig -a", shell=True, encoding="utf-8")
            for m in pattern.findall(output):
                macaddrs.append(m[0].upper())
        except subprocess.CalledProcessError:
            pass
        return macaddrs

    def _get_user_ids(self) -> list[str]:
        """Get all user IDs from the Kobo database."""
        userids = []
        cursor = self._cursor.execute("SELECT UserID FROM user")
        row = cursor.fetchone()
        while row is not None:
            try:
                userids.append(row[0])
            except Exception:
                pass
            row = cursor.fetchone()
        return userids

    def _compute_userkeys(self, macaddr: str) -> list[bytes]:
        """Compute all candidate user keys for a given MAC address."""
        userids = self._get_user_ids()
        userkeys = []
        for hash_key in KOBO_HASH_KEYS:
            deviceid = hashlib.sha256((hash_key + macaddr).encode("ascii")).hexdigest()
            for userid in userids:
                userkey_hex = hashlib.sha256((deviceid + userid).encode("ascii")).hexdigest()
                # Take bytes 16-31 (hex chars 32-63) of the SHA256 digest
                userkeys.append(binascii.a2b_hex(userkey_hex[32:]))
        return userkeys
