#!/usr/bin/env python3
"""Manual EPUBCheck installer - bypass GitHub API"""

import urllib.request
import zipfile
import shutil
from pathlib import Path

# Latest EPUBCheck direct download URL
EPUBCHECK_URL = "https://github.com/w3c/epubcheck/releases/download/v5.1.0/epubcheck-5.1.0.zip"
INSTALL_DIR = Path.home() / ".epub_toolkit" / "epubcheck"

print("Downloading EPUBCheck...")
print(f"URL: {EPUBCHECK_URL}")

# Create directory
INSTALL_DIR.mkdir(parents=True, exist_ok=True)

# Download
zip_path = INSTALL_DIR / "epubcheck.zip"
urllib.request.urlretrieve(EPUBCHECK_URL, zip_path)
print(f"Downloaded to: {zip_path}")

# Extract
print("Extracting...")
with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(INSTALL_DIR)

# Find jar
jars = list(INSTALL_DIR.rglob("epubcheck.jar"))
if jars:
    print(f"\nSuccess! EPUBCheck installed at:")
    print(f"  {jars[0]}")
else:
    print("\nERROR: epubcheck.jar not found after extraction")

# Cleanup
zip_path.unlink()
print("\nDone!")
