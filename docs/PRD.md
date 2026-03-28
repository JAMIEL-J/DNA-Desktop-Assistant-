# PRD — Product Requirements Document

**Version:** 1.0 | **Date:** March 2026 | **Author:** Jamiel J.

---

## 1. Product Overview

DNA (Desktop Natural Assistant) is a fully offline, privacy-first voice assistant for Windows. Handles voice commands to control the PC, manage files, automate tasks, and perform data analysis — no internet or cloud dependency.

**Single user:** Jamiel J., data science professional, Tiruchirappalli, India.

---

## 2. Problem Statement

Daily friction points DNA eliminates:

- Manually opening the same apps and files every session
- Switching keyboard focus to control media or volume
- Running data analysis scripts by navigating file explorer
- Summarising CSV/Excel files by opening and reading manually
- Repetitive typing tasks that could be dictated

---

## 3. Goals and Non-Goals

### Goals

- Fully offline — no cloud, no API calls, no internet at runtime
- Voice activation from 2 meters away, no key press needed
- Handle single and multi-step commands naturally
- Resolve context across commands ('that file', 'it', 'the data')
- Handle datasets up to 10M+ rows via DuckDB without memory issues
- NL2SQL for query/filter commands, NL2Py for transform/plot
- Proactive alerts for CPU spikes and new downloads
- Screen reading via vision model for debugging support
- Learn preferences, aliases, and approved skill snippets

### Non-Goals

- No GUI dashboard (voice-only)
- No multi-user support
- No mobile or cross-device sync
- No internet-dependent features
- No cloud model inference

---

## 4. Target User

| Attribute | Value |
| --- | --- |
| Name | Jamiel J. |
| Role | Data Science Professional / Student |
| Location | Tiruchirappalli, India |
| Hardware | Intel i3-1134G4, 8GB RAM, 512GB SSD, Windows 11 |
| GPU | None (Intel UHD integrated only) |
| Distance from Laptop | 0–2 meters |
| Technical Level | High — full Python/ML stack |

---

## 5. Feature Requirements

### 5.1 Core Voice Pipeline

| Feature | Requirement | Priority |
| --- | --- | --- |
| Wake Word | Detect 'Hey DNA'/'Hey Jarvis' always-on, <5% CPU | P0 |
| STT | Transcribe within 2 seconds. Whisper tiny/base on CPU | P0 |
| TTS | Speak response within 1 second. Piper TTS | P0 |
| Latency | Simple: <4s. LLM commands: <12s | P0 |

### 5.2 System Control

| Command | Examples | Implementation |
| --- | --- | --- |
| App Control | Open Chrome, close VS Code | subprocess / pyautogui |
| Volume | Volume 60, mute, unmute | pycaw |
| Media | Play, pause, next, previous | pyautogui hotkeys |
| System | Shutdown, restart, sleep | os.system |
| Screenshot | Take a screenshot | pyautogui.screenshot() |

### 5.3 File Management

| Command | Examples | Implementation |
| --- | --- | --- |
| Open File | Open sales report | find_file + os.startfile |
| Find File | Find quarterly_data.xlsx | os.walk over SEARCH_PATHS |
| List Folder | List my downloads | os.listdir |
| Create Folder | Create folder named Models | os.makedirs |

### 5.4 Data Analysis

| Command Type | Approach | Threshold |
| --- | --- | --- |
| Query / Filter / Aggregate | NL2SQL → DuckDB | Always for >100K rows |
| Transform / Feature Engineering | NL2Py → sandboxed pandas exec | Only <100K rows |
| Plot / Visualise | NL2Py → matplotlib → PNG | Any size (uses sample) |
| Analyse + Chart combined | analyse_and_chart() multi-step | DuckDB stats + pandas plot |
| Compare two files | compare_files() diff on numeric cols | DuckDB for large files |

### 5.5 Context and Memory

- Session state: active_file, active_app, last_result, last_df maintained in memory
- Pronoun resolution: 'that file' / 'it' / 'the data' map to session state
- Conversation history: last 10 turns in SQLite, fed to LLM as context
- Command log: every command, tool, args, success/failure persisted

### 5.6 Learning System

| Level | What DNA Learns | Reliability |
| --- | --- | --- |
| Preference Learning | App paths, corrections ('Chrome is at...') | 100% |
| Alias Learning | 'my project' = D:Vizzy | 100% |
| Skill Snippets | Custom routines (with human review gate) | ~70% |

### 5.7 Proactive Monitoring

- CPU alert: speak warning when CPU >90% for 30 seconds
- Download alert: speak filename when new file appears in Downloads
- Daemon thread, non-blocking

### 5.8 Screen Reading

- Commands: 'what error is on my screen', 'describe my screen'
- Implementation: pyautogui screenshot + Moondream via Ollama

---

## 6. Technical Constraints

| Constraint | Detail |
| --- | --- |
| CPU only | Intel i3-1134G4. No GPU acceleration. |
| RAM budget | 8GB total. Qwen3.5:2b: ~1.4GB (Q4K). Whisper tiny: ~0.3GB. OS: ~2.5GB. Extra headroom vs Phi-3-mini due to smaller model size. |
| OS | Windows 11. All code must be Windows-compatible. |
| Internet | Not required at runtime. Only for initial model downloads. |
| LLM latency | Qwen3.5:2b: 2-5s (thinking OFF). 5-20s (thinking ON). Thinking mode routed per task — OFF by default, ON for web summarisation, file comparison, ambiguous commands. |

---

## 7. Success Metrics

| Metric | Target |
| --- | --- |
| Wake word false positive rate | <1 per hour |
| STT accuracy (clear speech) | >90% |
| Simple command latency | <4 seconds |
| LLM command latency | <12 seconds |
| Large file query (2M rows) | <5 seconds via DuckDB |
| RAM at runtime | <6GB total |
| CPU at idle | <5% |

---

## 8. Build Phases

| Phase | Goal | Est. Time |
| --- | --- | --- |
| 1 | STT + TTS pipeline working | 1–2 days |
| 2 | Wake word + basic system commands | 2–3 days |
| 3 | Intent router — simple commands without LLM | 2 days |
| 4 | LLM agent — complex file and DA commands | 3–4 days |
| 5 | SQLite memory and command logging | 1 day |
| 6 | Session state + context/pronoun resolution (v2) | 2–3 days |
| 7 | Plan executor — multi-step commands (v2) | 3–4 days |
| 8 | Skill registry — pluggable modules (v2) | 1 day |
| 9 | DuckDB + NL2SQL/NL2Py router (v2) | 3–4 days |
| 10 | Vision skill — Moondream (v2) | 2 days |
| 11 | Proactive monitor (v2) | 2 days |
| 12 | Learning system — preferences + aliases (v2) | 3 days |
| 13 | Stability, edge cases, error handling | 1 week |

---

## 9. Version Notes

> This is a living personal document. To convert for college submission: add formal abstract, literature review, and citation format. To convert for showcase: add benchmark screenshots and performance graphs.
>