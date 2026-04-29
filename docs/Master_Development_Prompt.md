# DNA — Master Development Prompt


> **How to use this:** Copy this entire page and paste it at the start of every AI coding session for DNA. Update the `[CURRENT PHASE]` and `[CURRENT TASK]` lines before pasting. Everything else stays fixed.
> 

---

## PROJECT OVERVIEW

```
Project   : DNA (Desktop Natural Assistant)
Type      : Hybrid local-first, privacy-first voice assistant
Platform  : Windows 11
Owner     : Jamiel J. — single user, personal tool
Hardware  : Intel i3-1134G4 (or N305 class), 8GB RAM, no GPU, Intel UHD 128MB
Repo      : github.com/JAMIEL-J/DNA-Voice-Assistant

Current Phase : Phase 17 — Suggestion Engine & Behavioral Intelligence Foundation
Current Task  : Scored startup suggestions, cooldown policy, usage backfill, workflow templates, and cross-session persistence are complete.
```

**What DNA does:**

| Phase | Description | Status |
| --- | --- | --- |
| 1 | STT + TTS pipeline end-to-end | [x] |

Listens for a wake word → transcribes your voice command → routes it through an intent system → executes a tool (open app, analyse data, control system, read screen, etc.) → speaks the result back.

**Two versions:**

- v1 (Basic): Single command → single tool → spoken result
- v2 (Powerful): Context-aware, multi-step plans, pluggable skills, learning system, proactive alerts

---

## TECH STACK

| Layer | Library / Tool | Version / Notes |
| --- | --- | --- |
| Wake Word | openwakeword | 0.6.0 — hey_jarvis built-in model |
| STT | faster-whisper | 1.0.x — tiny (v1), base (v2), compute_type='int8' |
| LLM | Gemma 4 E2B via Ollama (+ optional cloud fallback) | Local-first at localhost:11434; cloud used only when explicitly configured |
| TTS | piper-tts | en_US-lessac-medium.onnx |
| Automation | pyautogui + pygetwindow | 0.9.54 |
| Audio | sounddevice + pyaudio | Recording pipeline |
| Volume | pycaw | Windows audio control only |
| Data (small) | pandas + matplotlib | <100K rows only |
| Data (large) | duckdb | >100K rows, file-based: dna_duck.db |
| Memory | sqlite3 | Built-in, dna_memory.db |
| Vision | moondream via Ollama | v2 only, on-demand load |
| Tray UI | pystray + Pillow | Status icon only |
| Toast UI | plyer | Response notifications |
| Orchestration | asyncio + threading | No external frameworks |

**RAM Budget at Runtime:**

| Component | RAM |
| --- | --- |
| Windows 11 OS | ~2.0–2.5GB |
| Qwen3.5:2b (Ollama) | ~1.4GB (Q4K) |
| Whisper tiny/base | ~300–500MB |
| OpenWakeWord | ~50MB |
| pandas + DuckDB | ~200–500MB (data dependent) |
| Moondream (on-demand) | ~1.7GB — never load simultaneously with large pandas |
| Buffer | ~500MB |
| **Total** | **~5.0–6.0GB — within 8GB limit** |

---

## ARCHITECTURE

```
Microphone
  └─> OpenWakeWord (always-on, ~3% CPU)
        └─> faster-whisper (STT)
              └─> Context Resolver (v2: pronoun resolution from session state)
                    └─> Intent Router
                          ├─> [Simple] Regex match → Direct tool call (<10ms)
                          └─> [Complex] Hybrid LLM Router (local-first) → JSON plan → Plan Executor
                                                                      └─> Skill Tools
                                                                            ├─> system_skill
                                                                            ├─> file_skill
                                                                            ├─> data_skill (DuckDB / pandas)
                                                                            ├─> vision_skill (Moondream)
                                                                            ├─> browser_skill
                                                                            └─> core/safety.py (Safety Gate)
                                                                                  ├─> Protected path check
                                                                                  ├─> Dangerous tool → Confirmation flow
                                                                                  ├─> Blocked tool → Hard reject
                                                                                  └─> Command sanitisation
                                                                            └─> core/personality.py (Persona Hub)
                                                                                  ├─> Dynamic Greetings
                                                                                  └─> Local Humanizer (Zero Latency)
                                                                            └─> Piper TTS → Speaker
                                                                            └─> SQLite logger

[Background] ProactiveMonitor (daemon thread) → CPU / Download alerts
[Background] pystray icon → state color changes
```

