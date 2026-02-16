# Book Loader Test Report

## Test Environment

- Python Version: 3.10+
- Package Management: uv
- Operating System: macOS (Darwin 24.6.0)

## Completed Tests ✓

### 1. CLI Basic Functionality Tests

#### 1.1 Help Commands
```bash
✓ uv run book-loader --help
✓ uv run book-loader info
✓ uv run book-loader auth --help
```

**Result**: All commands execute normally and display correct help text.

#### 1.2 System Information
```bash
✓ uv run book-loader info
```

**Result**: Correctly displays version, authorization directory, and authorization status.

### 2. Anonymous Authorization Tests

#### 2.1 Create Anonymous Authorization
```bash
✓ uv run book-loader auth create --anonymous
```

**Result**:
- Successfully created anonymous authorization
- Generated three authorization files:
  - `~/.config/book-loader/.adobe/activation.xml` (10731 bytes)
  - `~/.config/book-loader/.adobe/device.xml` (575 bytes)
  - `~/.config/book-loader/.adobe/devicesalt` (16 bytes)

#### 2.2 View Authorization Information
```bash
✓ uv run book-loader auth info
```

**Result**:
- Authorization status: Authorized ✓
- Authorization type: Anonymous

#### 2.3 Reset Authorization
```bash
✓ uv run book-loader auth reset --yes
```

**Result**:
- Successfully deleted all authorization files
- Authorization directory restored to empty state

### 3. Code Fixes

#### 3.1 Import Path Fixes
**Issue**: Files copied from acsm-calibre-plugin used absolute imports, causing `ModuleNotFoundError`

**Fixes**:
- `libadobe.py`: `from customRSA` → `from .customRSA`
- `libadobeAccount.py`: `from libadobe` → `from .libadobe` (6 occurrences)
- `libadobeFulfill.py`: `from libadobe` → `from .libadobe` (4 occurrences)

#### 3.2 Function Reference Fixes
**Issue**: `createDeviceKeyFile()` is in `libadobe.py`, not `libadobeAccount.py`

**Fixes**:
- In `account.py` authorization methods:
  - Changed `libadobeAccount.createDeviceKeyFile()` to `libadobe.createDeviceKeyFile()`

## Pending Tests ⏳

### 1. End-to-End Tests (Requires Actual ACSM Files)

#### 1.1 Anonymous Authorization + ACSM Processing
```bash
# Requires actual .acsm file
book-loader process sample.acsm
```

**Expected Result**:
- Automatically create anonymous authorization (if not exists)
- Download and fulfill ACSM file
- Remove DRM
- Output DRM-free EPUB or PDF

#### 1.2 Adobe ID Authorization Test
```bash
# Requires valid Adobe ID account
book-loader auth reset --yes
book-loader auth create --adobe-id --email your@email.com
book-loader process sample.acsm
```

**Expected Result**:
- Successfully create Adobe ID authorization
- Able to process ACSM files

#### 1.3 Error Handling Tests
- [ ] Invalid ACSM file
- [ ] Network connection failure
- [ ] Already-fulfilled ACSM file
- [ ] Corrupted authorization files

### 2. Optional Feature Tests (Requires Calibre)

#### 2.1 EPUB Optimization
```bash
brew install calibre  # If not already installed
book-loader process sample.acsm --optimize
```

#### 2.2 PDF Conversion
```bash
book-loader process sample.acsm --to-pdf
```

#### 2.3 Keep Encrypted File
```bash
book-loader process sample.acsm --keep-encrypted
```

## Testing Guide

### Prepare Actual ACSM Files

1. Go to Kobo website library
2. Select a purchased ebook
3. Download `.acsm` file

### Run Complete Tests

```bash
# 1. Create authorization (if not already created)
uv run book-loader auth create --anonymous

# 2. Process ACSM file
uv run book-loader process /path/to/your/book.acsm -o ~/Books/

# 3. Verify output
# - Check if DRM-free ebook exists in ~/Books/ directory
# - Open file with ebook reader to confirm readability

# 4. Test reset and re-authorization
uv run book-loader auth reset --yes
uv run book-loader auth create --anonymous
uv run book-loader process /path/to/another/book.acsm
```

### Test Adobe ID Authorization

```bash
# 1. Reset existing authorization
uv run book-loader auth reset --yes

# 2. Use Adobe ID authorization
uv run book-loader auth create --adobe-id --email your@email.com
# Enter password

# 3. View authorization information
uv run book-loader auth info
# Should display "Authorization type: Adobe ID"

# 4. Process ACSM
uv run book-loader process /path/to/book.acsm
```

## Known Issues

None

## Next Steps

1. Obtain actual ACSM files for end-to-end testing
2. Implement Calibre integration (optional feature)
3. Write unit tests
4. Improve error handling
5. Update README documentation

## Change History

- 2026-02-16: Initial test report
  - Completed CLI basic functionality tests
  - Completed anonymous authorization tests
  - Fixed import path issues
  - Fixed function reference issues
