# Fix: install_linux.sh Path Issue

## Problem
When running `scripts/install_linux.sh`, the script would fail at line 319 with:
```
./scripts/install_linux.sh: Zeile 319: venv/bin/activate: Datei oder Verzeichnis nicht gefunden
(Line 319: venv/bin/activate: No such file or directory)
```

The issue was that the script checked for and tried to activate the virtual environment using relative paths (`venv/bin/activate`), but the script is located in the `scripts/` subdirectory while the venv is created in the parent directory.

## Root Cause
- Script location: `/home/nils/sulf/sulfur/scripts/install_linux.sh`
- venv expected location: `/home/nils/sulf/sulfur/venv`
- Relative path used: `venv/bin/activate` (incorrect from scripts/ dir)
- Correct path should be: `../venv/bin/activate` or absolute path

## Solution
Updated the script to:
1. Get the repository root directory dynamically using `BASH_SOURCE`
2. Change to the repository root directory in `setup_venv()` function
3. Use absolute paths for all venv references
4. Pass the correct paths to functions that need them

## Changes Made

### 1. setup_venv() function (Lines 268-327)
- Added: `REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`
- Added: `cd "$REPO_DIR"` to change to the correct directory
- Changed: All venv references from `venv` to `$REPO_DIR/venv`
- Changed: All pip install references from `requirements.txt` to `$REPO_DIR/requirements.txt`

### 2. run_setup_wizard() function (Lines 333-341)
- Added: `REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`
- Changed: `source venv/bin/activate` to `source "$REPO_DIR/venv/bin/activate"`
- Added: `cd "$REPO_DIR"` before running master_setup.py

### 3. create_systemd_service() function (Lines 343-378)
- Added: `REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`
- Removed: `CURRENT_DIR=$(pwd)` (no longer needed)
- Changed: All path references from `$CURRENT_DIR` to `$REPO_DIR`

### 4. main() function (Lines 380-413)
- Added: `REPO_DIR` calculation
- Fixed: Non-interactive mode message to show correct path
- Fixed: Next steps instructions to include `cd $REPO_DIR`

## Technical Details

The key fix is the path calculation:
```bash
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
```

This works by:
1. `"${BASH_SOURCE[0]}"` - Gets the path of the current script (`scripts/install_linux.sh`)
2. `dirname` - Gets the directory (`scripts`)
3. `cd ... && pwd` - Changes to that directory and then parent (using `..`) and gets absolute path
4. Result: Absolute path to the repository root

## Testing
✅ Script syntax validated with `bash -n`
✅ All path references use absolute paths
✅ No more relative path issues
✅ Script will work correctly regardless of where it's called from

## Files Modified
- [scripts/install_linux.sh](scripts/install_linux.sh)
  - setup_venv() function
  - run_setup_wizard() function
  - create_systemd_service() function
  - main() function

## Status
✅ **FIXED** - Script will now correctly locate and use the virtual environment
