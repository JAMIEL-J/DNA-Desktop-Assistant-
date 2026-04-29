import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).resolve().parent


def _resolve_downloads_dir() -> Path:
    """Resolve the user's real Downloads directory on Windows with fallbacks."""
    candidates: list[Path] = []

    if os.name == 'nt':
        try:
            import winreg  # stdlib on Windows

            key_path = r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
            guid = '{374DE290-123F-4565-9164-39C4925E467B}'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _ = winreg.QueryValueEx(key, guid)
                if value:
                    candidates.append(Path(os.path.expandvars(value)))
        except Exception:
            pass

    # Common defaults and redirected OneDrive path.
    candidates.extend([
        Path.home() / 'Downloads',
        Path(os.getenv('USERPROFILE', '')) / 'Downloads',
        Path.home() / 'OneDrive' / 'Downloads',
    ])

    # Fallbacks for systems where downloads are redirected to drive roots.
    candidates.extend([
        Path('D:\\Downloads'),
        Path('D:\\'),
        Path('E:\\Downloads'),
    ])

    for candidate in candidates:
        if str(candidate).strip() and candidate.exists():
            return candidate

    return Path.home()

# Pipeline Settings
LOG_PATH = BASE_DIR / os.getenv('LOG_PATH', 'logs/dna.log')
DB_PATH = BASE_DIR / os.getenv('DB_PATH', 'data/dna_memory.db')
DUCK_PATH = BASE_DIR / os.getenv('DUCK_PATH', 'data/dna_duck.db')
DOWNLOADS_DIR = _resolve_downloads_dir()

# Model Settings
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'float32')
WHISPER_DEVICE = os.getenv('WHISPER_DEVICE', 'cpu')
WAKE_WORD_MODEL = os.getenv('WAKE_WORD_MODEL', 'hey_jarvis')
WAKE_WORD_THRESHOLD = float(os.getenv('WAKE_WORD_THRESHOLD', '0.5'))
WAKE_WORD_FRAMEWORK = os.getenv('WAKE_WORD_FRAMEWORK', 'onnx')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
CLOUD_LLM_MODEL = os.getenv('CLOUD_LLM_MODEL', 'gemini-1.5-flash')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma4:e2b')
OLLAMA_VISION_MODEL = os.getenv('OLLAMA_VISION_MODEL', 'moondream')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/chat')
OLLAMA_TIMEOUT = float(os.getenv('OLLAMA_TIMEOUT', '45'))
OLLAMA_CTX_NORMAL = int(os.getenv('OLLAMA_CTX_NORMAL', '2048'))
OLLAMA_CTX_THINKING = int(os.getenv('OLLAMA_CTX_THINKING', '2048'))
OLLAMA_TEMPERATURE = float(os.getenv('OLLAMA_TEMPERATURE', '0.2'))
OLLAMA_KEEP_ALIVE = os.getenv('OLLAMA_KEEP_ALIVE', '1m')

# TTS Settings
PIPER_VOICE = os.getenv('PIPER_VOICE', 'en_US-lessac-medium')
PIPER_MODEL_DIR = BASE_DIR / 'data' / 'models' / 'piper'
PIPER_MODEL_PATH = PIPER_MODEL_DIR / f'{PIPER_VOICE}.onnx'
PIPER_MODEL_JSON = PIPER_MODEL_DIR / f'{PIPER_VOICE}.onnx.json'

# Audio Settings
SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5
SILENCE_THRESHOLD = float(os.getenv('SILENCE_THRESHOLD', '0.006'))
SILENCE_DURATION = 1.5
END_OF_SPEECH_SILENCE = float(os.getenv('END_OF_SPEECH_SILENCE', '1.2'))
MIN_SPEECH_SECONDS = float(os.getenv('MIN_SPEECH_SECONDS', '0.7'))
MIC_CHUNK_SECONDS = float(os.getenv('MIC_CHUNK_SECONDS', '0.12'))
MIC_PRE_ROLL_SECONDS = float(os.getenv('MIC_PRE_ROLL_SECONDS', '0.30'))

# Session Mode Settings
AUTO_SLEEP_TIMEOUT = int(os.getenv('AUTO_SLEEP_TIMEOUT', '300'))
SHORT_TRANSCRIPT_MIN = int(os.getenv('SHORT_TRANSCRIPT_MIN', '1'))
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '-1.4'))
TTS_SUPPRESS_MS = int(os.getenv('TTS_SUPPRESS_MS', '500'))
ACTIVE_LISTEN_SECONDS = float(os.getenv('ACTIVE_LISTEN_SECONDS', '6.5'))
ACTIVE_RETRY_SECONDS = float(os.getenv('ACTIVE_RETRY_SECONDS', '5.0'))
STT_FAST_BEAM_SIZE = int(os.getenv('STT_FAST_BEAM_SIZE', '2'))
STT_ROBUST_BEAM_SIZE = int(os.getenv('STT_ROBUST_BEAM_SIZE', '5'))

