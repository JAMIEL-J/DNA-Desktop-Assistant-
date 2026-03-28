# 🛠️ Feature Breakdown

**Version:** 1.0 | **Date:** March 2026 | **Author:** Jamiel J.

---

## Status Legend

| Tag | Meaning |
| --- | --- |
| v1 | Ships in DNA v1 (Basic) |
| v2 | Ships in DNA v2 (Powerful) |
| planned | On roadmap, not yet implemented |

---

## System Skill

| Tool | Trigger Patterns | Implementation | Ver |
| --- | --- | --- | --- |
| open_app | 'open [app]', 'launch [app]', 'start [app]' | subprocess.Popen or os.startfile | v1 |
| close_app | 'close [app]', 'quit [app]', 'kill [app]' | pygetwindow + close() | v1 |
| set_volume | 'volume [0-100]', 'set volume to [n]' | pycaw IAudioEndpointVolume | v1 |
| mute_unmute | 'mute', 'unmute', 'toggle mute' | pycaw toggle master mute | v1 |
| media_control | 'play', 'pause', 'next', 'previous', 'skip' | pyautogui media hotkeys | v1 |
| shutdown | 'shutdown', 'restart', 'sleep', 'hibernate' | os.system shutdown commands | v1 |
| take_screenshot | 'take a screenshot', 'screenshot', 'capture screen' | pyautogui.screenshot, saved to Desktop | v1 |

---

## File Skill

| Tool | Trigger Patterns | Implementation | Ver |
| --- | --- | --- | --- |
| open_file | 'open [filename]', 'open my [filename]' | find_file() then os.startfile(path) | v1 |
| find_file | 'find [filename]', 'where is [filename]' | os.walk over SEARCH_PATHS with fuzzy match | v1 |
| list_folder | 'list [folder]', 'show contents of [folder]' | os.listdir(path), filter hidden files | v1 |
| create_folder | 'create folder [name]', 'make folder [name]' | os.makedirs(path, exist_ok=True) | v1 |

---

## Data Skill

| Tool | Trigger Patterns | Route | Ver |
| --- | --- | --- | --- |
| summarize_csv | 'summarise [file]', 'describe [file]' | DuckDB if >100K rows, else pandas | v1 |
| plot_chart | 'plot [col] as [type]', 'chart [x] vs [y]' | NL2Py (matplotlib) | v1 |
| analyse_and_chart | 'analyse [file]', 'analyse and chart [file]' | DuckDB stats + NL2Py chart | v1 |
| compare_files | 'compare [file1] with [file2]' | DuckDB for large, pandas for small | v2 |
| nl2sql_query | 'how many [x]', 'show top [n] [col]' | NL2SQL → DuckDB | v2 |
| nl2py_transform | 'create column [name]', 'pivot by [col]' | NL2Py → sandboxed exec | v2 |

### Data Routing Logic

```python
QUERY_INTENTS = ['show', 'filter', 'find', 'top', 'count', 'sum', 'average', 'group']
TRANSFORM_INTENTS = ['create column', 'merge', 'pivot', 'reshape', 'calculate rolling']

def route_data_command(command, row_count):
    if any(w in command for w in QUERY_INTENTS): return 'nl2sql'
    if any(w in command for w in TRANSFORM_INTENTS): return 'nl2py'
    if row_count > 100_000: return 'nl2sql'  # always DuckDB for large files
    return 'nl2py'  # default for small files
```

### DuckDB Row Count Check

```python
def smart_engine(path):
    con = duckdb.connect()
    count = con.execute(f"SELECT COUNT(*) FROM '{path}'").fetchone()[0]
    return 'duckdb' if count > 100_000 else 'pandas'
```

---

## Vision Skill

| Tool | Trigger Patterns | Implementation | Ver |
| --- | --- | --- | --- |
| read_screen | 'what is on my screen', 'what error is showing', 'describe my screen' | pyautogui screenshot + Moondream via Ollama | v2 |

---

## Browser Skill

| Tool | Trigger Patterns | Implementation | Ver |
| --- | --- | --- | --- |
| web_search | 'search for [query]', 'google [query]' | [webbrowser.open](http://webbrowser.open)(google search URL) | v1 |
| open_url | 'open [url]', 'go to [url]' | [webbrowser.open](http://webbrowser.open)(url) | v2 |

---

## Utility Skill

| Tool | Trigger Patterns | Implementation | Ver |
| --- | --- | --- | --- |
| get_time_date | 'what time is it', 'what is today' | [datetime.now](http://datetime.now)().strftime() | v1 |
| type_text | 'type [text]', 'write [text]', 'dictate [text]' | pyautogui.typewrite() | v1 |
| clipboard_copy | 'copy [text] to clipboard' | pyperclip.copy(text) | v1 |

---

## Proactive Features

| Feature | Trigger | Interval | Response | Ver |
| --- | --- | --- | --- | --- |
| CPU alert | psutil.cpu_percent >90 for 30s | Every 30s | Speaks CPU% warning | v2 |
| Download alert | New file in ~/Downloads | Every 30s | Speaks filename | v2 |

---

## Learning System

| Level | Trigger Signals | Storage | Ver |
| --- | --- | --- | --- |
| Preference learning | 'no, i meant', 'wrong app', 'use this instead' | user_preferences SQLite | v2 |
| Alias learning | 'remember that', 'call it', 'whenever i say' | aliases SQLite | v2 |
| Skill snippets | 'create a skill', 'teach you to', 'whenever i say X do Y' | learned_skills SQLite + approval gate | v2 |

---

## Context Features (v2)

| Feature | Pronouns Resolved | Session Value |
| --- | --- | --- |
| Active file tracking | 'that file', 'it', 'the data', 'this file' | SESSION['active_file'] |
| Active app tracking | 'that app', 'it' | SESSION['active_app'] |
| Last result reference | 'the result', 'what you said' | SESSION['last_result'] |
| Last dataframe | 'the dataframe', 'the dataset' | SESSION['last_df'] |

---

## Multi-Step Plan Examples

### Example 1: Find and compare

**Command:** 'Find last month’s sales file and compare it with this month’s'

| Step | Tool | Args |
| --- | --- | --- |
| 1 | find_file | {'name': 'sales_feb'} |
| 2 | find_file | {'name': 'sales_mar'} |
| 3 | compare_files | {'path1': step1 result, 'path2': step2 result} |

### Example 2: Summarise and plot

**Command:** 'Summarise the Q1 data and generate a bar chart for revenue'

| Step | Tool | Args |
| --- | --- | --- |
| 1 | find_file | {'name': 'Q1'} |
| 2 | summarize_csv | {'path': step1 result} |
| 3 | plot_chart | {'path': step1 result, 'chart_type': 'bar', 'y': 'revenue'} |

---

## Planned Features (Post-v2)

| Feature | Skill | Blocker |
| --- | --- | --- |
| WhatsApp messaging | whatsapp_[skill.py](http://skill.py) | Requires browser always open |
| Gmail read/send | gmail_[skill.py](http://skill.py) | OAuth flow setup |
| Jupyter cell execution | notebook_[skill.py](http://skill.py) | nbformat + kernel API |
| Custom wake word | Wake word training | Requires recording training data |
| Calendar check | calendar_[skill.py](http://skill.py) | OAuth flow setup |
