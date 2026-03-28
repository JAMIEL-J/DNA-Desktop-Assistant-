# 🏗️ System Design Document

## 1. Pipeline Architecture

### v1 Strategy (Linear)
`WakeWord (OpenWakeWord)` -> `STT (faster-whisper)` -> `Intent Router` -> `LLM Agent (Qwen3.5:2b)` -> `Tool Execution` -> `TTS (Piper)`

### v2 Strategy (Plan-Based)
Adds a **Task Planner** between Intent Router and LLM Agent to handle multi-step reasoning and complex workflows.

## 2. Technical Stack
- **STT:** `faster-whisper` (base.en model).
- **LLM:** `Ollama` running `qwen3.5:2b`.
- **TTS:** `Piper` (onnx-based, high speed).
- **Logic:** Python 3.11 core.
- **Database:** 
  - `SQLite` (Short-term memory, logging).
  - `DuckDB` (Large scale dataset analysis).

## 3. SQLite Schema
### Memory & Logs
- **`commands_log`**: `id, timestamp, raw_text, intent, success_status`
- **`memory_context`**: `id, key, value, expiration`
- **`learned_skills`**: `id, trigger_phrase, python_script_path`

## 4. Safety & Security
- **NL2Py Sandbox:** A restricted execution environment for generated scripts.
- **Blocked Libraries:** `os`, `subprocess`, `open` (unless via wrapper), `import` (dynamic).
- **Validation:** All tools must return a `human_readable` string and an `execution_code`.