**Key routing decisions:**

- Regex handles: volume, mute, media, open app, shutdown, screenshot, time
- LLM handles: everything else
- Dangerous tools (shutdown, restart, empty bin, lock): require spoken confirmation
- Blocked tools (format_disk, delete_system, rm_rf): always rejected
- DuckDB handles: any dataset >100K rows (never pandas for large files)
- NL2SQL for: query / filter / aggregate commands
- NL2Py for: transform / feature engineering / plot commands
- Thinking mode ON for: web summarisation, file comparison, ambiguous commands
- Thinking mode OFF for: everything else (90% of commands)

---

## FILE STRUCTURE

```
DNA-Assistant/
├── dna_main.py               # Entry point, main loop
├── config.py                 # ALL paths, model names, thresholds — no hardcoding elsewhere
├── pipeline/
│   ├── wake_word.py          # OpenWakeWord listener
│   ├── stt.py                # faster-whisper wrapper
│   ├── context_resolver.py   # Pronoun resolution (v2)
│   ├── intent_router.py      # Regex SIMPLE_INTENTS + LLM fallback
│   ├── llm_agent.py          # Ollama API, thinking mode router, JSON plan generation
│   ├── plan_executor.py      # Multi-step plan runner (v2)
│   ├── tts.py                # Piper TTS wrapper
│   └── memory.py             # SQLite read/write
├── skills/
│   ├── system_skill.py       # OS, volume, media, screenshot — exposes TOOLS dict
│   ├── file_skill.py         # File find, open, list, create — exposes TOOLS dict
│   ├── data_skill.py         # CSV/Excel, DuckDB, NL2SQL, NL2Py — exposes TOOLS dict
│   ├── vision_skill.py       # Moondream screen reading (v2) — exposes TOOLS dict
│   ├── browser_skill.py      # Web search, URL open (v2) — exposes TOOLS dict
│   └── learned/              # Approved skill snippets (v2)
├── core/
│   ├── session.py            # Session state: active_file, active_app, last_result, last_df
│   ├── safety.py             # Safety & security: path protection, command sanitisation, confirmation gates
│   ├── personality.py        # Aide Persona Hub, system prompt instructions, local humanizer
│   ├── skill_registry.py     # Auto-discovers all *_skill.py files, builds TOOL_MAP
│   └── proactive.py          # Daemon thread: CPU >90% alert, new download alert
├── ui/
│   ├── tray.py               # pystray icon, state color, right-click menu
│   └── toast.py              # plyer notification wrapper
├── data/
│   ├── dna_memory.db         # SQLite: conversation, command_log, preferences, aliases
│   └── dna_duck.db           # DuckDB persistent database
├── logs/
│   └── dna.log
└── requirements.txt
```

---

## STRICT CONSTRAINTS

> These are non-negotiable. Follow every one without exception.
> 

**1. HARDWARE FIRST**

Every solution must run on Intel i3 CPU, 8GB RAM, no GPU.

- Never suggest GPU-only libraries (torch with CUDA, tensorflow-gpu, etc.)
- Never suggest always-on models larger than 4B parameters
- Never load Moondream and large pandas DataFrames simultaneously
- Always check RAM implications before recommending a library

**2. NO FRAMEWORKS**

