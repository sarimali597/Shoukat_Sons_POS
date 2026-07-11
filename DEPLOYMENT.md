# Shoukat Sons Garments POS - Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Building the Application](#building-the-application)
3. [Code Signing (Recommended)](#code-signing-recommended)
4. [Creating an Installer](#creating-an-installer)
5. [Deployment Checklist](#deployment-checklist)
6. [Installation on Shop PC](#installation-on-shop-pc)
7. [First-Run Setup](#first-run-setup)
8. [Configuration](#configuration)
9. [Backup Strategy](#backup-strategy)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Development Machine (for building)

- **Python 3.10+** installed and added to PATH
- **pip** package manager
- **PyInstaller** (`pip install pyinstaller`)
- **Inno Setup** (optional, for creating installer)
- **Code signing certificate** (optional, recommended)

### Shop PC (deployment target)

- **Windows 10/11** (64-bit)
- **4 GB RAM** minimum (8 GB recommended)
- **500 MB free disk space**
- **USB ports** for barcode scanner and printers
- **Network access** (optional, for updates)

### Hardware Requirements

| Device | Model | Connection |
|--------|-------|------------|
| Label Printer | BlackCopper BC-LP-1300 | USB |
| Receipt Printer | Generic 80mm thermal | USB/Ethernet |
| Barcode Scanner | Any USB HID scanner | USB |

---

## Building the Application

### Step 1: Install Dependencies

```bash
cd /workspace
pip install -r shoukat_pos/requirements.txt
pip install pyinstaller
```

### Step 2: Verify Tests Pass

```bash
cd shoukat_pos
pytest tests/ --cov=shoukat_pos --cov-report=term-missing
```

**Expected:** All tests pass, coverage >= 80%

### Step 3: Build with PyInstaller

#### Option A: Using the spec file (recommended)

```bash
pyinstaller ShoukatPOS.spec
```

#### Option B: Using build.bat (Windows only)

```batch
build.bat
```

#### Option C: Manual command

```bash
pyinstaller --noconfirm --windowed --onedir --icon=shoukat_pos/assets/logo.ico main.py
```

**CRITICAL:** Always use `--onedir`, NOT `--onefile`. The `--onefile` mode is disproportionately likely to be flagged as a trojan by Windows Defender and other AV engines.

### Step 4: Verify Build Output

After successful build:

```
dist/ShoukatPOS/
├── ShoukatPOS.exe          # Main executable
├── _internal/              # Dependencies and resources
│   ├── customtkinter/
│   ├── tksheet/
│   ├── PIL/
│   └── ...
└── assets/                 # Copied assets
    ├── logo.png
    └── barcode_templates/
```

**Test the executable:**

```bash
cd dist/ShoukatPOS
./ShoukatPOS.exe
```

Verify:
- [ ] Application launches without errors
- [ ] Login screen appears
- [ ] No console window opens (windowed mode)
- [ ] No antivirus warnings (if code-signed)

---

## Code Signing (Recommended)

### Why Code Sign?

- Reduces AV false positives
- Required for Windows SmartScreen
- Looks professional to users
- Allows automatic whitelisting by AV vendors

### Steps to Code Sign

1. **Purchase a code-signing certificate** from a recognized CA:
   - DigiCert
   - Sectigo
   - Certum
   - GlobalSign

2. **Install the certificate** in Windows certificate store

3. **Sign the executable** after PyInstaller build:

```batch
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a "dist\ShoukatPOS\ShoukatPOS.exe"
```

4. **Verify the signature:**

```batch
signtool verify /pa "dist\ShoukatPOS\ShoukatPOS.exe"
```

### If False Positives Persist

Try **Nuitka** as an alternative packager:

```bash
pip install nuitka
python -m nuitka --standalone --windows-disable-console --windows-icon-from-ico=assets/logo.ico --enable-plugin=tk-inter main.py
```

Nuitka compiles Python to C and then to native binary, producing executables that read very differently to AV heuristics.

---

## Creating an Installer

### Using Inno Setup

1. **Download and install Inno Setup** from https://jrsoftware.org/isdl.php

2. **Compile the installer script:**

```batch
ISCC.exe installer.iss
```

3. **Output:** `ShoukatPOS_Setup.exe`

### Installer Features

- Installs to `C:\Program Files\ShoukatPOS`
- Creates desktop shortcut (optional)
- Creates Start Menu entry
- Includes uninstaller
- Auto-launches application after installation

---

## Deployment Checklist

### Pre-Deployment Verification

- [ ] All tests pass (`pytest tests/`)
- [ ] Coverage >= 80% (`pytest --cov`)
- [ ] No lint errors (`ruff check .`)
- [ ] No type errors (`mypy shoukat_pos/`)
- [ ] Build succeeds (`pyinstaller ShoukatPOS.spec`)
- [ ] Application launches without errors
- [ ] First-run wizard completes successfully
- [ ] Admin login works (default: admin/admin123)
- [ ] Test print on label printer succeeds
- [ ] Test print on receipt printer succeeds
- [ ] Barcode scanner inputs correctly
- [ ] Backup and restore work
- [ ] Code-signed (if certificate obtained)

### Post-Deployment Tasks

- [ ] Create desktop shortcut
- [ ] Pin to taskbar (optional)
- [ ] Set Windows to auto-start Shoukat POS on boot (optional)
- [ ] Configure daily auto-backup
- [ ] Train cashier on basic operations:
  - [ ] New sale with barcode scan
  - [ ] Cash and credit transactions
  - [ ] Held sales
  - [ ] Returns and exchanges
- [ ] Train owner on admin operations:
  - [ ] View reports
  - [ ] Manage settings
  - [ ] Backup/restore database
  - [ ] Manage users
- [ ] Print a test label and verify barcode scans correctly
- [ ] Run first-day reconciliation: opening cash + sales - returns = closing

---

## Installation on Shop PC

### Method 1: Using Installer (Recommended)

1. Copy `ShoukatPOS_Setup.exe` to shop PC
2. Double-click to run installer
3. Follow installation wizard
4. Launch application from desktop shortcut

### Method 2: Portable Installation

1. Copy entire `dist/ShoukatPOS/` folder to shop PC
2. Place in desired location (e.g., `C:\Program Files\ShoukatPOS\`)
3. Create shortcut to `ShoukatPOS.exe`
4. Right-click shortcut → Send to → Desktop (create shortcut)

---

## First-Run Setup

On first launch, the application will guide you through:

1. **Shop Information:**
   - Shop name
   - Address
   - Phone number
   - NTN/Sales tax number (optional)

2. **Admin Account:**
   - Username (default: admin)
   - Password (change from default!)
   - Security questions

3. **Printer Configuration:**
   - Label printer selection
   - Receipt printer selection
   - Test prints

4. **Initial Data:**
   - Default categories are pre-loaded
   - Add your first products

---

## Configuration

### Essential Settings

Access via **Settings** menu:

| Setting | Recommended Value | Notes |
|---------|------------------|-------|
| Currency | Rs. (PKR) | Pre-configured |
| Invoice Prefix | INV | Pre-configured |
| Default Tax Rate | 0% | Adjust if needed |
| Session Timeout | 30 minutes | Security setting |
| Backup Frequency | Daily | Critical! |

### Printer Setup

**Label Printer (BlackCopper BC-LP-1300):**

1. Install printer driver from manufacturer
2. In POS: Settings → Printers → Label Printer
3. Select "BlackCopper BC-LP-1300"
4. Click "Test Print"
5. Verify barcode scans correctly

**Receipt Printer (80mm thermal):**

1. Install printer driver
2. In POS: Settings → Printers → Receipt Printer
3. Select printer from dropdown
4. Click "Test Print"

**Barcode Scanner:**

- Most USB scanners work as HID devices (plug-and-play)
- No driver needed
- Test by scanning a product barcode in New Sale screen

---

## Backup Strategy

### Automated Backups

The POS includes automatic backup functionality:

1. **Daily backups** at configurable time
2. **Pre-transaction backups** before large operations
3. **Manual backup** option in Settings

### Backup Location

Default: `C:\Users\[User]\Documents\ShoukatPOS\backups\`

### Restore Procedure

1. Open POS application
2. Go to Settings → Backup & Restore
3. Click "Restore Backup"
4. Select backup file (.db or encrypted archive)
5. Confirm restoration

### Best Practices

- [ ] Enable daily automatic backups
- [ ] Store backups on external drive weekly
- [ ] Test restore procedure monthly
- [ ] Keep at least 30 days of backups

---

## Troubleshooting

### Application Won't Start

**Symptoms:** Nothing happens when clicking shortcut

**Solutions:**
1. Check if Windows Defender blocked it (quarantine)
2. Try running as Administrator
3. Check event viewer for errors
4. Reinstall with code signing certificate

### Printer Not Working

**Symptoms:** Test print fails or nothing prints

**Solutions:**
1. Verify printer is connected and powered on
2. Check printer is set as default in Windows
3. Reinstall printer drivers
4. In POS: Settings → Printers → Reconfigure

### Database Errors

**Symptoms:** "Database locked" or "Cannot connect"

**Solutions:**
1. Close all instances of the application
2. Check no other process is using the database
3. Restart the computer
4. Restore from backup if corruption suspected

### Barcode Scanner Issues

**Symptoms:** Scanner types characters instead of barcode

**Solutions:**
1. Ensure scanner is in HID mode (not COM emulation)
2. Check scanner configuration barcodes
3. Test in Notepad to verify output format
4. Replace scanner batteries if wireless

### Update Failures

**Symptoms:** "Update file corrupted" error

**Solutions:**
1. Check internet connection
2. Verify SHA-256 hash manually
3. Download update manually from website
4. Contact support if problem persists

---

## Support

For technical support:

- **Email:** support@shoukatsons.com
- **Phone:** [Your contact number]
- **Documentation:** See README.md in project root

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-15 | Initial release |

---

## License

Proprietary software - Shoukat Sons Garments

---

*Last updated: July 2026*
