@echo off
REM Build script for Shoukat Sons Garments POS
REM This script builds the Windows executable using PyInstaller

echo ============================================================
echo Building Shoukat Sons Garments POS
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous build
echo Cleaning previous build artifacts...
rmdir /s /q build dist 2>nul
if exist ShoukatPOS.spec (
    del /q ShoukatPOS.log 2>nul
)

echo.
echo Running PyInstaller...
echo.

REM Run PyInstaller using the spec file
REM Using --onedir mode (NOT --onefile) to avoid AV false positives
pyinstaller --noconfirm ShoukatPOS.spec

if errorlevel 1 (
    echo.
    echo ============================================================
    echo BUILD FAILED!
    echo ============================================================
    echo Check the error messages above for details.
    echo Common issues:
    echo   - Missing dependencies (run: pip install -r requirements.txt)
    echo   - Missing assets/logo.ico file
    echo   - PyInstaller version incompatibility
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo BUILD SUCCESSFUL!
echo ============================================================
echo.
echo Output directory: dist\ShoukatPOS\
echo Executable: dist\ShoukatPOS\ShoukatPOS.exe
echo.
echo Next steps:
echo   1. Test the application: dist\ShoukatPOS\ShoukatPOS.exe
echo   2. If you have a code signing certificate, sign the executable:
echo      signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a "dist\ShoukatPOS\ShoukatPOS.exe"
echo   3. Create an installer using Inno Setup (optional):
echo      ISCC.exe installer.iss
echo ============================================================
echo.
pause
