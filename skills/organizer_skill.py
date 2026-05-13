"""
skills/organizer_skill.py
DNA Desktop & Folder Organizer Skill

Behavior:
  1. Scan target folder (default: Desktop)
  2. Classify files by extension into categories
  3. SPEAK a preview — "I found 12 files. 4 PDFs, 3 images, 2 scripts..."
  4. ASK for confirmation — "Shall I organize them?"
  5. Only move files after explicit "yes" / "go ahead" / "do it"
  6. Report what was done
  7. Create an undo log so moves can be reversed

Never moves: folders, shortcuts (.lnk), system files
Never overwrites: if file exists in destination, renames with timestamp
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

from config import DESKTOP_PATH, ORGANIZER_UNDO_LOG, ORGANIZER_CONFIRM_TIMEOUT

logger = logging.getLogger('dna.skill.organizer')

# ── File Category Map ─────────────────────────────────────────────────────────

CATEGORIES = {
    "PDFs":        [".pdf"],
    "Images":      [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
                    ".svg", ".ico", ".tiff"],
    "Videos":      [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Audio":       [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "Documents":   [".doc", ".docx", ".odt", ".txt", ".rtf", ".pages"],
    "Spreadsheets":[".xls", ".xlsx", ".csv", ".ods"],
    "Presentations":[".ppt", ".pptx", ".odp"],
    "Archives":    [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Scripts":     [".py", ".js", ".ts", ".sh", ".bat", ".ps1",
                    ".rb", ".php", ".r"],
    "Code":        [".html", ".css", ".json", ".xml", ".yaml", ".yml",
                    ".toml", ".ini", ".cfg", ".sql"],
    "Executables": [".exe", ".msi", ".dmg", ".deb", ".apk"],
    "Data":        [".parquet", ".feather", ".h5", ".hdf5", ".pkl",
                    ".joblib", ".npy", ".npz"],
    "Notebooks":   [".ipynb"],
}

# Extensions to never touch
SKIP_EXTENSIONS = {".lnk", ".url", ".desktop"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_category(ext: str) -> str:
    """Return category name for a file extension."""
    ext = ext.lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"

def _safe_move(src: Path, dst_dir: Path) -> Path:
    """
    Move file to dst_dir. If file with same name exists,
    append timestamp to avoid overwrite.
    Returns final destination path.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name

    if dst.exists():
        stem = src.stem
        suffix = src.suffix
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = dst_dir / f"{stem}_{ts}{suffix}"

    shutil.move(str(src), str(dst))
    return dst

def _scan_folder(folder: Path) -> dict:
    """
    Scan folder for organizable files.
    Returns dict: {category: [Path, ...]}
    """
    categorized = {}
    for item in folder.iterdir():
        # Skip: directories, shortcuts, hidden files
        if item.is_dir():
            continue
        if item.suffix.lower() in SKIP_EXTENSIONS:
            continue
        if item.name.startswith("."):
            continue

        category = _get_category(item.suffix)
        categorized.setdefault(category, []).append(item)

    return categorized

def _build_preview(categorized: dict, folder_name: str = "Desktop") -> str:
    """Build a spoken preview of what will be organized."""
    total = sum(len(v) for v in categorized.values())
    if total == 0:
        return "no_files"

    parts = []
    for cat, files in sorted(categorized.items(), key=lambda x: -len(x[1])):
        count = len(files)
        parts.append(f"{count} {'file' if count == 1 else 'files'} in {cat}")

    summary = ", ".join(parts[:5])
    if len(parts) > 5:
        summary += ", and more"

    return (f"I found {total} {'file' if total == 1 else 'files'} in your {folder_name}. "
            f"{summary}. "
            f"Shall I organize them into folders? Say yes to proceed or no to cancel.")

def _save_undo_log(moves: list[dict]):
    """Save move log for undo capability."""
    log_path = Path(ORGANIZER_UNDO_LOG)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if log_path.exists():
        try:
            with open(log_path) as f:
                existing = json.load(f)
        except Exception:
            existing = []

    existing.extend(moves)

    with open(log_path, "w") as f:
        json.dump(existing[-500:], f, indent=2)  # keep last 500 moves


# ── Pending confirmation state ────────────────────────────────────────────────
# Used to hold scan results while waiting for user to say yes/no

_pending = {
    "folder":      None,
    "categorized": None,
    "expires_at":  0.0
}

def _clear_pending():
    _pending["folder"]      = None
    _pending["categorized"] = None
    _pending["expires_at"]  = 0.0

def has_pending() -> bool:
    """Check if there's a pending organize action awaiting confirmation."""
    return bool(_pending["categorized"]) and time.time() < _pending["expires_at"]


# ── Main Tools ────────────────────────────────────────────────────────────────

