#!/usr/bin/env python3
"""
EPUBCheck installer 
"""

import os
import sys
import json
import tempfile
import zipfile
import urllib.request
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

def get_latest_release() -> Optional[Dict[str, str]]:
    """Fetch latest release info from GitHub API"""
    try:
        api_url = "https://api.github.com/repos/w3c/epubcheck/releases/latest"
        
        # Support for GitHub token
        headers = {}
        github_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        tag_name = data.get('tag_name', '')
        if not tag_name:
            return None
        
        version_clean = tag_name.lstrip('v')
        download_url = f"https://github.com/w3c/epubcheck/releases/download/{tag_name}/epubcheck-{version_clean}.zip"
        
        return {
            'version': tag_name,
            'download_url': download_url
        }
    except Exception as e:
        print(f"️ GitHub API error: {e}")
        return None

def download_and_extract(download_url: str, install_dir: Path) -> bool:
    """Download ZIP and extract - security improvements"""
    temp_file = None
    try:
        #  Fix: mktemp() -> NamedTemporaryFile (security)
        # Use delete=False to control manual cleanup
        temp_file = tempfile.NamedTemporaryFile(
            suffix="-epubcheck.zip",
            delete=False
        )
        temp_zip = temp_file.name
        temp_file.close()  # Close file handle before download
        
        print(f" Downloading: {download_url}")
        urllib.request.urlretrieve(download_url, temp_zip)
        print(f" Download complete: {Path(temp_zip).stat().st_size / 1024 / 1024:.1f}MB")
        
        # Remove existing installation directory
        if install_dir.exists():
            print(f"️ Removing existing installation: {install_dir}")
            shutil.rmtree(install_dir)
        install_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract ZIP archive
        print(f" Extracting archive...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(install_dir)
        
        # Clean up temporary file
        Path(temp_zip).unlink()
        print(f" Extraction complete")
        return True
        
    except Exception as e:
        print(f" Download failed: {e}")
        # Clean up temporary file even on error
        if temp_file and Path(temp_file.name).exists():
            try:
                Path(temp_file.name).unlink()
            except:
                pass
        return False

def create_execution_script(install_dir: Path) -> bool:
    """Create execution scripts"""
    try:
        # Find epubcheck-x.x.x directory
        epubcheck_version_dir = None
        for item in install_dir.iterdir():
            if item.is_dir() and item.name.startswith("epubcheck-"):
                epubcheck_version_dir = item
                break
        
        if not epubcheck_version_dir:
            print(f" Could not find EPUBCheck directory")
            print(f" Search location: {install_dir}")
            print(f" Directory contents: {list(install_dir.iterdir())}")
            return False
        
        print(f" EPUBCheck directory: {epubcheck_version_dir.name}")
        
        # Unix/Mac script
        script_path = install_dir / "epubcheck.sh"
        with open(script_path, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f'EPUBCHECK_DIR="{epubcheck_version_dir}"\n')
            f.write('java -cp "$EPUBCHECK_DIR/*:$EPUBCHECK_DIR/lib/*" com.adobe.epubcheck.tool.Checker "$@"\n')
        
        script_path.chmod(0o755)
        print(f" Execution script created: {script_path}")
        
        # Windows batch script (optional)
        bat_path = install_dir / "epubcheck.bat"
        with open(bat_path, 'w') as f:
            f.write('@echo off\n')
            f.write(f'set EPUBCHECK_DIR={epubcheck_version_dir}\n')
            f.write('java -cp "%EPUBCHECK_DIR%\\*;%EPUBCHECK_DIR%\\lib\\*" com.adobe.epubcheck.tool.Checker %*\n')
        
        return True
        
    except Exception as e:
        print(f" Script creation failed: {e}")
        import traceback
        print(f" Detailed error:\n{traceback.format_exc()}")
        return False

# =============================================================================
# Backwards-compatible helper functions
# =============================================================================

def install_latest_epubcheck(force: bool = False) -> bool:
    """Install the latest EPUBCheck - path bug fixes"""
    
    #  Fix: .eepub_toolkit -> .epub_toolkit
    install_dir = Path.home() / ".epub_toolkit/epubcheck"
    
    try:
        print(" Checking for latest EPUBCheck release...")
        
        # Fetch latest release info
        release_info = get_latest_release()
        if not release_info:
            print(" Could not retrieve latest release information")
            print(" Manual install: https://github.com/w3c/epubcheck/releases")
            print(" Or set a GitHub token: export GITHUB_TOKEN=your_token")
            return False
        
        version = release_info['version']
        download_url = release_info['download_url']
        
        print(f" Latest version: {version}")
        
        # Skip if already installed (unless force)
        script_path = install_dir / "epubcheck.sh"
        if not force and script_path.exists():
            # Version check
            try:
                result = subprocess.run([str(script_path), '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and version.lstrip('v') in result.stdout:
                    print(" Latest version is already installed")
                    print(f" Installation location: {install_dir}")
                    return True
            except Exception as e:
                print(f"️ Version check failed: {e}")
        
        # Download and install
        print(f" Downloading EPUBCheck {version}...")
        if not download_and_extract(download_url, install_dir):
            return False
        
        # Create execution scripts
        if not create_execution_script(install_dir):
            return False
        
        # Verify installation
        if not script_path.exists():
            print(" Installation verification failed: script missing")
            return False
        
        # Version test
        try:
            result = subprocess.run([str(script_path), '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f" Installation verification complete:")
                print(f"   {result.stdout.strip()}")
            else:
                print(f"️ Version check failed (code: {result.returncode})")
        except Exception as e:
            print(f"️ Version check test failed: {e}")
        
        print(f" EPUBCheck {version} installed successfully!")
        print(f" Installation location: {install_dir}")
        print(f" Execution script: {script_path}")
        
        return True
        
    except Exception as e:
        print(f" Error during installation: {e}")
        import traceback
        print(f" Detailed error:\n{traceback.format_exc()}")
        return False

def update_epubcheck() -> bool:
    """Force update EPUBCheck - backwards compatible"""
    return install_latest_epubcheck(force=True)

def get_epubcheck_jar_path(auto_install: bool = True, auto_update: bool = False) -> str:
    """Return EPUBCheck script path - backwards compatible"""
    
    script_path = Path.home() / ".epub_toolkit/epubcheck/epubcheck.sh"
    
    # Auto-update
    if auto_update:
        print(" Checking for EPUBCheck updates...")
        install_latest_epubcheck(force=True)
    
    # Auto-install
    elif auto_install and not script_path.exists():
        print(" EPUBCheck is not installed. Starting automatic installation...")
        if not install_latest_epubcheck():
            raise RuntimeError("EPUBCheck installation failed")
    
    # Verify path
    if not script_path.exists():
        raise FileNotFoundError(
            f"EPUBCheck is not installed.\n"
            f"Expected path: {script_path}\n"
            f"Install command: python -m epub_toolkit.utils.epubcheck_installer --install"
        )
    
    return str(script_path)

def run_epubcheck(epub_file: str, options: list = None) -> Dict[str, Any]:
    """Run EPUBCheck - backwards compatible"""
    
    try:
        options = options or []
        script_path = get_epubcheck_jar_path()
        
        cmd = [script_path] + options + [epub_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        return {
            "success": result.returncode in [0, 1],  # 0: success, 1: warnings
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "EPUBCheck execution timed out (60s)",
            "returncode": -2
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -3
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"EPUBCheck execution error: {str(e)}",
            "returncode": -4
        }

def check_epubcheck_updates() -> Tuple[bool, Optional[str], Optional[str]]:
    """Check for updates - backwards compatible"""
    
    try:
        release_info = get_latest_release()
        if not release_info:
            return False, None, "Could not retrieve latest release information"
        
        latest_version = release_info['version']
        
        # Check currently installed version
        script_path = Path.home() / ".epub_toolkit/epubcheck/epubcheck.sh"
        if not script_path.exists():
            return True, latest_version, "EPUBCheck is not installed"
        
        try:
            result = subprocess.run([str(script_path), '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                if latest_version.lstrip('v') in result.stdout:
                    return False, latest_version, "Latest version is installed"
                else:
                    return True, latest_version, f"Update available: {latest_version}"
        except Exception as e:
            print(f"️ Version check error: {e}")
        
        return True, latest_version, "Unable to determine installation status"
        
    except Exception as e:
        return False, None, f"Update check failed: {str(e)}"

def get_epubcheck_status() -> Dict[str, Any]:
    """Get installation status - backwards compatible"""
    
    script_path = Path.home() / ".epub_toolkit/epubcheck/epubcheck.sh"
    install_dir = script_path.parent
    
    # Installed?
    installed = script_path.exists()
    
    # Version info
    version = None
    if installed:
        try:
            result = subprocess.run([str(script_path), '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Extract version from "EPUBCheck vX.Y.Z" format
                import re
                match = re.search(r'EPUBCheck v(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    version = f"v{match.group(1)}"
        except Exception as e:
            print(f"️ Version check error: {e}")
    
    return {
        "installed": installed,
        "version": version,
        "install_dir": str(install_dir),
        "script_path": str(script_path)
    }

def main():
    """CLI interface - backwards compatible"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EPUBCheck installer')
    parser.add_argument('--install', action='store_true', help='Install/update')
    parser.add_argument('--update', action='store_true', help='Force update')
    parser.add_argument('--check', action='store_true', help='Check for updates')
    parser.add_argument('--status', action='store_true', help='Installation status')
    parser.add_argument('--run', metavar='EPUB_FILE', help='Validate an EPUB file')
    parser.add_argument('--force', action='store_true', help='Force reinstall')
    
    args = parser.parse_args()
    
    try:
        if args.install or args.update:
            success = install_latest_epubcheck(force=args.update or args.force)
            return 0 if success else 1
        
        elif args.check:
            has_update, version, message = check_epubcheck_updates()
            print(f" {message}")
            if has_update and version:
                print(f" Latest version: {version}")
                print(f" Update: python -m epub_toolkit.utils.epubcheck_installer --update")
            return 0
        
        elif args.status:
            status = get_epubcheck_status()
            print(" EPUBCheck installation status:")
            print(f"   Installed: {'' if status['installed'] else ''}")
            print(f"   Version: {status['version'] or 'none'}")
            print(f"   Path: {status['install_dir']}")
            print(f"   Script: {status['script_path']}")
            
            # Check Java
            try:
                java_result = subprocess.run(['java', '-version'], 
                                           capture_output=True, text=True, timeout=5)
                if java_result.returncode == 0:
                    java_version = java_result.stderr.split('\n')[0] if java_result.stderr else "unknown"
                    print(f"   Java:  {java_version}")
                else:
                    print(f"   Java:  not installed")
            except:
                print(f"   Java:  not installed")
            
            return 0
        
        elif args.run:
            result = run_epubcheck(args.run)
            if result['stdout']:
                print(result['stdout'])
            if result['stderr']:
                print(result['stderr'], file=sys.stderr)
            return result['returncode']
        
        else:
            # Default: install
            success = install_latest_epubcheck()
            return 0 if success else 1
            
    except KeyboardInterrupt:
        print("\n️ User interrupted")
        return 130
    except Exception as e:
        print(f" Error: {str(e)}")
        import traceback
        print(f" Detailed error:\n{traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main())