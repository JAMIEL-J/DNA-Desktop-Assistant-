# System Design Document
**Version:** 1.0 | **Date:** March 2026 | **Author:** Jamiel J.

---

## 1. System Overview

DNA is a multi-component local voice assistant. Each component runs as a Python module. Communication is synchronous in v1 (function calls), with a background daemon thread for proactive monitoring in v2. No network calls at runtime.

---

## 2. High-Level Architecture

### v1 Pipeline (Basic)

Linear pipeline. One tool per command.

| Stage | Component | Library | Output |
| --- | --- | --- | --- |
| 1 | Microphone input | sounddevice | Raw audio float32 array |
| 2 | Wake word detection | openwakeword | Boolean trigger |
| 3 | Speech-to-Text | faster-whisper (tiny) | Command string |
| 4 | Intent routing | regex + Phi-3-mini | Tool name + args JSON |
| 5 | Tool execution | os / pyautogui / pandas / DuckDB | Result string |
| 6 | Text-to-Speech | Piper TTS | Audio to speaker |
| 7 | Logging | SQLite | Persisted command record |

### v2 Pipeline (Powerful)

Context-aware, multi-step, plan-based execution.

| Stage | Component | Addition vs v1 |
| --- | --- | --- |
| 1–2 | Microphone + Wake word | Same |
| 3 | STT | Upgrade to Whisper base |
| 4 | Context resolver | NEW: resolves pronouns from session state |
| 5 | Intent routing | Extended patterns |
| 6 | LLM plan generation | Returns JSON plan array, not single tool |
| 7 | Plan executor | NEW: loops through multi-step plan |
| 8 | Skill registry | NEW: auto-discovers skill modules |
| 9 | Tool execution | Extended with DuckDB, vision, browser |
| 10 | TTS | Same |
| 11 | SQLite v2 | Extended schema |
| 12 | Proactive monitor | NEW: daemon thread |

---

## 3. Component Design

### 3.1 Wake Word — OpenWakeWord

- Model: hey_jarvis (built-in, no training needed to start)
- CPU usage: ~3% continuous
- False positive rate: <1/hour at threshold 0.5
- Custom 'Hey DNA' can be trained after core pipeline works

### 3.2 STT — faster-whisper

| Model | RAM | Latency | Accuracy | Use When |
| --- | --- | --- | --- | --- |
| tiny | ~300MB | 1–2s | ~85% | v1 default |
| base | ~500MB | 2–3s | ~90% | v2 upgrade |
| small | ~1GB | 4–6s | ~93% | Only if base is insufficient |

Always use `compute_type='int8'` on CPU. Reduces memory ~40%.

### 3.3 LLM — Qwen3.5:2b via Ollama

