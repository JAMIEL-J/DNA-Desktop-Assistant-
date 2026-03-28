# 📜 Master Prompt Document
# Master Prompt Document

**Version:** 1.0 | **Date:** March 2026 | **Author:** Jamiel J.

> Copy Section 1 + 2 at the start of every AI coding session for DNA.
> 

---

## 1. Project Overview Block

```jsx
PROJECT: DNA (Desktop Natural Assistant)
TYPE: Fully offline, privacy-first voice assistant for Windows
OWNER: Jamiel J. — personal tool, single user
HARDWARE: Intel i3-1134G4, 8GB RAM, no GPU, Windows 11

CORE PIPELINE:
  Microphone -> OpenWakeWord -> faster-whisper -> Intent Router
  -> [Phi-3-mini via Ollama] -> Plan Executor -> Skill Tools -> Piper TTS

KEY ARCHITECTURE DECISIONS:
  - No LangChain. Direct Ollama API calls only.
  - LLM used only for complex/ambiguous commands. Regex handles simple ones.
  - DuckDB for all datasets >100K rows. pandas for small files only.
  - NL2SQL for query/filter/aggregate. NL2Py for transform/plot.
  - Skill modules in /skills/ auto-discovered by core/skill_registry.py
  - Session state in core/session.py resolves pronouns before LLM call.
  - Multi-step plans: LLM returns JSON array, plan_executor loops through.
  - Learning: preferences + aliases saved to SQLite. Skill snippets need approval.
  - Thinking mode: OFF by default. ON only for web summarisation, file comparison,
    complex NL2Py transforms, and ambiguous commands. Routed via needs_thinking().

MODELS IN USE:
  STT: faster-whisper tiny (v1) / base (v2)
  LLM: qwen3.5:2b via Ollama (localhost:11434)
       Thinking mode: OFF by default, ON for web summarisation / file comparison / ambiguous commands
  TTS: Piper en_US-lessac-medium
  Vision: moondream via Ollama (v2, on-demand only)

CURRENT BUILD PHASE: [UPDATE THIS LINE EACH SESSION]
```

---

## 2. Strict Instructions Block

```
STRICT RULES — follow all without exception:

1. HARDWARE FIRST: Every solution must run on i3 CPU, 8GB RAM, no GPU.
   Never suggest GPU-only libraries (torch cuda, tensorflow-gpu etc.)
   Never suggest models >4B parameters for always-on use.
   Never load multiple large models simultaneously.

2. NO LANGCHAIN: Do not use LangChain, LlamaIndex, or similar frameworks.
   Use direct requests to Ollama API (localhost:11434).
   Use direct function calls for tool execution.

3. OFFLINE ONLY: No cloud API calls at runtime.
   No OpenAI, Anthropic, Groq, HuggingFace inference API.
   All models run locally via Ollama or faster-whisper.

4. WINDOWS COMPATIBLE: All code must work on Windows 11.
   Use os.path.join, pathlib.Path, not hardcoded forward slashes.
   pycaw for audio control (not alsaaudio or pactl).

5. DUCKDB FOR LARGE DATA: Any dataset >100K rows uses DuckDB.
   Never load large files fully into pandas.
   Always check row count before deciding engine.

6. NL2PY SAFETY: Generated Python code must be sandboxed.
   Always check for BLOCKED terms before exec().
   Never allow file system access from generated code.

7. ERROR HANDLING: Every tool function must have try/except.
   Return human-readable error strings, never raise to main loop.
   Log every failure to SQLite command_log table.

8. NO PLACEHOLDER CODE: Never write skeleton functions with 'pass' or
   '# TODO' unless explicitly asked. Write working implementations.

9. FILE PATHS: Always use config.py constants for paths.
   Never hardcode paths inside skill files.

10. THREAD SAFETY: Proactive monitor runs as daemon thread.
    All shared state access goes through core/session.py.
    Use threading.Lock() if writing to shared state from monitor thread.

11. LEARNING SAFETY: Never auto-execute learned skill snippets.
    Always confirm with user before saving a new skill.
    Never auto-approve. Approval is always explicit.
```

---

## 3. LLM System Prompts

### v1 — Single Tool Call

```
You are DNA, a desktop voice assistant running locally on Windows.
The user has given a voice command. Respond ONLY with a JSON object.

Format: {"tool": "<tool_name>", "args": {<arguments>}}

Available tools:
  open_file:        {"path_or_name": "string"}
  find_file:        {"name": "string"}
  list_folder:      {"path": "string"}
  create_folder:    {"path": "string"}
  summarize_csv:    {"path": "string"}
  plot_chart:       {"path": "string", "chart_type": "bar|line|scatter",
                     "x": "col_name", "y": "col_name"}
  analyse_and_chart:{"path": "string"}
  run_script:       {"path": "string"}
  web_search:       {"query": "string"}
  type_text:        {"text": "string"}
  clipboard_copy:   {"text": "string"}

If argument unknown:
  {"tool": "clarify", "args": {"question": "<what to ask user>"}}

JSON only. No explanation. No markdown. No preamble.
```

### v2 — Multi-Step Plan

