# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Management

Use `uv` for all Python package and environment management:

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add package-name

# Run the CLI
book-loader <command>

# Install in editable mode for development
uv pip install -e .
```

## Development Commands

```bash
# Format code
uv run black src/
uv run ruff check src/ --fix

# Run the CLI directly (for testing)
uv run python -m book_loader.cli <command>
```

## Architecture Overview

`book_loader` is a dual-purpose DRM removal tool for Adobe ACSM and Kobo KEPUB ebooks.

### Core Workflow (Adobe ACSM)

**Processing pipeline:** ACSM → Fulfillment → DRM Removal → (Optional) PDF Conversion

1. **Authorization** (`core/adobe/account.py`): Manages Adobe authorization via anonymous or Adobe ID
   - Supports two formats: Standard (`activation.xml` + `device.xml` + `devicesalt`) and ADE 4.5+ (`activation.dat`)
   - Authorization files stored in `~/.config/book-loader/.adobe/`

2. **Fulfillment** (`core/adobe/fulfill.py`): Downloads encrypted ebook from Adobe server using ACSM file
   - Uses `libadobeFulfill.py` for Adobe Content Server protocol
   - Transaction-based: each ACSM can only be fulfilled once per authorization

3. **DRM Removal** (`core/drm/remover.py`): Decrypts ebook using authorization's RSA private key
   - EPUB: `ineptepub.py` (AES-CBC decryption)
   - PDF: `ineptpdf.py` (RSA + AES decryption)

4. **Conversion** (`core/conversion/`): Optional EPUB → PDF conversion
   - Two engines: `python` (weasyprint) or `calibre` (external)

### Kobo DRM Removal (macOS only)

**Processing pipeline:** Kobo Desktop SQLite → MAC Address + UserID → Key Derivation → AES-ECB Decryption

1. **Library** (`core/kobo/library.py`): Reads Kobo Desktop's `Kobo.sqlite` database
   - **CRITICAL**: Uses separate cursors for nested queries to avoid result set overwrites (commit `a1d2b53` fix)
   - Derives decryption keys: `SHA256(hash_key + MAC) → SHA256(deviceid + userid)[32:]`
   - Supports `--source` option for custom library paths

2. **Decryptor** (`core/kobo/decryptor.py`): Two-layer AES-ECB decryption
   - Layer 1: `userkey` decrypts `encrypted_page_key` (from DB)
   - Layer 2: `page_key` decrypts XHTML/image content
   - Validates decryption with content checks (XML/JPEG magic bytes)

### CLI Structure

`cli.py` uses Click with command groups:
- `process` - ACSM workflow
- `auth` - Authorization management (create/info/reset/backup/restore)
- `kobo` - Kobo commands (list/dedrm) with `--source` option
- `convert` - Standalone EPUB → PDF
- `info` - System information

### Key Modules

- **`utils/config.py`**: Configuration management (auth directory paths)
- **`utils/errors.py`**: Custom exception hierarchy (`BookLoaderError` base)
- **`core/workflow.py`**: `BookLoader` orchestrates the Adobe ACSM processing pipeline

## Important Implementation Details

### Kobo SQLite Cursor Bug (Fixed in a1d2b53)

**Problem:** Reusing the same cursor for nested queries causes the outer loop to terminate after the first iteration.

**Solution:** Use `.fetchall()` for outer query and create separate cursor for inner queries:

```python
# ✅ Correct
drm_rows = self._cursor.execute("SELECT ...").fetchall()
inner_cursor = self._conn.cursor()
for row in drm_rows:
    for ef_row in inner_cursor.execute("SELECT ... WHERE volumeid=?", ...):
        # Process
```

### Adobe Authorization Formats

Two supported formats (checked in order):
1. **ADE 4.5+**: Single `activation.dat` file (binary)
2. **Standard**: `activation.xml` + `device.xml` + `devicesalt` (XML/binary)

Always check both formats in `is_authorized()`.

### Kobo Key Derivation

MAC addresses obtained via `/sbin/ifconfig -a` (macOS-specific). Hash keys are fixed constants from Kobo's client:

```python
KOBO_HASH_KEYS = ["88b3a2e13", "XzUhGYdFp", "NoCanLook", "QJhwzAtXL"]
deviceid = SHA256(hash_key + MAC)
userkey = SHA256(deviceid + UserID)[32:]  # Last 16 bytes
```

Try all combinations (4 hashes × N MACs × M UserIDs) until decryption succeeds.

## CLI Command Reference

### Adobe ACSM
```bash
book-loader process book.acsm [-o OUTPUT_DIR] [--to-pdf] [--auth-dir AUTH_DIR]
book-loader auth create [--anonymous | --adobe-id --email EMAIL]
book-loader auth info
book-loader auth backup [-o BACKUP_DIR]
book-loader auth restore [--file BACKUP_FILE]
```

### Kobo Desktop
```bash
book-loader kobo [--source KOBO_DIR] list
book-loader kobo [--source KOBO_DIR] dedrm [--all] [-o OUTPUT_DIR]
```

Default Kobo path: `~/Library/Application Support/Kobo/Kobo Desktop Edition`
