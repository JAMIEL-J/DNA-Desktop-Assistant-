# 1. stdlib
import os
import sys
import subprocess
import logging
from pathlib import Path

# 2. internal
from config import FOLDER_ALIASES

logger = logging.getLogger('dna.skill.file')

# Add common variants locally
_FOLDER_VARIANTS = {
    'download': 'downloads',
    'document': 'documents',
    'video': 'videos',
    'picture': 'pictures',
    'photo': 'pictures',
    'photos': 'pictures',
}


def _resolve_folder(name: str) -> tuple:
    """Resolve a spoken folder name to an actual Path.
    
    Checks config.FOLDER_ALIASES for mappings.
    """
    original_name = name.strip()
    clean = original_name.lower()
    
    # Check for direct alias (case-insensitive)
    path = FOLDER_ALIASES.get(clean)
    
    # Try common variants if not found
    if not path and clean in _FOLDER_VARIANTS:
        path = FOLDER_ALIASES.get(_FOLDER_VARIANTS[clean])
        
    if not path:
        # Recursive Search (Depth 2): Look for a subfolder with this name deeper in common bases
        # We limit depth to 2 to keep it fast on i3 CPUs
        search_bases = [Path.home(), Path.home() / 'Desktop', Path.home() / 'Documents']
        for base in search_bases:
            if not base.exists(): continue
            try:
                # Level 1: Check EXACT match first (case-sensitive)
                exact_path = base / original_name
                if exact_path.is_dir():
                    path = exact_path
                    break
                
                # Level 1: Check CASE-INSENSITIVE scan
                for item in base.iterdir():
                    if item.is_dir():
                        if item.name.lower() == clean:
                            path = item
                            break
                        
                        # Level 2 scan (one level deeper)
                        try:
                            # Level 2: Exact check
                            sub_exact = item / original_name
                            if sub_exact.is_dir():
                                path = sub_exact
                                break
                                
                            # Level 2: Case-insensitive scan
                            for sub_item in item.iterdir():
                                if sub_item.is_dir() and sub_item.name.lower() == clean:
                                    path = sub_item
                                    break
                        except PermissionError:
                            continue
                    if path: break
                if path: break
            except PermissionError:
                continue

    if not path:
        return None, f"I couldn't find a folder called {name} in your user profile (searching up to 2 levels deep). You can add it to config.py for direct access."

    target = Path(path)
    if not target.exists():
        return None, f"The folder at {path} does not exist."

    return target, target.name


def list_files(directory: str) -> str:
    """List files in common Windows directories like Desktop, Downloads, or Documents."""
    try:
        target, display = _resolve_folder(directory)
        if target is None:
            return display  # display holds the error message

        items = os.listdir(target)
        if not items:
            return f'Your {display} folder is empty.'

        files = [f for f in items if (target / f).is_file()]
        if not files:
            return f'Your {display} folder has no files, only subfolders.'

        count = len(files)
        limit = 5
        to_speak = files[:limit]

        result = f'Found {count} files in your {display} folder. '
        result += 'The first few are: ' + ', '.join(to_speak)
        if count > limit:
            result += f', and {count - limit} more.'

        return result

    except Exception as e:
        logger.error('list_files failed: %s', e)
        return f'Could not list your files: {str(e)}'


def open_folder(directory: str) -> str:
    """Open a common folder in Explorer."""
    try:
        target, display = _resolve_folder(directory)
        if target is None:
            return display

        if sys.platform == 'win32':
            os.startfile(target)
        elif sys.platform == 'darwin':
            subprocess.run(['open', target], check=True)
        else:
            subprocess.run(['xdg-open', target], check=True)
        return f'Opening your {display} folder.'

    except Exception as e:
        logger.error('open_folder failed: %s', e)
        return f'Could not open the folder: {str(e)}'


# Skill module contract
TOOLS = {
    'list_files': list_files,
    'open_folder': open_folder,
}
