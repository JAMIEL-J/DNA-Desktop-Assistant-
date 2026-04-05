import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Pipeline Settings
LOG_PATH = BASE_DIR / os.getenv('LOG_PATH', 'logs/dna.log')
DB_PATH = BASE_DIR / os.getenv('DB_PATH', 'data/dna_memory.db')
DUCK_PATH = BASE_DIR / os.getenv('DUCK_PATH', 'data/dna_duck.db')

# Model Settings
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'float32')
WHISPER_DEVICE = os.getenv('WHISPER_DEVICE', 'cpu')
WAKE_WORD_MODEL = os.getenv('WAKE_WORD_MODEL', 'hey_jarvis')
WAKE_WORD_THRESHOLD = float(os.getenv('WAKE_WORD_THRESHOLD', '0.5'))
WAKE_WORD_FRAMEWORK = os.getenv('WAKE_WORD_FRAMEWORK', 'onnx')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3.5:2b')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/chat')
OLLAMA_TIMEOUT = float(os.getenv('OLLAMA_TIMEOUT', '20'))
OLLAMA_CTX_NORMAL = int(os.getenv('OLLAMA_CTX_NORMAL', '2048'))
OLLAMA_CTX_THINKING = int(os.getenv('OLLAMA_CTX_THINKING', '4096'))
OLLAMA_TEMPERATURE = float(os.getenv('OLLAMA_TEMPERATURE', '0.1'))

# TTS Settings
PIPER_VOICE = os.getenv('PIPER_VOICE', 'en_US-lessac-medium')
PIPER_MODEL_DIR = BASE_DIR / 'data' / 'models' / 'piper'
PIPER_MODEL_PATH = PIPER_MODEL_DIR / f'{PIPER_VOICE}.onnx'
PIPER_MODEL_JSON = PIPER_MODEL_DIR / f'{PIPER_VOICE}.onnx.json'

# Audio Settings
SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.5

# Wake Word Audio Settings
WAKE_CHUNK_SIZE = 1280  # 80ms at 16kHz — openwakeword expects this

