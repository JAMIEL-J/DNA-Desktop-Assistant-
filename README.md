# DNA — Desktop Natural Assistant

**DNA (Desktop Natural Assistant)** is an offline-only, privacy-first voice assistant for Windows. It leverages local AI models for speech-to-text, intent processing, and text-to-speech, ensuring all interactions remain secure and performant on mid-range hardware.

## 📁 Project Documentation
The core architectural and design specifications are stored in the `docs/` folder:

1. [PRD — Product Requirements Document](file:///d:/DNA(Desktop Assistant)/docs/PRD.md)
2. [System Design Document](file:///d:/DNA(Desktop Assistant)/docs/System_Design.md)
3. [UI/UX Wireframes](file:///d:/DNA(Desktop Assistant)/docs/UI_UX_Wireframes.md)
4. [Feature Breakdown Document](file:///d:/DNA(Desktop Assistant)/docs/Feature_Breakdown.md)
5. [Master Prompt Document](file:///d:/DNA(Desktop Assistant)/docs/Master_Prompt.md)

## 🛠️ Technology Stack
- **STT:** `faster-whisper`
- **LLM:** `Qwen3.5:2b` via Ollama
- **TTS:** `Piper`
- **Database:** DuckDB & SQLite