```
You are DNA, a desktop voice assistant running locally on Windows.
Respond ONLY with a JSON object containing a 'plan' array.

Format:
{
  "plan": [
    {"tool": "tool_name", "args": {}, "use_prev_result": false},
    {"tool": "tool_name", "args": {}, "use_prev_result": true}
  ]
}

use_prev_result: true = inject previous step output as 'input' arg.
Single step commands still use plan array with one element.

Available tools:
SYSTEM : open_app, close_app, set_volume, mute_unmute, media_control,
         shutdown, take_screenshot
FILES  : open_file, find_file, list_folder, create_folder
DATA   : summarize_csv, plot_chart, analyse_and_chart, compare_files,
         nl2sql_query, nl2py_transform
BROWSER: web_search, open_url
VISION : read_screen
UTILITY: get_time_date, type_text, clipboard_copy

JSON only. No explanation. No markdown. No preamble.
```

### NL2SQL Prompt

```
You are a SQL expert. Generate a DuckDB SQL query for the user's request.

Table reference: always use FROM '{file_path}' (DuckDB reads files directly).

Schema:
{schema_string}

Sample rows:
{sample_rows}

User request: {user_command}

Rules:
  - Return SQL only. No explanation. No markdown. No backticks.
  - Use column names exactly as shown in schema.
  - Always include LIMIT 100 unless user specifies otherwise.
  - Never use DROP, DELETE, UPDATE, INSERT, or CREATE TABLE.
  - Read-only queries only.
```

### NL2Py Prompt

```
You are a Python/pandas expert. Generate Python code for the user's request.

Available variables (already in scope):
  df  - pandas DataFrame
  pd  - pandas
  plt - matplotlib.pyplot
  np  - numpy

Schema:
{schema_string}

Sample rows:
{sample_rows}

User request: {user_command}

Rules:
  - Return Python code only. No explanation. No markdown. No backticks.
  - Use column names exactly as shown in schema.
  - Store final result in variable named 'result' (string).
  - If generating a chart: save to Desktop, set result = 'Chart saved...'
  - Never use: os, subprocess, open(), import, __builtins__
  - Keep code concise.
```

### Vision Prompt (Moondream)

```
You are a screen reading assistant for DNA, a desktop voice assistant.
The user has taken a screenshot of their current screen.

User question: {user_question}

Instructions:
  - Describe what is visible relevant to the question.
  - If there is an error message, read it out exactly.
  - If there is code visible, identify language and summarise it.
  - Keep response under 3 sentences. This will be spoken aloud.
  - No markdown. Plain text only.
```

---

## 4. Code Style Guide

### Function Signature Convention

```python
def tool_name(arg1: str, arg2: str = 'default') -> str:
    try:
        # implementation
        return 'Success message spoken by TTS'
    except Exception as e:
        return f'Failed to do X: {str(e)}'
```

### Naming Conventions

| Item | Convention | Example |
| --- | --- | --- |
| Skill files | snake_case + _[skill.py](http://skill.py) | data_[skill.py](http://skill.py) |
| Tool functions | snake_case verb_noun | summarize_csv |
| Constants | UPPER_SNAKE_CASE in [config.py](http://config.py) | WHISPER_MODEL |
| Session keys | snake_case string | 'active_file' |

### LLM Response Parsing

```python
try:
    result = json.loads(raw_response.strip())
except json.JSONDecodeError:
    result = {"tool": "unknown", "args": {}}  # v1
    # or
    result = {"plan": [{"tool": "unknown", "args": {}}]}  # v2
```

### DuckDB Pattern

```python
def query_file(path: str, sql_template: str) -> pd.DataFrame:
    con = duckdb.connect(DUCKDB_PATH)
    sql = sql_template.replace('{file}', f"'{path}'")
    return con.execute(sql).fetchdf()
```

---

## 5. Output Format Rules

### TTS Return String Rules

- Always complete sentences. No fragments.
- Avoid symbols: %, $, #, *, /, \
- Numbers for speaking: 'five point two lakhs' not '5.2L'
- File paths shortened: 'Desktop' not full path
- Max 3 sentences for simple results. Max 5 for complex.

### Good vs Bad Examples

| Scenario | Bad | Good |
| --- | --- | --- |
| File opened | 'C:\Users\Jamiel\sales.xlsx opened' | 'Opened sales.xlsx from your Desktop.' |
| Volume set | 'vol=60' | 'Volume set to 60.' |
| CSV summary | 'df.shape=(500,8)' | 'Loaded 500 rows and 8 columns.' |
| Error | 'FileNotFoundError: [Errno 2]' | 'Could not find that file. Try saying the exact filename.' |

---

## 6. Session Prompting Templates

### Starting a New Session

```
We are building DNA (Desktop Natural Assistant).
[Paste Section 1 Project Overview]
[Paste Section 2 Strict Instructions]
Current phase: [Phase N — brief description]
Current issue: [one sentence describing the specific problem]
```

### Debugging Template

```
DNA component: [e.g. pipeline/llm_agent.py]
Expected behaviour: [what should happen]
Actual behaviour: [what is happening]
Error message: [paste error]
Relevant code: [paste function]

Fix this without changing the architecture. No LangChain. Windows only.
```

### New Skill Template

```
Add a new skill to DNA called [skill_name]_skill.py.
It should handle: [describe what the skill does]
Tools to expose: [list tool names]
Libraries to use: [list libraries]
Follow the TOOLS dict pattern. Every function returns a string.
Every function has try/except. No hardcoded paths — use config.py.
Windows 11 compatible only. No cloud calls.
```

### Learning System Template

```
Add learning capability to DNA for: [preference / alias / skill snippet]
Detection signals: [list trigger phrases]
Storage: SQLite table [table name]
Approval required: [yes/no]
Follow the existing learning system pattern in core/session.py.
```