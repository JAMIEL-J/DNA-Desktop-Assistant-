# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands
- **Setup**:
    - Install dependencies: `pip install -r requirements.txt`
    - Required Ollama models: `ollama pull gemma2:2b` and `ollama pull moondream`
- **Run main application**: `python dna_main.py`
- **Run test scripts**: `python test_phase<N>.py` (e.g., `python test_phase1.py`, `python test_phase2.py`, `python test_phase4.py`)
- **Run work mode test**: `python test_work_mode.py`

## Architecture Overview
DNA (Desktop Natural Assistant) is a local, privacy-first voice assistant for Windows using a pipeline-based architecture.

### Pipeline Flow
1. **Wake Word Detection**: `pipeline/wake_word.py` uses `openwakeword` to trigger the assistant.
2. **Speech-to-Text (STT)**: `pipeline/stt.py` converts audio to text using `faster-whisper`.
3. **Context Resolution**: `pipeline/context_resolver.py` resolves pronouns and session state.
4. **Intent Routing**: `pipeline/intent_router.py` uses a two-tier system:
    - **Fast Path (Regex)**: Immediate execution for common commands (<10ms).
    - **Agent Path (LLM)**: Fallback for complex/ambiguous requests.
5. **LLM Agent**: `pipeline/llm_agent.py` implements a hybrid routing strategy:
    - **Primary**: Google AI Studio API using `gemma-4-31b-it` (when `GOOGLE_API_KEY` is present).
    - **Fallback**: Ollama (e.g., `Qwen3.5:2b` or `gemma2:2b`).
    - Generates a JSON tool-call plan for the executor.
6. **Plan Execution**: `pipeline/plan_executor.py` loops through the generated plan and executes skills.
7. **Skill Execution**: Modular skills in `skills/` (e.g., `system_skill.py`, `data_skill.py`) perform the actual tasks.
8. **Text-to-Speech (TTS)**: `pipeline/tts.py` converts responses to audio using `Piper`.

### Core Components
- **Core Logic**: `core/` contains session management (`session.py`), personality (`personality.py`), and proactive monitoring (`proactive.py`).
- **UI Components**: `ui/` handles the system tray, window, and toast notifications using `PySide6`.
- **Data Layer**:
    - `data/dna_duck.db`: DuckDB for high-performance querying of local CSVs/datasets.
    - `data/dna_memory.db`: SQLite for conversation history, user preferences, and learned aliases.

### Data Routing Strategy
- **NL2SQL (DuckDB)**: Used for queries, filters, and aggregations on large datasets (>100K rows).
- **NL2Py (pandas)**: Used for transformations, feature engineering, and plotting.

### Safety & Constraints
- **Confirmation Gates**: Dangerous tools (shutdown, kill process) require spoken confirmation.
- **Path Protection**: Critical system directories (`C:\Windows`, `AppData`) are blocked from file operations.
- **Sandbox Execution**: Generated Python code for data analysis runs in a restricted namespace.
- **Hardware Budget**: Optimized for 8GB RAM using 4-bit quantization and demand loading for vision models.
