# 🧬 DNA — Desktop Natural Assistant

> **Your Personal AI Butler** — A privacy-first, offline-only voice assistant for Windows that responds to natural language commands with intelligent action.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Windows Only](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status: Active Development](https://img.shields.io/badge/status-Active%20Development-brightgreen.svg)]()

---

## 🎯 What is DNA?

**DNA (Desktop Natural Assistant)** is a sophisticated, voice-controlled desktop automation system built specifically for Windows. It combines advanced speech recognition, natural language processing, and intelligent intent routing to provide a seamless hands-free experience—all running **100% offline and locally** for maximum privacy.

Unlike cloud-based assistants, DNA never sends your voice, commands, or personal data to external servers. Everything stays on your machine, processed by lightweight local AI models optimized for consumer hardware.

---

## ✨ Key Features

### 🎤 **Voice Control**
- **Natural Language Commands**: Speak in your own words, DNA understands context and nuance
- **Wake Word Detection**: Say "Hey Jarvis" or "Hey DNA" to activate (supports custom wake words)
- **Smart Session Mode**: Stays awake and responsive after activation, auto-sleeps when idle
- **Continuation Capture**: Automatically captures multi-part commands for incomplete speech recognition
- **Confidence-Based Retry**: Intelligently re-records if confidence is low

### 🧠 **Intelligent Intent Routing**
- **Fast Path (Regex)**: Lightning-fast execution for common commands (<10ms)
- **Smart Path (LLM)**: Falls back to local LLM for complex, ambiguous requests
  - **Primary**: Google Gemini 1.5 Flash (`gemini-1.5-flash` model, when `GOOGLE_API_KEY` is present)
  - **Fallback**: Local Ollama models (100% offline, no API key needed)
- **Confirmation Gates**: Dangerous operations require spoken confirmation for safety
- **Context Awareness**: Resolves pronouns and maintains session state across commands
- **Morning Briefing**: Automatic weather, news, and job suggestions at startup

### 🛠️ **Rich Skill System**
DNA includes 14+ modular skills for diverse functionality:

| Skill | Capabilities |
|-------|--------------|
| **System Skill** | App/process management, volume, brightness, media control, window management |
| **File Skill** | Open, copy, move, delete, organize files with voice confirmation |
| **Data Skill** | Query CSV files, generate charts, perform data analysis with natural language |
| **Browser Skill** | Search web, open websites, manage tabs |
| **Chat Skill** | Conversation with local LLM, context-aware responses |
| **Vision Skill** | Screenshot analysis, visual Q&A using local vision models |
| **Screen Skill** | Capture, annotate, save screenshots |
| **Weather Skill** | Real-time weather queries (OpenWeatherMap API) |
| **News Skill** | Aggregated news updates, topic search |
| **Job Search Skill** | Search job listings, filter by role, location, experience |
| **Organizer Skill** | Smart file organization, undo support, batch operations |
| **Learning Skill** | Educational queries, concept explanations |
| **Web Skill** | HTTP requests, API interactions |

### 🔐 **Privacy & Security**
- ✅ **100% Offline Operation**: No cloud dependencies (except optional weather/news APIs)
- ✅ **No Data Transmission**: Your voice and commands never leave your machine
- ✅ **Path Protection**: Blocks access to critical Windows directories (C:\Windows, AppData)
- ✅ **Sandboxed Execution**: Generated Python code runs in restricted namespace
- ✅ **Confirmation Gates**: Sensitive operations require spoken approval
- ✅ **Local Databases**: SQLite for memory/preferences, DuckDB for data queries

### ⚡ **Performance Optimized**
- Runs smoothly on **8GB RAM** systems
- **4-bit quantization** for lightweight LLM inference
- **Demand loading** for resource-heavy components
- **Wake word detection** using efficient openwakeword
- **Sub-100ms** command latency for regex-matched requests

### 📊 **Data Analysis Capabilities**
- Query large datasets using **natural language to SQL (NL2SQL)** with DuckDB
- Generate charts and visualizations
- Transform data using pandas for feature engineering
- Support for CSV, Parquet, and structured databases

---

## 🏗️ Architecture Overview

### Pipeline Flow (How DNA Works)

```
┌─────────────────────────────────────────────────────────────┐
│                     USER SPEAKS                              │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
     ┌────────────────────┐
     │  WAKE WORD CHECK   │  (openwakeword)
     │  "Hey Jarvis..."   │  Detects activation phrase
     └────────┬───────────┘
              │ ✓ Wake word detected
              ▼
     ┌────────────────────┐
     │   AUDIO RECORD     │  Records 6.5s of speech
     │  (sounddevice)     │  or until silence detected
     └────────┬───────────┘
              │
              ▼
     ┌────────────────────┐
     │  SPEECH-TO-TEXT    │  (faster-whisper)
     │  Transcribe Audio  │  Fast path + robust retry
     └────────┬───────────┘
              │
              ▼
     ┌────────────────────┐
     │  TEXT NORMALIZE    │  Clean STT noise, fix punctuation
     └────────┬───────────┘
              │
              ▼
     ┌────────────────────────────────────────┐
     │    INTENT ROUTING                      │
     │  ┌──────────────────────────────────┐  │
     │  │  FAST PATH (Regex Patterns)      │  │ <10ms
     │  │  Common commands: open X, set   │  │
     │  │  volume, etc.                    │  │
     │  └──────────────┬───────────────────┘  │
     │                │                        │
     │    No match?   ▼ Falls through          │
     │  ┌──────────────────────────────────┐  │
     │  │  SMART PATH (LLM Agent)          │  │
     │  │  Gemini 1.5 Flash or Ollama      │  │
     │  │  Generates tool-call JSON plan   │  │
     │  └──────────────┬───────────────────┘  │
     └─────────────────┼──────────────────────┘
                       │
                       ▼
     ┌────────────────────────────────────┐
     │  CONTEXT RESOLUTION                │  Resolve pronouns,
     │  (context_resolver.py)             │  session state
     └────────┬─────────────────────────┘
              │
              ▼
     ┌────────────────────────────────────────┐
     │  CHECK DANGEROUS OPERATIONS            │  
     │  ┌────────────────────────────────────┐│
     │  │ Shutdown? Reboot? Kill process?   ││
     │  │ → Request SPOKEN CONFIRMATION     ││
     │  │ ┌───────────────────────────────┐ ││
     │  │ │ Wait 30s for user to confirm  │ ││
     │  │ │ or cancel                     │ ││
     │  │ └───────────────────────────────┘ ││
     │  └────────────────────────────────────┘│
     └────────┬─────────────────────────────┘
              │ ✓ Approved
              ▼
     ┌────────────────────────────────────┐
     │  PLAN EXECUTION                    │  Loop through
     │  (plan_executor.py)                │  tool-call plan
     └────────┬─────────────────────────┘
              │
              ▼
     ┌────────────────────────────────────┐
     │  SKILL EXECUTION                   │  14+ modular
     │  (skills/*.py)                     │  skills library
     │  • system_skill.py                 │
     │  • data_skill.py                   │
     │  • vision_skill.py                 │
     │  • etc.                            │
     └────────┬─────────────────────────┘
              │
              ▼
     ┌────────────────────────────────────┐
     │  RESPONSE GENERATION               │  Personality-driven
     │  (personality.py)                  │  humanized replies
     └────────┬─────────────────────────┘
              │
              ▼
     ┌────────────────────────────────────┐
     │  TEXT-TO-SPEECH                    │  (piper-tts)
     │  Speak Response Aloud              │  Natural-sounding
     │  (piper.py)                        │  butler voice
     └────────┬─────────────────────────┘
              │
              ▼
     ┌────────────────────────────────────┐
     │   LOG & MEMORY                     │  Store in SQLite
     │   (memory.py)                      │  for learning
     └────────────────────────────────────┘
```

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Pipeline** | `pipeline/` | Audio I/O, STT, intent routing, LLM reasoning, plan execution |
| **Skills** | `skills/` | 14+ modular tools for system control, data, web, vision |
| **Core Logic** | `core/` | Session management, personality, safety enforcement, monitoring |
| **UI** | `ui/` | System tray integration, desktop window, toast notifications |
| **Config** | `config.py` | Environment variables, app aliases, audio settings, thresholds |
| **Data Layer** | `data/` | SQLite for memory/preferences, DuckDB for data queries |

### Technology Stack

```
🎤 Audio Input        → sounddevice (low-latency recording)
🎙️ Wake Word           → openwakeword (efficient local detection)
📝 Speech-to-Text      → faster-whisper (local transcription, int8 quantization)
🧠 Language Model      → Google Gemini 1.5 Flash (optional) or Ollama (local fallback)
💬 Text-to-Speech      → Piper TTS (natural voices, ONNX runtime)
📊 Data Processing     → DuckDB (NL2SQL) + Pandas (transformations)
🔄 Automation          → pyautogui + Win32 APIs
💾 Memory/Preferences  → SQLite
🎨 UI Framework        → PySide6 + system tray integration
```

---

## 🚀 Quick Start

### Prerequisites

- **Windows 10/11** (64-bit)
- **Python 3.10+**
- **8GB RAM minimum** (optimized for mid-range hardware)
- **Microphone** and **speakers**
- **Ollama** (for local LLM) — [Download here](https://ollama.ai)

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/JAMIEL-J/DNA-Desktop-Assistant-.git
   cd DNA-Desktop-Assistant-
   ```

2. **Create Virtual Environment** (Recommended)
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download Ollama Models** (Required for local LLM)
   ```bash
   ollama pull gemma2:2b
   ollama pull moondream  # For vision capabilities
   ```
   
   💡 **Tip**: Start Ollama before launching DNA
   ```bash
   ollama serve
   ```

5. **Configure Environment Variables**
   
   Create a `.env` file in the project root (copy from `.env.example`):
   ```env
   # Model Settings
   WHISPER_MODEL=small                    # tiny, base, small, medium, large
   WHISPER_COMPUTE_TYPE=int8              # float32, int8, int4
   WAKE_WORD_MODEL=hey_jarvis             # or: hey_google, hey_alexa
   
   # LLM Options (prioritized in this order)
   GOOGLE_API_KEY=your_google_key         # Optional: Gemini 1.5 Flash
   OLLAMA_MODEL=gemma2:2b                 # Fallback: Local Ollama
   
   # Audio Settings
   SILENCE_THRESHOLD=0.006                # Sensitivity to background noise
   SILENCE_DURATION=1.5                   # Seconds of silence to stop recording
   
   # Session Timeout
   AUTO_SLEEP_TIMEOUT=300                 # Seconds before auto-sleep (5 minutes)
   
   # Optional: Weather API
   WEATHER_API_KEY=your_openweather_key
   WEATHER_DEFAULT_CITY=Chennai
   ```

6. **Run DNA**
   ```bash
   python dna_main.py
   ```

   The assistant will:
   - Initialize all components
   - Start system tray icon
   - Listen for wake word (default: "Hey Jarvis")
   - Deliver morning briefing (weather, news, jobs)

---

## 🎤 Usage Examples

Once DNA is running, just speak naturally. Here are example commands:

### **System Control**
```
"Open Chrome"
"Set volume to 50 percent"
"Close VS Code"
"Take a screenshot"
"Show me the system tray"
"What's the screen brightness?"
```

### **File Management**
```
"Open my Downloads folder"
"Copy file.txt to Desktop"
"Delete old_file.docx"  # (requires confirmation)
"Organize my Desktop"
"Find my resume in Documents"
```

### **Data Analysis**
```
"Query my sales data"
"Show me revenue by month"
"Create a chart of customer counts"
"Analyze this CSV"
```

### **Web & Information**
```
"Search for Python tutorials"
"What's the weather in London?"
"Tell me the latest news"
"Find data analyst jobs in Chennai"
"Show me job listings for experience level fresher"
```

### **Chat & Conversation**
```
"What is machine learning?"
"Explain quantum computing"
"How does DNA work?"  # The assistant answers about itself
```

### **Vision & Screen Analysis**
```
"What's on my screen right now?"
"Analyze this screenshot"
"Read the text from my screen"
```

### **Workflows**
```
"Work mode"           # Opens VS Code + Chrome, sets volume to 40%
"Focus mode"          # Opens VS Code, dims volume to 30%
"End work"            # Takes screenshot, closes apps, resets volume
```

---

## ⚙️ Configuration Reference

### Audio Tuning

Edit these in `.env` or `config.py` to match your microphone:

```python
SILENCE_THRESHOLD=0.006           # Lower = more sensitive, higher = needs louder speech
SILENCE_DURATION=1.5              # Seconds of quiet to trigger speech end
END_OF_SPEECH_SILENCE=1.2          # Pause time to finalize capture
MIN_SPEECH_SECONDS=0.7             # Minimum speech duration to avoid noise
MIC_CHUNK_SECONDS=0.12             # Audio chunk size (80ms at 16kHz)
```

### Session Timing

```python
AUTO_SLEEP_TIMEOUT=300             # 5 minutes: wake→active timeout
ACTIVE_LISTEN_SECONDS=6.5          # How long to listen per command
ACTIVE_RETRY_SECONDS=5.0           # Retry duration on no-speech
ORGANIZER_CONFIRM_TIMEOUT=60       # Confirmation window for file ops
```

### Model Selection

```python
# Speech-to-Text
WHISPER_MODEL=small                 # Options: tiny, base, small, medium, large
WHISPER_COMPUTE_TYPE=int8           # Options: float32, int8, int4
WHISPER_DEVICE=cpu                  # Options: cpu, cuda

# LLM Priority Chain (Google Gemini)
CLOUD_LLM_MODEL=gemini-1.5-flash    # Model API identifier (Google Gemini only)
GOOGLE_API_KEY=your_key             # 1st priority: Google Gemini (optional)

# LLM Fallback (Local)
OLLAMA_MODEL=gemma2:2b              # 2nd priority: Local Ollama (no API key needed)

# Vision
OLLAMA_VISION_MODEL=moondream       # For screenshot analysis
```

---

## 🧪 Testing

Run the included test suite to verify functionality:

```bash
# Phase 1: Core Pipeline (STT, wake word, intent routing)
python test_phase1.py

# Phase 2: Skills Integration
python test_phase2.py

# Phase 4: End-to-End System
python test_phase4.py

# Work Mode Workflow
python test_work_mode.py
```

---

## 📖 Key Concepts

### **Intent Routing Strategy**

DNA uses a two-tier routing system for optimal latency and accuracy:

1. **Fast Path (Regex)** — <10ms
   - Pre-compiled patterns for common commands
   - Examples: "open X", "set volume Y", "what time is it"
   - No LLM overhead, instant execution

2. **Smart Path (LLM)** — 100-500ms
   - Complex, ambiguous, or novel requests
   - Examples: "Can you help me organize my project files?", "Analyze this CSV for trends"
   - Generates structured JSON tool-call plans
   - Falls back to Ollama if no Google key

### **Context Resolution**

The assistant maintains session state to understand pronouns and context:

```
Command 1: "Open Chrome"
Command 2: "Close it"          # "it" → Chrome
Command 3: "What's the time"   # Remembers Chrome was last app
```

### **Confirmation Gates**

Dangerous operations require spoken confirmation within 30 seconds:

```
User: "Shutdown my computer"
DNA: "Are you sure? Just say 'confirm' or 'cancel'"
User: "Confirm"
DNA: Proceeds with shutdown
```

### **Morning Briefing**

On startup, DNA provides:
- Weather for configured city
- Recent news headlines
- Job postings matching your roles
- Personalized suggestion based on your command history

---

## 🔒 Safety Features

| Feature | Protections |
|---------|-------------|
| **Path Blocking** | Prevents access to `C:\Windows`, `AppData`, critical system dirs |
| **Confirmation Gates** | Requires spoken "confirm" for: shutdown, reboot, kill process, delete |
| **Sandboxed Execution** | Generated Python code runs in restricted namespace (no `os.system`, `eval`, etc.) |
| **Command Logging** | All commands and results stored locally for audit trail |
| **Auto-Sleep** | Disconnects after 5 minutes of inactivity (configurable) |
| **Noise Filtering** | Rejects very short transcripts to avoid accidental triggers |

---

## 🛠️ Development & Extension

### Adding a Custom Skill

Create a new file in `skills/`:

```python
# skills/my_skill.py
import logging

logger = logging.getLogger('dna.skill.my_skill')

def my_command(arg1: str, arg2: int = 10) -> str:
    """Docstring describes what the skill does."""
    logger.info('Running my_command with arg1=%s', arg1)
    result = f"Did something with {arg1} and {arg2}"
    return result
```

The skill is automatically discovered and registered. Call it naturally:

```
"Run my command with hello and 20"
```

### Modifying Intent Patterns

Edit `pipeline/intent_router.py` to add regex patterns for fast-path commands:

```python
SYSTEM_COMMAND_PATTERNS = [
    # Existing patterns...
    (re.compile(r"\bplay\s+(?:music|song|audio)\b", re.I), "play_audio"),
    (re.compile(r"\bstop\s+music\b", re.I), "stop_audio"),
]
```

### Tuning LLM Behavior

Add these to your `.env` file to control LLM response characteristics:

```env
# Adjust temperature for more/less creativity
OLLAMA_TEMPERATURE=0.2         # Lower = more focused, deterministic
                               # Higher = more creative, varied
```

Or modify directly in `pipeline/llm_agent.py` for code-level constants.

---

## 📊 Project Structure

```
DNA-Desktop-Assistant-/
├── dna_main.py                 # Entry point
├── config.py                   # Configuration & environment
├── requirements.txt            # Python dependencies
│
├── pipeline/                   # Audio & intent processing
│   ├── wake_word.py           # Wake word detection
│   ├── stt.py                 # Speech-to-text
│   ├── intent_router.py       # Command routing
│   ├── llm_agent.py           # LLM reasoning
│   ├── plan_executor.py       # Execute tool plans
│   ├── context_resolver.py    # Pronoun resolution
│   ├── session_manager.py     # State management
│   ├── tts.py                 # Text-to-speech
│   └── memory.py              # Conversation history
│
├── skills/                     # Modular tool library
│   ├── system_skill.py        # Apps, volume, brightness, media
│   ├── file_skill.py          # File operations
│   ├── data_skill.py          # Data analysis (CSV, queries)
│   ├── browser_skill.py       # Web search, URLs
│   ├── chat_skill.py          # Conversation
│   ├── vision_skill.py        # Screenshot analysis
│   ├── screen_skill.py        # Screenshots
│   ├── weather_skill.py       # Weather queries
│   ├── news_skill.py          # News aggregation
│   ├── job_search_skill.py    # Job listings
│   ├── organizer_skill.py     # File organization
│   ├── learning_skill.py      # Educational queries
│   └── web_skill.py           # HTTP requests, APIs
│
├── core/                       # Core logic
│   ├── session.py             # Session state
│   ├── personality.py         # Response generation
│   ├── skill_registry.py      # Skill discovery
│   ├── safety.py              # Safety enforcement
│   ├── window_monitor.py      # Context monitoring
│   ├── proactive.py           # Proactive alerts
│   └── morning_briefing.py    # Startup briefing
│
├── ui/                         # User interface
│   ├── window.py              # Desktop window
│   ├── tray.py                # System tray
│   └── toast.py               # Notifications
│
└── data/                       # Data & logs
    ├── dna_memory.db          # Conversation history (SQLite)
    ├── dna_duck.db            # Data queries (DuckDB)
    ├── organizer_undo.json    # File operation undo log
    ├── screenshots/           # Captured screenshots
    ├── models/piper/          # TTS voice models
    └── logs/dna.log           # Application logs
```

---

## 🐛 Troubleshooting

### Microphone Not Detected
```
Solution: Check Windows Audio settings → ensure microphone is default input
Restart DNA after changing audio settings
```

### Slow LLM Responses
```
Solution: Lower OLLAMA_TEMPERATURE for faster, more focused responses
         (e.g., 0.1 for focused mode, 0.2 for balanced)
         or use smaller model (gemma2:2b instead of larger variants)
         or switch to Google Gemini with GOOGLE_API_KEY
```

### STT Accuracy Issues
```
Solution: Increase SILENCE_THRESHOLD if environment is noisy
         Lower SILENCE_THRESHOLD if DNA cuts off speech early
         Use larger Whisper model (base or small instead of tiny)
```

### "DNA is online" but no response
```
Solution: 1. Check Ollama is running: ollama serve
         2. Check microphone permissions in Windows Settings
         3. View logs: Open file explorer, navigate to: data\logs\dna.log
            Or in command prompt: type data\logs\dna.log
```

### High CPU Usage
```
Solution: Use int8 quantization: WHISPER_COMPUTE_TYPE=int8
         Use smaller models: WHISPER_MODEL=tiny
         Reduce WINDOW_MONITOR_INTERVAL from 2 to 5 seconds
```

---

## 🤝 Contributing

We welcome contributions! Areas for enhancement:

- [ ] Additional skills (calendar, email, music streaming)
- [ ] Improved voice recognition accuracy
- [ ] Custom voice model training
- [ ] Multi-language support
- [ ] Mobile app integration
- [ ] CI/CD pipeline improvements

---

## 📝 License

This project is licensed under the MIT License — see LICENSE file for details.

---

## 🙏 Acknowledgments

- **OpenAI** — faster-whisper for efficient speech recognition
- **Ollama** — Easy local LLM deployment
- **Google** — Gemini API for advanced reasoning
- **Meta Llama Community** — Open-source language models
- **PySide6** — Qt bindings for Python UI

---

## 📞 Support

- 💬 **Issues & Bugs**: Open a GitHub issue
- 💡 **Feature Requests**: Discussions tab
- 📚 **Documentation**: See README sections above
- 🔧 **Debug Logs**: Check `logs/dna.log` for detailed execution trace

---

## 🌟 Show Your Support

If DNA helps you boost productivity, please consider:
- ⭐ Starring this repository
- 🐛 Reporting bugs
- 💡 Suggesting features
- 🔧 Contributing code

---

**Made with ❤️ for privacy-conscious developers and power users.**

**DNA: Your Desktop, Your Rules. 100% Offline. 100% Private.**
