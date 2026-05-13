# ═══════════════════════════════════════════════════════════════
# ADD TO config.py
# ═══════════════════════════════════════════════════════════════

import os

DESKTOP_PATH             = os.path.expanduser("~/Desktop")
ORGANIZER_UNDO_LOG       = "data/organizer_undo.json"
ORGANIZER_CONFIRM_TIMEOUT = 60   # seconds to wait for yes/no before expiring


# ═══════════════════════════════════════════════════════════════
# ADD TO pipeline/intent_router.py SIMPLE_INTENTS
# (import at top: from skills import organizer_skill)
# ═══════════════════════════════════════════════════════════════

ORGANIZER_INTENTS = {

    # Trigger preview (scan + ask for confirmation)
    r"(organize|clean up|sort|tidy).*(desktop|files)":
        lambda m: organizer_skill.preview_organize(),

    r"(organize|clean|sort).*(download|downloads)":
        lambda m: organizer_skill.organize_downloads(),

    r"organize (the )?folder (.+)":
        lambda m: organizer_skill.organize_folder(m.group(2)),

    # Confirmation — user says yes after preview
    r"^(yes|yeah|go ahead|do it|confirm|proceed|sure|ok|okay)$":
        lambda m: organizer_skill.confirm_organize(),

    # Cancellation
    r"^(no|nope|cancel|stop|never mind|don't|dont)$":
        lambda m: organizer_skill.cancel_organize(),

    # Undo
    r"(undo|reverse|revert).*(organiz|move|sort)":
        lambda m: organizer_skill.undo_organize(),

    # Clean empty folders after organizing
    r"(clean|remove).*(empty|blank).*(folder|directory)":
        lambda m: organizer_skill.clean_empty_folders(),
}

# ⚠️ Important: Add ORGANIZER_INTENTS into SIMPLE_INTENTS dict,
# but make sure the yes/no patterns are BELOW dismiss patterns.
# "yes" and "no" are short and could conflict with other intents.
# Add a pending_confirmation check before routing yes/no:

# In intent_router.py, before SIMPLE_INTENTS check, add:
#
# from skills.organizer_skill import _pending, confirm_organize, cancel_organize
#
# def route(command: str):
#     cmd = command.lower().strip()
#
#     # Check dismiss first (existing)
#     if is_dismiss_command(cmd):
#         return None, "dismiss"
#
#     # Check pending confirmation (organizer or any other pending action)
#     if _pending["categorized"] and time.time() < _pending["expires_at"]:
#         if re.search(r'^(yes|yeah|go ahead|do it|confirm|proceed|sure|ok|okay)$', cmd):
#             return confirm_organize(), "simple"
#         if re.search(r'^(no|nope|cancel|stop|never mind)$', cmd):
#             return cancel_organize(), "simple"
#
#     # Then rest of SIMPLE_INTENTS routing...


# ═══════════════════════════════════════════════════════════════
# FOLDER STRUCTURE CREATED ON DESKTOP
# ═══════════════════════════════════════════════════════════════

# Desktop/
# ├── PDFs/
# ├── Images/
# ├── Videos/
# ├── Audio/
# ├── Documents/
# ├── Spreadsheets/
# ├── Presentations/
# ├── Archives/
# ├── Scripts/
# ├── Code/
# ├── Executables/
# ├── Data/
# ├── Notebooks/
# └── Others/


# ═══════════════════════════════════════════════════════════════
# EXAMPLE CONVERSATIONS
# ═══════════════════════════════════════════════════════════════

# [Full organize flow]
# You : "Organize my desktop"
# DNA : "I found 23 files on your Desktop.
#        8 files in PDFs, 6 files in Images, 4 files in Documents,
#        3 files in Scripts, 2 files in Others.
#        Shall I organize them into folders? Say yes to proceed or no to cancel."
# You : "Yes"
# DNA : "Done. Moved 23 files into 5 folders on your Desktop.
#        I've saved an undo log in case you want to reverse this."

# [Undo]
# You : "Undo the organize"
# DNA : "Restored 23 files to their original locations."

# [Downloads]
# You : "Organize my downloads"
# DNA : "I found 47 files in Downloads. 12 in Archives, 9 in Executables..."
# You : "Go ahead"
# DNA : "Done. Moved 47 files into 6 folders in Downloads."

# [Specific folder]
# You : "Organize the folder D:\Projects"
# DNA : "I found 15 files in Projects. 8 scripts, 4 notebooks, 3 data files.
#        Shall I organize them?"
# You : "Yes"
# DNA : "Done."

# [Cancel]
# You : "Organize my desktop"
# DNA : "I found 23 files... Shall I organize them?"
# You : "No"
# DNA : "Cancelled. Nothing was moved."

# [Already clean]
# You : "Organize my desktop"
# DNA : "Your Desktop is already clean. No files to organize."


# ═══════════════════════════════════════════════════════════════
# NO NEW INSTALLS NEEDED
# shutil, os, pathlib, json — all stdlib
# ═══════════════════════════════════════════════════════════════
