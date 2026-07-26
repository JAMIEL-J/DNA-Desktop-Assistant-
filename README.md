# 🧬 DNA (Desktop Natural Assistant)

**DNA** is a professional-grade, privacy-first, fully offline voice assistant designed for Windows. It transforms the desktop experience by combining low-latency voice orchestration with deep OS integration and high-performance local data analysis.

Unlike cloud-based assistants, DNA operates entirely on your hardware, ensuring that your voice, files, and data never leave your machine.

---

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Windows Only](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status: Active Development](https://img.shields.io/badge/status-Active%20Development-brightgreen.svg)]()
[![Ollama](https://img.shields.io/badge/LLM-Ollama-black?logo=ollama)](https://ollama.ai)
[![DuckDB](https://img.shields.io/badge/Data-DuckDB-yellow?logo=duckdb)](https://duckdb.org/)
[![PySide6](https://img.shields.io/badge/UI-PySide6-brightgreen?logo=qt)](https://doc.qt.io/qtforpython/)
[![Faster-Whisper](https://img.shields.io/badge/STT-Faster--Whisper-orange)](https://github.com/SYSTRAN/faster-whisper)

---

<details>
<summary><b>View Application Interfaces</b></summary>

### The Orb Interface
[Insert Orb Interface Screenshot Here]

### System Tray Status
[Insert System Tray Icon Screenshot Here]

</details>

---

## 🚀 Core Capabilities

<details open>
<summary><b>🎙️ Voice Orchestration & Processing</b></summary>

- **Wake Word Detection:** Always-on listening using OpenWakeWord for zero-latency activation.
- **Robust Transcription:** Powered by Faster-Whisper, featuring fast and smart dual-path decoding with support for partial phrases and dynamic continuation capture.
- **Local Text-to-Speech:** Generates fluid natural voice output via Piper-TTS running on ONNX Runtime.

</details>

<details open>
<summary><b>🖥️ System & Desktop Control</b></summary>

- **Application Management:** Launch and close common applications intelligently.
- **Resource Monitoring:** Background process monitoring using `psutil`, capable of identifying resource-heavy tasks.
- **Volume & Screen Control:** Automated volume adjustment using Windows COM and screen tracking/screenshots using `pyautogui`.
- **System Tray Presence:** Lightweight system tray visualizer to indicate listening state using `pystray`.

</details>

<details open>
<summary><b>📊 Data Analytics & Data Engineering</b></summary>

- **High-Speed SQL:** Leverages DuckDB for querying massive datasets entirely locally.
- **Pandas Sandbox:** Uses sandboxed Pandas execution for ad-hoc aggregations and CSV-based data science workflows.

</details>

<details open>
<summary><b>🧠 Advanced Intelligence & Workflows</b></summary>

- **LLM Reasoning:** Integrates with local Ollama models for processing ambiguous language and complex planning.
- **Memory & Graph Engine:** Maintains persistent SQLite conversation memory and graph sync using `GraphProcessor`.
- **Proactive Context Awareness:** Background window monitoring (`WindowMonitor`) that provides contextual information to the AI engine without prompt engineering.
- **Morning Briefing:** Startup sequence aggregating weather, news, job search results, and personalized system status.
- **Specialized Skills:** Over a dozen pluggable modules handling weather, job searches, news, learning queries, career operations, and file organization.

</details>

---

## 🛠️ System Architecture

### The Pipeline Flow

DNA utilizes a sophisticated linear-to-agentic pipeline:
`Wake Word` $\rightarrow$ `STT` $\rightarrow$ `Context Resolver` $\rightarrow$ `Intent Router` $\rightarrow$ `LLM Agent` $\rightarrow$ `Plan Executor` $\rightarrow$ `Skill Registry` $\rightarrow$ `TTS`

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

### Hybrid Routing Strategy
To maximize responsiveness, DNA uses a two-tier routing system:
1. **Fast Path (Regex)**: Common commands (volume, time, etc.) are matched against high-speed regex patterns and executed in $<10\text{ms}$.
2. **Agent Path (LLM)**: Complex or ambiguous requests are routed to a local LLM (Gemma/Qwen via Ollama) which generates a structured tool-call plan.

### Safety-First Design
Security is baked into the core:
- **Confirmation Gates**: "Dangerous" tools (shutdown, lock, kill process) require a spoken confirmation.
- **Path Protection**: Critical system directories (`C:\Windows`, `AppData`) are strictly blocked from file operations.
- **Sandbox Execution**: All generated Python code for data analysis is run in a restricted namespace to prevent system modification.

---

## 💻 Technical Stack

DNA's architecture emphasizes local processing, combining low-latency components to act as an offline proxy between user intention and system execution.

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Intelligence** | `Ollama` (Local), `google-genai` | Multi-tier command routing and natural language planning. |
| **Speech-To-Text** | `faster-whisper` (Int8 CPU) | Fast, local speech decoding and phrase boundary capture. |
| **Text-To-Speech** | `piper-tts`, `onnxruntime` | Low-latency response generation. |
| **Wake Word** | `openwakeword` | Microphone stream trigger mechanism. |
| **Data Engine** | `duckdb`, `pandas` | Intelligent data querying and memory-efficient aggregations. |
| **System Automation**| `pyautogui`, `psutil`, `pycaw` | Direct process, resource, and IO control. |
| **User Interface** | `PySide6`, `WebSockets` | Real-time frontend visualization via Qt WebEngine. |
| **State Storage** | `SQLite` | Immutable context session logs and knowledge graphs. |


### Hardware Optimization (8GB RAM Budget)
DNA is engineered to run on modest hardware (e.g., Intel i3, 8GB RAM):
- **Quantization**: Uses 4-bit quantized models to minimize VRAM/RAM footprint.
- **Demand Loading**: Vision models are loaded only when screen-reading is requested.
- **Virtual Memory Strategy**: Synchronized with a 12GB SSD Page File to ensure absolute stability during spikes.

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

### Command Quick-Reference Table

| User Says | DNA Action | Pipeline Path |
| :--- | :--- | :--- |
| *"Hey DNA, set volume to 40"* | Sets system volume to 40% | Regex $\rightarrow$ System Skill |
| *"Open my sales report"* | Finds `sales_report.csv` $\rightarrow$ Opens in Excel | LLM $\rightarrow$ File Skill |
| *"Analyze the churn data and plot a bar chart"* | DuckDB Query $\rightarrow$ Pandas Plot $\rightarrow$ PNG | LLM $\rightarrow$ Plan $\rightarrow$ Data Skill |
| *"What error is showing on my screen?"* | Screenshot $\rightarrow$ Moondream $\rightarrow$ Spoken Description | LLM $\rightarrow$ Vision Skill |
| *"Work mode"* | Launches VS Code, Browser, and opens project folder | Router $\rightarrow$ Workflow Plan |

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

# LLM Priority Chain (Gemini)
CLOUD_LLM_MODEL=gemini-1.5-flash    # Gemini 1.5 Flash API model (not used with Ollama)
GOOGLE_API_KEY=your_key             # 1st priority: Gemini 1.5 Flash (optional)

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
OLLAMA_TEMPERATURE=0.2         # Lower = more focused, deterministic (0.0-1.0)
                               # Default: 0.2 (supported as environment variable)
```

This environment variable is loaded from `config.py` and controls Ollama model behavior.

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
         or switch to Gemini 1.5 Flash with GOOGLE_API_KEY
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
         3. View logs: 
            - Open Command Prompt in project directory (Shift+Right-click > Open PowerShell)
            - Run: type data\logs\dna.log
            - Or simply open file manager and navigate to: data\logs\dna.log
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
