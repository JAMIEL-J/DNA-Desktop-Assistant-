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
WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')
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
APP_ALIASES = {
    'notepad': 'notepad.exe',
    'calculator': 'calc.exe',
    'calc': 'calc.exe',
    'explorer': 'explorer.exe',
    'file explorer': 'explorer.exe',
    'files': 'explorer.exe',
    'cmd': 'cmd.exe',
    'command prompt': 'cmd.exe',
    'terminal': 'wt.exe',
    'task manager': 'taskmgr.exe',
    'settings': 'ms-settings:',
    'paint': 'mspaint.exe',
    'snipping tool': 'snippingtool.exe',
    'chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'google chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'edge': r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'microsoft edge': r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'vscode': 'code',
    'vs code': 'code',
    'visual studio code': 'code',
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