# Suggestion Engine Settings
SUGGESTIONS_ENABLED = os.getenv('SUGGESTIONS_ENABLED', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
STARTUP_SUGGESTIONS_ENABLED = os.getenv('STARTUP_SUGGESTIONS_ENABLED', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
STARTUP_SUGGESTION_MIN_COUNT = int(os.getenv('STARTUP_SUGGESTION_MIN_COUNT', '3'))
STARTUP_SUGGESTION_MIN_CONFIDENCE = float(os.getenv('STARTUP_SUGGESTION_MIN_CONFIDENCE', '0.55'))
STARTUP_SUGGESTION_COOLDOWN_MINUTES = int(os.getenv('STARTUP_SUGGESTION_COOLDOWN_MINUTES', '180'))

# Conversational pacing controls for friendlier butler delivery.
TTS_HUMAN_PAUSE_MIN_SEC = float(os.getenv('TTS_HUMAN_PAUSE_MIN_SEC', '0.18'))
TTS_HUMAN_PAUSE_MAX_SEC = float(os.getenv('TTS_HUMAN_PAUSE_MAX_SEC', '0.34'))

WAKE_RESPONSES = [
    'Yes sir, I am listening.',
    'At your service, sir.',
    'Please go ahead, sir.',
    'I am listening, sir.',
    'Ready when you are, sir.',
    'Please continue, sir.',
]

SLEEP_RESPONSES = [
    'Understood, sir. I will remain on standby.',
    'Very well, sir. Call me when needed.',
    'As you wish, sir. I will stay quiet for now.',
    'Of course, sir. Stepping back.',
]

TIMEOUT_RESPONSES = [
    'I will give you some quiet time, sir.',
    'I am here whenever you need me, sir.',
    'Standing by, sir.',
]

DISMISS_RESPONSES = [
    'Understood, sir. I am stepping back.',
    'Certainly, sir. Going quiet now.',
    'As requested, sir. I will wait for your call.',
    'Very well, sir. I remain at your service.',
]

# Workflow Templates
# Declarative plans executed by the plan executor when the trigger phrase matches.
WORKFLOWS = {
    'work mode': [
        {'tool': 'speak', 'args': {'text': 'Activating work mode. Let me get you set up.'}},
        {'tool': 'open_app', 'args': {'app_name': 'vscode'}},
        {'tool': 'announce_app_opening', 'args': {'app_name': 'VS Code'}},
        {'tool': 'open_app', 'args': {'app_name': 'chrome'}},
        {'tool': 'announce_app_opening', 'args': {'app_name': 'Chrome'}},
        {'tool': 'set_volume', 'args': {'level': '40'}},
        {'tool': 'gather_work_context', 'args': {}},
    ],
    'focus mode': [
        {'tool': 'speak', 'args': {'text': 'Entering focus mode. Minimizing distractions.'}},
        {'tool': 'open_app', 'args': {'app_name': 'vscode'}},
        {'tool': 'announce_app_opening', 'args': {'app_name': 'VS Code'}},
        {'tool': 'set_volume', 'args': {'level': '30'}},
    ],
    'end work': [
        {'tool': 'speak', 'args': {'text': 'Wrapping up your work session. Taking a screenshot for your records.'}},
        {'tool': 'take_screenshot', 'args': {}},
        {'tool': 'close_app', 'args': {'app_name': 'vscode'}},
        {'tool': 'speak', 'args': {'text': 'VS Code closed.'}},
        {'tool': 'set_volume', 'args': {'level': '60'}},
        {'tool': 'speak', 'args': {'text': 'Great job today. See you next time.'}},
    ],
}

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

_NOTION_PATH = Path(os.getenv('LOCALAPPDATA', '')) / 'Programs' / 'Notion' / 'Notion.exe'

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
    'vlcmediaplayer': r'C:\Program Files\VideoLAN\VLC\vlc.exe',
    'winzip': r'C:\Program Files (x86)\WinZip\WINZIP32.EXE',
    'win zip': r'C:\Program Files (x86)\WinZip\WINZIP32.EXE',
    'notion': str(_NOTION_PATH),
    'potion': str(_NOTION_PATH),
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
    'notion': 'Notion',
    'potion': 'Notion',
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
    'notion': 'Notion.exe',
    'potion': 'Notion.exe',
}


# Common Folder Paths (Windows)
FOLDER_ALIASES = {
    'downloads': DOWNLOADS_DIR,
    'desktop': Path.home() / 'Desktop',
    'documents': Path.home() / 'Documents',
    'music': Path.home() / 'Music',
    'videos': Path.home() / 'Videos',
    'pictures': Path.home() / 'Pictures',
    'photos': Path.home() / 'Pictures',
    # Add your CUSTOM FOLDERS here:
    # 'projects': r'D:\Projects',
}

# Job Search Settings
JOBS_ROLES        = ["data analyst", "data science", "business analyst"]
JOBS_LOCATION     = "South India"
JOBS_MAX_AGE_DAYS = 7       # only show jobs posted in last 7 days
JOBS_ON_STARTUP   = True    # check for new jobs every morning on startup