def preview_organize(folder_path: str = None) -> str:
    """
    Scan Desktop (or given folder) and speak a preview.
    Does NOT move anything. Sets pending state for confirmation.
    """
    try:
        folder = Path(folder_path) if folder_path else Path(DESKTOP_PATH)

        if not folder.exists():
            return f"Could not find the folder: {folder}"

        categorized = _scan_folder(folder)

        if not categorized:
            folder_name = folder.name or "Desktop"
            return f"Your {folder_name} is already clean. No files to organize."

        # Store pending state
        _pending["folder"]      = folder
        _pending["categorized"] = categorized
        _pending["expires_at"]  = time.time() + ORGANIZER_CONFIRM_TIMEOUT

        folder_name = folder.name or "Desktop"
        return _build_preview(categorized, folder_name)

    except Exception as e:
        logger.error('preview_organize failed: %s', e)
        return f"Could not scan the folder: {str(e)}"


def confirm_organize() -> str:
    """
    Execute the pending organization. Called when user says yes/go ahead.
    """
    try:
        if not _pending["categorized"]:
            return "No pending organization. Say organize my desktop first."

        if time.time() > _pending["expires_at"]:
            _clear_pending()
            return ("That request expired. "
                    "Say organize my desktop again to start fresh.")

        folder      = _pending["folder"]
        categorized = _pending["categorized"]
        _clear_pending()

        moves = []
        moved_count = 0
        failed_count = 0

        for category, files in categorized.items():
            dst_dir = folder / category
            for src in files:
                try:
                    dst = _safe_move(src, dst_dir)
                    moves.append({
                        "timestamp": datetime.now().isoformat(),
                        "from":      str(src),
                        "to":        str(dst),
                        "category":  category
                    })
                    moved_count += 1
                except Exception:
                    failed_count += 1

        if moves:
            _save_undo_log(moves)

        folder_name = folder.name or "Desktop"
        result = f"Done. Moved {moved_count} files into {len(categorized)} folders in {folder_name}."
        if failed_count:
            result += f" {failed_count} files could not be moved."
        result += " I have saved an undo log in case you want to reverse this."

        logger.info('Organized %d files in %s', moved_count, folder)
        return result

    except Exception as e:
        _clear_pending()
        logger.error('confirm_organize failed: %s', e)
        return f"Organization failed: {str(e)}"


def cancel_organize() -> str:
    """Cancel pending organization."""
    if _pending["categorized"]:
        _clear_pending()
        return "Cancelled. Nothing was moved."
    return "No pending organization to cancel."


def undo_organize() -> str:
    """
    Reverse the last organization batch by reading the undo log.
    Moves files back to their original locations.
    """
    try:
        log_path = Path(ORGANIZER_UNDO_LOG)
        if not log_path.exists():
            return "No undo log found. Nothing to reverse."

        with open(log_path) as f:
            moves = json.load(f)

        if not moves:
            return "The undo log is empty."

        # Group by timestamp batch — undo most recent batch
        # Find all moves from the last organize session (same minute)
        latest_ts = moves[-1]["timestamp"][:16]  # YYYY-MM-DDTHH:MM
        batch = [m for m in moves if m["timestamp"][:16] == latest_ts]

        restored = 0
        failed   = 0

        for move in reversed(batch):
            try:
                src = Path(move["to"])
                dst = Path(move["from"])
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                    restored += 1
            except Exception:
                failed += 1

        # Remove undone batch from log
        remaining = [m for m in moves if m["timestamp"][:16] != latest_ts]
        with open(log_path, "w") as f:
            json.dump(remaining, f, indent=2)

        result = f"Restored {restored} files to their original locations."
        if failed:
            result += f" {failed} files could not be restored."
        
        logger.info('Undo organize: restored %d files', restored)
        return result

    except Exception as e:
        logger.error('undo_organize failed: %s', e)
        return f"Undo failed: {str(e)}"


def organize_downloads() -> str:
    """Preview organization of Downloads folder."""
    downloads = Path.home() / "Downloads"
    return preview_organize(str(downloads))


def organize_folder(path: str) -> str:
    """Preview organization of a specific folder."""
    return preview_organize(path)


def clean_empty_folders(folder_path: str = None) -> str:
    """Remove empty folders left after organization."""
    try:
        folder = Path(folder_path) if folder_path else Path(DESKTOP_PATH)
        removed = 0
        for item in folder.iterdir():
            if item.is_dir():
                try:
                    item.rmdir()   # only removes if empty
                    removed += 1
                except OSError:
                    pass           # not empty, skip
        if removed:
            return f"Removed {removed} empty folders."
        return "No empty folders found."
    except Exception as e:
        logger.error('clean_empty_folders failed: %s', e)
        return f"Could not clean folders: {str(e)}"


# ── Skill Contract ────────────────────────────────────────────────────────────

TOOLS = {
    "preview_organize":    preview_organize,
    "confirm_organize":    confirm_organize,
    "cancel_organize":     cancel_organize,
    "undo_organize":       undo_organize,
    "organize_downloads":  organize_downloads,
    "organize_folder":     organize_folder,
    "clean_empty_folders": clean_empty_folders,
}