# Common App Paths (Windows)
# We prioritize common install locations and user-specific paths
_USER_LOCAL_CHROME = Path(os.getenv('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe'
_PROG_FILES_CHROME = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
_CHROME_PATH = str(_USER_LOCAL_CHROME) if _USER_LOCAL_CHROME.exists() else str(_PROG_FILES_CHROME)

_EDGE_PATH_X86 = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
_EDGE_PATH = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
_FINAL_EDGE = _EDGE_PATH_X86 if Path(_EDGE_PATH_X86).exists() else _EDGE_PATH

APP_ALIASES = {
    'notepad': 'notepad.exe',
    'calculator': 'calc.exe',
    'calc': 'calc.exe',
    'explorer': 'explorer.exe',
    'file explorer': 'explorer.exe',
    'fileexplorer': 'explorer.exe',
    'files': 'explorer.exe',
    'cmd': 'cmd.exe',
    'command prompt': 'cmd.exe',
    'commandprompt': 'cmd.exe',
    'terminal': 'wt.exe',
    'task manager': 'taskmgr.exe',
    'taskmanager': 'taskmgr.exe',
    'settings': 'ms-settings:',
    'paint': 'mspaint.exe',
    'ms paint': 'mspaint.exe',
    'snipping tool': 'snippingtool.exe',
    'snippingtool': 'snippingtool.exe',
    'chrome': _CHROME_PATH,
    'google chrome': _CHROME_PATH,
    'googlechrome': _CHROME_PATH,
    'edge': _FINAL_EDGE,
    'microsoft edge': _FINAL_EDGE,
    'microsoftedge': _FINAL_EDGE,
    'vscode': 'code',
    'vs code': 'code',
    'visual studio code': 'code',
    'visualstudiocode': 'code',
    # Added from Desktop / Requirements
    'whatsapp': 'whatsapp:',
    'whats up': 'whatsapp:',
    'whatsup': 'whatsapp:',
    'whatsapp web': 'https://web.whatsapp.com',
    'whatsappweb': 'https://web.whatsapp.com',
    'claude': r'shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude',
    'cloud': r'shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude',
    'clouder': r'shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude',
    'clawed': r'shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude',
    'clod': r'shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude',
    'antigravity': r'shell:AppsFolder\Google.Antigravity',
    'anti gravity': r'shell:AppsFolder\Google.Antigravity',
    'anti-gravity': r'shell:AppsFolder\Google.Antigravity',
    'gravity': r'shell:AppsFolder\Google.Antigravity',
    'anaconda': r'C:\Users\ADMIN\anaconda3\pythonw.exe',
    'ana conda': r'C:\Users\ADMIN\anaconda3\pythonw.exe',
    'capcut': r'C:\Users\ADMIN\AppData\Local\CapCut\Apps\CapCut.exe',
    'cap cut': r'C:\Users\ADMIN\AppData\Local\CapCut\Apps\CapCut.exe',
    'acrobat': r'C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe',
    'adobe acrobat': r'C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe',
    'acrobat reader': r'C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe',
    'tableau': r'C:\Program Files\Tableau\Tableau Public 2025.3\bin\tabpublic.exe',
    'table': r'C:\Program Files\Tableau\Tableau Public 2025.3\bin\tabpublic.exe',
    'tally erp': r'C:\Program Files\Tally\Tally.ERP9\tally.exe',
    'tallyerp': r'C:\Program Files\Tally\Tally.ERP9\tally.exe',
    'tally prime': r'C:\Program Files\TallyPrime\tally.exe',
    'tallyprime': r'C:\Program Files\TallyPrime\tally.exe',
    'vlc': r'C:\Program Files (x86)\VideoLAN\VLC\vlc.exe',
    'vlc media player': r'C:\Program Files (x86)\VideoLAN\VLC\vlc.exe',
    'vlc player': r'C:\Program Files (x86)\VideoLAN\VLC\vlc.exe',
    'vlcmediaplayer': r'C:\Program Files (x86)\VideoLAN\VLC\vlc.exe',
    'winzip': r'C:\Program Files (x86)\WinZip\WINZIP32.EXE',
    'win zip': r'C:\Program Files (x86)\WinZip\WINZIP32.EXE',
}

# Maps aliases to their properly capitalized/pronounced names for STT/TTS replies
APP_PROPER_NAMES = {
    'cloud': 'Claude',
    'clouder': 'Claude',
    'clawed': 'Claude',
    'clod': 'Claude',
    'claude': 'Claude',
    'whats up': 'WhatsApp',
    'whatsup': 'WhatsApp',
    'cap cut': 'CapCut',
    'ana conda': 'Anaconda',
    'table': 'Tableau',
}

# Maps aliases to their actual Windows process names for taskkill
APP_PROCESS_MAP = {
    'claude': 'claude.exe',
    'cloud': 'claude.exe',
    'clouder': 'claude.exe',
    'clawed': 'claude.exe',
    'clod': 'claude.exe',
    'whatsapp': 'WhatsApp.Root.exe',
    'whats up': 'WhatsApp.Root.exe',
    'whatsup': 'WhatsApp.Root.exe',
    'antigravity': 'Antigravity.exe',
    'anti gravity': 'Antigravity.exe',
    'anti-gravity': 'Antigravity.exe',
    'gravity': 'Antigravity.exe',
    'vscode': 'Code.exe',
    'vs code': 'Code.exe',
    'visual studio code': 'Code.exe',
    'visualstudiocode': 'Code.exe',
    'chrome': 'chrome.exe',
    'google chrome': 'chrome.exe',
    'googlechrome': 'chrome.exe',
    'edge': 'msedge.exe',
    'microsoft edge': 'msedge.exe',
    'microsoftedge': 'msedge.exe',
    'tableau': 'tabpublic.exe',
    'table': 'tabpublic.exe',
    'anaconda': 'pythonw.exe',
    'ana conda': 'pythonw.exe',
    'notepad': 'notepad.exe',
    'calculator': 'calc.exe',
    'calc': 'calc.exe',
    'file explorer': 'explorer.exe',
    'fileexplorer': 'explorer.exe',
    'explorer': 'explorer.exe',
    'files': 'explorer.exe',
    'cmd': 'cmd.exe',
    'command prompt': 'cmd.exe',
    'terminal': 'wt.exe',
}


# Common Folder Paths (Windows)
FOLDER_ALIASES = {
    'downloads': Path.home() / 'Downloads',
    'desktop': Path.home() / 'Desktop',
    'documents': Path.home() / 'Documents',
    'music': Path.home() / 'Music',
    'videos': Path.home() / 'Videos',
    'pictures': Path.home() / 'Pictures',
    'photos': Path.home() / 'Pictures',
    # Add your CUSTOM FOLDERS here:
    # 'projects': r'D:\Projects',
}