- No LangChain, LlamaIndex, Haystack, or similar agent frameworks
- No LangGraph, AutoGen, CrewAI, or orchestration libraries
- Use direct HTTP requests to Ollama API at [localhost:11434](http://localhost:11434)
- Use direct Python function calls for all tool execution

**3. HYBRID LOCAL-FIRST**

- Local inference is the default path for runtime commands.
- Cloud LLM fallback is allowed only when explicitly configured (API key present).
- No mandatory cloud dependency for core assistant operations.
- Sensitive/OS-destructive operations must still pass local safety gates before execution.

**4. WINDOWS 11 ONLY**

- Use `pathlib.Path` or `os.path.join` — never hardcoded forward slashes
- Use `pycaw` for audio — never `alsaaudio`, `pactl`, or Linux-only libs
- Use `subprocess` with Windows-correct commands
- Test all paths with `os.path.expanduser()` for `~` expansion

**5. DUCKDB FOR LARGE DATA**

- Any dataset with >100K rows uses DuckDB — no exceptions
- Never load large files fully into pandas
- Always check row count before deciding engine:

```python
count = duckdb.connect().execute(f"SELECT COUNT(*) FROM '{path}'").fetchone()[0]
engine = 'duckdb' if count > 100_000 else 'pandas'
```

- Schema + 3-row sample must be injected into every LLM data prompt

**6. NL2PY SAFETY**

- All generated Python code must be sandboxed before exec()
- Always check for blocked terms first:

```python
BLOCKED = ['os.', 'subprocess', 'open(', 'import', '__']
if any(b in code for b in BLOCKED):
    return 'Generated code looks unsafe, skipping.'
```

- Allowed exec namespace: `{'df': df, 'pd': pd, 'plt': plt, 'np': np}`
- Never allow file system writes from generated code except `plt.savefig()`

**7. ERROR HANDLING — MANDATORY**

- Every single tool function must have `try/except Exception as e`
- Always return a human-readable string on failure — never raise to main loop
- Always log every failure to SQLite `command_log` table
- Never let a tool crash DNA's main loop

**8. NO PLACEHOLDER CODE**

- Never write functions with `pass`, `# TODO`, or `raise NotImplementedError`
- Write complete, working implementations only
- If something can't be implemented yet, say so explicitly — don't stub it

**9. [CONFIG.PY](http://CONFIG.PY) IS THE SINGLE SOURCE OF TRUTH**

- All paths, model names, thresholds, search paths live in `config.py`
- No hardcoded values inside any skill file or pipeline file
- If a new constant is needed, add it to `config.py` first

**10. THREAD SAFETY**

- Proactive monitor and tray icon run as daemon threads
- All shared state access goes through `core/session.py`
- Use `threading.Lock()` for any shared state written from background threads

**11. SKILL MODULE CONTRACT**

- Every skill file must expose: `TOOLS = {'tool_name': function, ...}`
- Every tool function signature: `def tool_name(arg: str, ...) -> str`
- Every tool function has try/except, returns spoken-friendly string
- No skill file imports from another skill file — only from `core/` or stdlib

**12. THINKING MODE IS PER-TASK**

- Never set `think=True` globally
- Route thinking mode based on command type:

```python
THINKING_TASKS = ['summarise webpage', 'explain', 'compare', 'analyse']
def needs_thinking(command: str) -> bool:
    return any(w in command.lower() for w in THINKING_TASKS)
```

- Default: `think=False`. Thinking ON only for: web summarisation, file comparison, ambiguous commands, complex NL2Py transforms

**13. LEARNING SYSTEM SAFETY**

- Never auto-execute learned skill snippets
- Always confirm with the user before saving any new skill
- `approved` column in `learned_skills` must be 1 before any execution
- Preference and alias learning need no approval — they are non-executable

**14. PROCESS ISOLATION (APP LAUNCH)**

- All subprocess.Popen calls MUST use `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`
- All subprocess.run calls MUST use `creationflags=CREATE_NO_WINDOW` (0x08000000)
- Always set `start_new_session=True` and `close_fds=True` on Popen
- Redirect stdin/stdout/stderr to `subprocess.DEVNULL` for launched apps
- Always close gracefully first (`taskkill /T`), then force-kill as fallback
- Never use `rundll32.exe` for lock — use `ctypes.windll.user32.LockWorkStation()`

**15. SAFETY & CONFIRMATION FLOW**

- All tools in `core/safety.DANGEROUS_TOOLS` require spoken user confirmation before execution
- All tools in `core/safety.BLOCKED_TOOLS` must NEVER execute — reject immediately
- Confirmation window is 30 seconds — auto-cancels after timeout
- LLM system prompt must include explicit safety rules (no file deletion, no system modification)
- LLM-suggested tool names must be validated against the available tool list — reject hallucinated names
- All tool arguments must be scanned for dangerous shell patterns before execution
- Protected system paths (`C:\Windows`, `C:\Program Files`, `AppData`) must never be targets of file operations
- App names must be sanitised against shell injection characters (`& | ; > < ' " \`)

---

## CODE STYLE GUIDANCE

**Function pattern — every tool must follow this:**

```python
def tool_name(arg1: str, arg2: str = 'default') -> str:
    """One-line description of what this tool does."""
    try:
        # implementation
        return 'Spoken confirmation message.'
    except Exception as e:
        return f'Could not complete that: {str(e)}'
```

**Naming conventions:**

| Item | Convention | Example |
| --- | --- | --- |
| Skill files | snake_case + _[skill.py](http://skill.py) | data_[skill.py](http://skill.py) |
| Tool functions | snake_case verb_noun | summarize_csv, open_file |
| Config constants | UPPER_SNAKE_CASE | WHISPER_MODEL, DB_PATH |
| Session keys | lowercase string | 'active_file', 'last_df' |
| Pipeline files | snake_case, no suffix | intent_[router.py](http://router.py) |
| Thinking task list | UPPER_SNAKE_CASE list | THINKING_TASKS |

**LLM JSON parsing — always use this pattern:**

```python
try:
    result = json.loads(raw.strip())
except json.JSONDecodeError:
    result = {"plan": [{"tool": "unknown", "args": {}}]}  # safe fallback
```

**DuckDB query pattern:**

```python
def query_file(path: str, sql: str) -> pd.DataFrame:
    con = duckdb.connect(DUCKDB_PATH)
    safe_sql = sql.replace('{file}', f"'{path}'")
    return con.execute(safe_sql).fetchdf()
```

**Ollama API call pattern:**

```python
requests.post('http://localhost:11434/api/chat', json={
    'model': OLLAMA_MODEL,
    'messages': messages,
    'stream': False,
    'think': thinking,      # True or False per task
    'options': {
        'num_ctx': 4096 if thinking else 2048,
        'temperature': 0.1,
        'num_parallel': 1
    }
})
```

**Session state access pattern:**

```python
from core.session import update, get
update('active_file', path)   # write
current = get('active_file')  # read
```

**Import order (follow strictly):**

```python
# 1. stdlib
import os, json, re, threading
# 2. third-party
import duckdb, pandas as pd
# 3. internal — core first, then pipeline, then skills
from core.session import update, get
from config import DB_PATH, OLLAMA_MODEL
```

---

## OUTPUT FORMAT RULES

**All tool return strings are spoken by Piper TTS. Follow these rules:**

| Rule | Bad | Good |
| --- | --- | --- |
| Complete sentences | 'vol=60' | 'Volume set to 60.' |
| No symbols | '$5.2L revenue' | '5 point 2 lakhs revenue' |
| No full paths | 'C:UsersJamielsales.xlsx' | 'sales dot xlsx from your Desktop' |
| No raw errors | 'FileNotFoundError: [Errno 2]' | 'Could not find that file. Try the exact filename.' |
| Max 3 sentences for simple | 5 sentences for 'volume set' | 1 sentence |
| Max 5 sentences for complex | 10 sentence analysis | 3–5 sentence summary |

**LLM output formats:**

v1 single tool:

```json
{"tool": "summarize_csv", "args": {"path": "sales_q1.xlsx"}}
```

v2 multi-step plan:

```json
{
  "plan": [
    {"tool": "find_file", "args": {"name": "sales_feb"}, "use_prev_result": false},
    {"tool": "compare_files", "args": {}, "use_prev_result": true}
  ]
}
```

Clarification request:

```json
{"tool": "clarify", "args": {"question": "Which file should I analyse?"}}
```

NL2SQL output (plain SQL, no markdown, no backticks):

```sql
SELECT product, SUM(revenue) FROM 'C:/path/to/file.csv'
GROUP BY product ORDER BY SUM(revenue) DESC LIMIT 10
```

NL2Py output (plain Python, no markdown, no backticks, result in `result` var):

```python
result_df = df.groupby('product')['revenue'].sum().sort_values(ascending=False).head(10)
result = f'Top 10 products: {result_df.to_dict()}'
```

---

## SESSION TEMPLATES

### Starting any coding session

```
We are building DNA (Desktop Natural Assistant).
[Paste this entire master prompt above this line]

Current phase  : Phase N — [brief description]
Current task   : [one sentence — what specifically are you building right now]
Files to touch : [list the files you expect to edit]
```

### Debugging an existing component

```
DNA component     : [e.g. pipeline/llm_agent.py]
Expected behaviour: [what should happen]
Actual behaviour  : [what is happening]
Error message     : [paste full traceback]
Relevant code     : [paste the function]

Fix this without changing the overall architecture.
No LangChain. Windows 11 only. Return complete working code.
```

### Adding a new skill module

```
Add a new skill to DNA: [skill_name]_skill.py

What it does  : [description]
Tools to expose: [list of tool_name: description]
Libraries     : [list pip packages]
Windows compat: yes
Cloud calls   : none

Follow the TOOLS dict pattern.
Every function returns a spoken-friendly string.
Every function has try/except.
All paths come from config.py — no hardcoding.
```

### Adding a new simple intent (regex route)

```
Add a new simple intent to pipeline/intent_router.py.

Trigger phrase pattern: [regex pattern]
Tool to call          : [tool function]
Args                  : [what to extract from the match]
Expected return string: [example of what DNA should say]

Do not use LLM for this — add it to SIMPLE_INTENTS dict.
```

### Adding learning capability

```
Add learning to DNA for: [preference / alias / skill snippet]

Detection signals : [list of trigger phrases]
Storage table     : [SQLite table name]
Approval required : [yes — skill snippets only / no — prefs and aliases]
Pattern to follow : existing learning system in core/session.py

Never auto-execute. Always confirm with user before saving a skill snippet.
```

---

## BUILD PHASE TRACKER

| Phase | Goal | Status |
| --- | --- | --- |
| 1 | STT + TTS pipeline end-to-end | [x] |
| 2 | Wake word + system commands (open/volume/media) | [x] |
| 3 | Intent router — all simple commands without LLM | [x] |
| 4 | LLM agent — complex file and DA commands | [x] |
| 5 | SQLite memory + command logging | [x] |
| 6 | Session state + pronoun resolution (v2) | [x] |
| 7 | Plan executor — multi-step commands (v2) | [x] |
| 8 | Skill registry — auto-discovery (v2) | [x] |
| 9 | DuckDB + NL2SQL / NL2Py data router (v2) | [x] |
| 10 | Vision skill — Moondream (v2) | [x] |
| 11 | Proactive monitor — CPU / download alerts (v2) | [x] |
| 12 | Learning system — preferences + aliases (v2) | [x] |
| 13 | Tray icon + toast notifications (UI) | [x] |
| 14 | Stability, edge cases, error hardening | [x] |
| 15 | Personality & Humanization | [x] |
| 16 | Context + Workflow + Deep OS Expansion | [x] |
| 17 | Suggestion Engine + Usage Intelligence Foundation | [x] |

> Update [ ] to [x] as phases complete. Update `Current Phase` at the top of this prompt before each session.

## PHASE 4 COMPLETION NOTES (2026-03-29)

- Added `pipeline/llm_agent.py` for Ollama fallback routing.
- Added per-task thinking mode router (`needs_thinking`) with default `think=False`.
- Added JSON cleaning/parsing fallback for markdown-wrapped LLM output.
- Wired `pipeline/intent_router.py` fallback path for non-regex commands.
- Added `allow_llm` switch in `route()` so regex tests can run deterministically.
- Added Ollama tuning constants in `config.py` (`OLLAMA_TIMEOUT`, `OLLAMA_CTX_NORMAL`, `OLLAMA_CTX_THINKING`, `OLLAMA_TEMPERATURE`).
- Updated `.env.example` for the new Ollama settings.
- Regression tested routing: `test_phase2.py` passed (23 out of 23).

## CRASH FIX & SAFETY HARDENING (2026-04-05)

### UI Crash Fix (Black Screen on App Close)
- **Root cause**: Child processes inherited DNA's console window via `subprocess.Popen` without creation flags. When UWP/shell apps closed, the shared window handle was destroyed, causing a black screen artifact.
- **Fix**: All `Popen` calls now use `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` with `start_new_session=True`. All `subprocess.run` calls use `CREATE_NO_WINDOW`.
- Graceful close chain: `taskkill /T` (WM_CLOSE) → wait 1s → `taskkill /F /T` (force) fallback.
- Lock screen changed from `rundll32.exe` to `ctypes.windll.user32.LockWorkStation()`.

### Safety Module (`core/safety.py` — NEW)
- Two-tier path protection: TREE_PROTECTED (entire directory tree blocked) and EXACT_PROTECTED (only exact path blocked).
- Dangerous tool confirmation flow (30s timeout): shutdown, restart, empty recycle bin, lock screen.
- Blocked tools (never execute): format_disk, delete_system, rm_rf, wipe.
- Dangerous shell command pattern detection (format, rd /s, diskpart, reg delete, etc.).
- App name sanitisation against shell injection characters.

### LLM Safety Hardening (`pipeline/llm_agent.py`)
- Safety rules injected into system prompt (never delete files, never guess destructive actions).
- Tool name validation against available tool list — hallucinated names are rejected.
- Pre-execution safety gate (`_validate_tool_safety`) on every tool invocation.
- Multi-step plans are fully pre-validated before any step executes.

### Intent Router Confirmation Flow (`pipeline/intent_router.py`)
- Dangerous tools trigger a spoken warning and await confirmation.
- Confirmation expires after 30 seconds or on unrelated command.
- Cancel phrases supported: cancel, no, stop, abort, never mind, forget it.

### File Skill Hardening (`skills/file_skill.py`)
- `_resolve_folder()` validates paths against `is_path_protected()` before and after resolution.
- Blocks LLM-directed browsing of `C:\Windows`, `C:\Program Files`, `AppData`.

## PHASE 5 COMPLETION NOTES (2026-04-05)

- Implemented `pipeline/memory.py` encapsulating SQLite operations.
- Created `init_db()` and tables for `conversation`, `command_log`, `preferences`, and `aliases`.
- Hooked up `log_command(command, result, status)` inside `dna_main.py` main loop.
- Automatically handles success/error distinction to populate DB log correctly.

## PHASE 6 COMPLETION NOTES (2026-04-07)

- Added `pipeline/context_resolver.py` to resolve pronouns (it, this, that) within user commands using session state.
- Hooked `resolve_pronouns()` into `pipeline/intent_router.py` before matching simple regex intents or falling back to the LLM.
- Hooked `core.session.update('active_app', name)` inside `skills/system_skill.py` to keep track of active applications.
- Hooked `core.session.update('active_file', name)` inside `skills/file_skill.py` to log folders and files the user opens or queries.

## PHASE 7 COMPLETION NOTES (2026-04-07)

- Created `pipeline/plan_executor.py` explicitly for executing multi-step LLM JSON plans.
- Moved `_validate_tool_safety`, `_invoke_tool`, and `_execute_plan` heavily into `plan_executor.py`.
- Plumbed `execute_plan` and `invoke_tool` directly into `handle_complex_command` in `pipeline/llm_agent.py`.

## PHASE 8 COMPLETION NOTES (2026-04-07)

- Added `core/skill_registry.py` to dynamically discover and aggregate `TOOLS` from all files matching `*_skill.py` across the `/skills` directory.
- Hooked `discover_skills()` natively into the startup sequence of `dna_main.py` so tool sets are resolved immediately.
- Erased hardcoded imports inside `pipeline/intent_router.py` and connected it gracefully to `get_tool_map()`.
- Refactored stateless utility functions (`_volume_up`, `_volume_down`, `_brightness_up`, `_brightness_down`) structurally from the intent router into `skills/system_skill.py` extending its export to truly house all low-level Windows functions.

## PHASE 9 COMPLETION NOTES (2026-04-07)

- Contributed `skills/data_skill.py` carrying the `analyze_data` capability.
- Programmed an intelligent logic router mapping queries against >100K CSV rows toward `_duckdb_analysis`, maintaining `<100K` datasets gracefully within `_pandas_analysis`.
- Added tight NLP schema injection pipelines for Ollama to construct valid Python / SQL queries automatically.
- Integrated safety checks into `NL2Py` limiting `exec()` behavior entirely and blacklisting operations such as file-reads and subprocess spawns.

## PHASE 10 COMPLETION NOTES (2026-04-07)

- Crafted `skills/vision_skill.py` establishing `read_screen` to capture and relay screen understanding visually through Ollama.
- Introduced configuration parameter `OLLAMA_VISION_MODEL` (defaulting to `moondream`) inside `config.py`.
- Utilized base64 encoded streams across local REST requests directly to localhost instead of CLI interfaces to safely encapsulate requests safely.

## PHASE 11 COMPLETION NOTES (2026-04-07)

- Crafted `core/proactive.py` equipped with separated daemon threads for CPU monitoring and Downloads folder monitoring respectively.
- Interrogates SQLite and current context `get('is_listening')` dynamically prior to interacting over TTS effectively preserving the conversation's state.
- Cooldown thresholds incorporated efficiently: limits CPU repetition to 5-minute spans and downloads effectively mapped dynamically.
- `start_proactive_monitors` is formally wired within `dna_main`'s init sequence.

## PHASE 12 COMPLETION NOTES (2026-04-07)

- Crafted `pipeline/memory.py` wrappers targeting the `preferences` and `aliases` SQLite tables natively.
- Developed `skills/learning_skill.py` unlocking explicit preferences teaching allowing the user to dictate settings organically.
- Seamlessly plumbed `get_aliases()` lookups globally into `_resolve_folder` and `open_app`/`close_app` workflows.
- Injected `get_preferences()` natively within `_build_system_prompt` informing Ollama proactively of any established parameters unconditionally!

## PHASE 13 COMPLETION NOTES (2026-04-07)

- Crafted `ui/toast.py` wrapping the `plyer` library to invoke standard Windows 11 system notifications gracefully.
- Added `ui/tray.py` operating under a daemon polling routine through `pystray`. Safely wired instances back into `dna_main.py` and `core/proactive.py`.
- Established a visual cue (`green` / `gray` mapping) communicating dynamic microphone listening states silently mapping back from `core/session.py`.

## PHASE 14 COMPLETION NOTES (2026-04-07)

- Injected a stateful `is_running` lifecycle flag across the `core/session.py` architecture.
- Seamlessly threaded `ui/tray.py`'s context Exit hook into the global ecosystem allowing DNA to collapse itself elegantly dynamically.
- `wait_for_wake_word` natively checks the boolean status flag to stop cleanly returning rather than forcefully terminating over blocking event polls.
- Caught gracefully all `KeyboardInterrupt` loops to permit organic console-level Ctrl+C shutdowns seamlessly syncing to the UI instance safely breaking all daemon threads passively. All tasks achieved perfectly.

## PHASE 15 COMPLETION NOTES (2026-04-10)

- Developed `core/personality.py` implementing the **Loyal Digital Aide** (butler) persona.
- Centralized the LLM system prompt in `personality.py`, transitioning DNA from a casual friend to a respectful, subservient assistant.
- Engineered a **Hybrid Humanizer**:
    - **LLM Branch**: Persona results naturally generated via system instruction.
    - **Fast-Path Branch**: Regex tool results are wrapped in dynamic prefixes (As you wish sir, etc.) locally within `personality.py` to ensure zero response lag.
- Refined TTS flow by optimizing punctuation and using commas to create natural rhythmic speech instead of robotic pauses.
- Integrated `get_wake_greeting()` into `dna_main.py` for dynamic, time-aware activation responses.

## PHASE 16 COMPLETION NOTES (2026-04-13)

- Added workflow templates in `config.py` (`work mode`, `focus mode`, `end work`) and direct workflow routing in `pipeline/intent_router.py`.
- Added cross-session context persistence (`session_state`) with startup restore and shutdown save.
- Added usage pattern table and logging foundation in `pipeline/memory.py`.
- Expanded `skills/system_skill.py` with `list_heavy_processes`, `kill_process`, and `get_system_health`.
- Added dangerous-tool coverage for `kill_process` with confirmation warnings in `core/safety.py`.

## PHASE 17 COMPLETION NOTES (2026-04-13)

- Added suggestion policy config controls (enable switches, min confidence, min evidence count, cooldown minutes).
- Implemented scored startup suggestions using usage data confidence and top-result margin.
- Added cooldown persistence to prevent repetitive startup prompts.
- Added incremental historical backfill from `command_log` into `usage_patterns` for faster usefulness on existing deployments.
- Implemented sparse-data fallback (same hour across weekdays) for low-data startup recommendation resilience.
