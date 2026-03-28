# 🛠️ Feature Breakdown

## 1. Skill Modules
### System Control
- Volume, Brightness, Power (Sleep/Shutdown).
- Monitoring (CPU/RAM usage).

### File Management
- Search, Move, Delete (with confirmation).
- Content summarization (PDF/Txt).

### Data Analysis
- Querying CSV/Excel via NL2SQL (DuckDB).
- Visualization generation.

### Browser/Web (Limited)
- Local cache search.
- Specific site automation (if configured).

## 2. Proactive Features
- **Learning Mode:** Records user patterns to suggest macros or automated skills.
- **Contextual Memory:** Remembers the last 5 interactions for follow-up questions.
- **Self-Correction:** If a tool fails, the agent attempts to "Self-Debug" using LLM error analysis.

## 3. Development Phases
1. **Phase 1 (Core):** Wake + STT + Basic System Control + TTS.
2. **Phase 2 (Intelligence):** RAG (Docs) + SQLite Memory + NL2SQL.
3. **Phase 3 (Expansion):** Learning Mode + Vision (Screenshots) + Third-party API plugins.