- Model: qwen3.5:2b (~1.4GB Q4K / ~2.7GB Q8)
- Inference: 2–5 seconds per call on i3-1134G4
- API: HTTP POST to [localhost:11434/api/chat](http://localhost:11434/api/chat)
- Native tool calling support built-in
- v1 output: single JSON tool call
- v2 output: JSON plan array
- System prompt always includes available tools + schema for data commands
- Last 6 conversation turns sent as context

**Thinking Mode — Per-Task Routing:**

Thinking mode is NOT a global on/off. It is routed per task type:

| Task | Thinking | Reason |
| --- | --- | --- |
| Tool call routing (open Chrome, volume) | OFF | Need fast JSON, not reasoning |
| NL2SQL generation | OFF | Short structured output |
| NL2Py simple transforms | OFF | Fast enough without thinking |
| NL2Py complex transforms | OPTIONAL | Slightly better code quality |
| Dataset analysis / summarisation | OFF | DuckDB runs the query, not LLM |
| Web page summarisation / exploration | ON | Multi-step reasoning over unstructured content |
| Comparing two files logically | ON | Needs reasoning, not pattern matching |
| Ambiguous or unclear commands | ON | Better intent resolution |

Implementation in llm_[agent.py](http://agent.py):

```python
THINKING_TASKS = ['summarise webpage', 'explain', 'compare', 'analyse']

def needs_thinking(command: str) -> bool:
    return any(w in command.lower() for w in THINKING_TASKS)

def ask_llm(command, history, thinking=False):
    response = requests.post('http://localhost:11434/api/chat', json={
        'model': 'qwen3.5:2b',
        'messages': [...],
        'stream': False,
        'think': thinking,
        'options': {
            'num_ctx': 4096 if thinking else 2048,
            'temperature': 0.1
        }
    })
```

Default: thinking=False. 90% of DNA commands never need thinking mode.

### 3.4 Intent Router

Two-stage routing to minimise LLM calls:

1. Regex match against SIMPLE_INTENTS — executes in <10ms
2. LLM fallback for complex or ambiguous commands

### 3.5 Data Execution Router

| Command Intent | Route | Engine | Why |
| --- | --- | --- | --- |
| Query / filter / aggregate | NL2SQL | DuckDB | Deterministic, handles 2M+ rows |
| Transform / feature engineering | NL2Py | pandas (sandboxed) | Flexible, handles complex logic |
| Plot / visualise | NL2Py | matplotlib | SQL can't generate charts |
| File >100K rows (any intent) | NL2SQL | DuckDB | pandas would OOM on 8GB |
| Unknown intent (default) | NL2SQL | DuckDB | Safer default |

### 3.6 DuckDB Integration

- File-based persistence: dna_duck.db
- Direct file querying: `SELECT * FROM 'path/to/file.csv'` — no import needed
- Row count check before deciding engine (100K threshold)
- Schema extraction injected into LLM prompt
- 3-row sample always included for column name accuracy

### 3.7 NL2Py Sandboxing

Generated code executes via exec() with restricted builtins.

```
BLOCKED = ['os.', 'subprocess', 'open(', 'import', '__']
Allowed namespace: df, pd, plt, np only
```

### 3.8 TTS — Piper

- Voice: en_US-lessac-medium
- Latency: 0.5–1s
- Fully offline ONNX model
- Output: WAV played via Windows PowerShell

### 3.9 Learning System (v2)

| Level | Storage | Reliability |
| --- | --- | --- |
| Preference learning | user_preferences SQLite table | 100% |
| Alias learning | aliases SQLite table | 100% |
| Skill snippet learning | learned_skills table + human review gate | ~70% |

---

## 4. Database Design

### SQLite Schema

```sql
-- Conversation context
CREATE TABLE conversation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    role TEXT,
    content TEXT
);

-- Command audit trail
CREATE TABLE command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    raw_command TEXT,
    tool_used TEXT,
    args TEXT,
    success INTEGER,
    error_msg TEXT
);

-- Learned preferences
CREATE TABLE user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT,
    learned_at TEXT,
    times_used INTEGER
);

-- Learned aliases
CREATE TABLE aliases (
    trigger TEXT PRIMARY KEY,
    resolved TEXT,
    tool_hint TEXT,
    created_at TEXT
);

-- Skill snippets (require approval)
CREATE TABLE learned_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger TEXT,
    description TEXT,
    code TEXT,
    approved INTEGER,  -- 0=pending, 1=approved, 2=rejected
    created_at TEXT,
    times_used INTEGER
);
```

---

## 5. RAM Budget

| Component | RAM | Notes |
| --- | --- | --- |
| Windows 11 OS | ~2.0–2.5GB | Always on |
| Phi-3-mini (Ollama) | ~2.3GB | Loaded once |
| Whisper tiny | ~300MB | Loaded once |
| Moondream (v2 vision) | ~1.7GB | Load on demand only |
| OpenWakeWord | ~50MB | Negligible |
| pandas + DuckDB | ~200–500MB | Data dependent |
| Buffer | ~500MB | For spikes |
| **TOTAL** | **~5.5–6.5GB** | **Within 8GB (no Moondream + large pandas simultaneously)** |

---

## 6. File Structure

```
DNA-Assistant/
├── dna_main.py
├── config.py
├── pipeline/
│   ├── wake_word.py
│   ├── stt.py
│   ├── context_resolver.py   (v2)
│   ├── intent_router.py
│   ├── llm_agent.py
│   ├── plan_executor.py      (v2)
│   ├── tts.py
│   └── memory.py
├── skills/
│   ├── system_skill.py
│   ├── file_skill.py
│   ├── data_skill.py
│   ├── vision_skill.py       (v2)
│   ├── browser_skill.py      (v2)
│   └── learned/              (v2 - approved snippets)
├── core/
│   ├── session.py            (v2)
│   ├── skill_registry.py     (v2)
│   └── proactive.py          (v2)
├── data/
│   ├── dna_memory.db
│   └── dna_duck.db
└── requirements.txt
```

---

## 7. Error Handling Strategy

| Failure Type | Handling |
| --- | --- |
| Wake word missed | Silent — user repeats naturally |
| STT returns empty | DNA stays silent, listens again |
| LLM invalid JSON | Fallback: 'I couldn’t understand that' |
| Tool execution exception | Catch, log to command_log, speak error |
| Plan step fails mid-execution | Stop plan, report partial results + failure |
| DuckDB query error | Catch SQL error, speak it, suggest rephrasing |
| NL2Py unsafe code detected | Reject, speak 'Generated code looks unsafe' |
| Moondream timeout | Fallback: 'Screen reading timed out' |
| Skill snippet not approved | Speak 'This skill needs your approval first' |