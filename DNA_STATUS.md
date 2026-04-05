# DNA Project Status & Memory

## 🚀 Current Phase: Phase 6
**Goal**: Session state + pronoun resolution (v2).
**Status**: 🚀 In Progress
**Current Task**: Track active context and resolve pronouns (it, this, that) using session state.

## 📋 Phase Tracker
| Phase | Goal | Status |
| --- | --- | --- |
| 1 | STT + TTS pipeline end-to-end | ✅ Complete |
| 2 | Wake word + system commands (open/volume/media) | ✅ Complete |
| 3 | Intent router — all simple commands without LLM | ✅ Complete |
| 4 | LLM agent — complex file and DA commands | ✅ Complete |
| 5 | SQLite memory + command logging | ✅ Complete |
| 6 | Session state + pronoun resolution (v2) | 🚀 In Progress |
| 7 | Plan executor — multi-step commands (v2) | ⏳ Pending |
| 8 | Skill registry — auto-discovery (v2) | ⏳ Pending |
| 9 | DuckDB + NL2SQL / NL2Py data router (v2) | ⏳ Pending |
| 10 | Vision skill — Moondream (v2) | ⏳ Pending |
| 11 | Proactive monitor — CPU / download alerts (v2) | ⏳ Pending |
| 12 | Learning system — preferences + aliases (v2) | ⏳ Pending |
| 13 | Tray icon + toast notifications (UI) | ⏳ Pending |
| 14 | Stability, edge cases, error hardening | ⏳ Pending |

## 🔑 Session Memory
- **[2026-03-28]**: Project initialization. Master Prompt read. Persistent memory file created.
- **[2026-03-28]**: Phase 1 Complete. STT (faster-whisper base) and TTS (Piper 1.4.1 AudioChunk API) verified.
- **[2026-03-28]**: Phase 2 Complete. Created: wake_word.py, system_skill.py (17 tools), intent_router.py (23 patterns), dna_main.py, core/session.py.
- **[2026-03-28]**: openwakeword uses ONNX framework (tflite-runtime not available on Python 3.14/Win). Downloaded hey_jarvis, melspectrogram, embedding models manually.
- **[2026-03-28]**: Phase 3 Complete. Added Browser Skill, File Skill (Recursive Depth 2), Brightness control, and STT loop-hardening.
- **[2026-03-28]**: Implemented Case-Preference search and solved 'Intent Shadowing' bug where apps stole folder commands.
- **[2026-03-28]**: Transitioning to Phase 4 (LLM agent Integration).
- **[2026-03-29]**: Phase 4 integration started. Added `pipeline/llm_agent.py`, wired LLM fallback in `pipeline/intent_router.py`, and added Ollama tuning settings in `config.py`.
- **[2026-03-29]**: Phase 4 marked complete. Activated Phase 5 for SQLite memory and command logging implementation.
- **[2026-03-29]**: Added `test_phase4.py` for deterministic Phase 4 fallback validation (7/7 passed). Live Ollama smoke check auto-skips when Ollama is offline.
- **[2026-03-29]**: Extensive structural hardening and debugging. Added `threading.Lock()` to Whisper/Piper initializers, migrated `wait_for_wake_word` to `threading.Event()`, added robust atomic file download capabilities (`shutil.copyfileobj`). Patched `shell=True` vulnerabilities across `system_skill.py` and improved punctuation retention in LLM fuzzy corrections. Added cross-platform fallbacks for `os.startfile`.
- **[2026-04-05]**: **Crash Fix & Safety Hardening.** Fixed black screen / UI crash on app close caused by child processes inheriting console window (added `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` flags). Created `core/safety.py` — new security module with protected path checking, dangerous tool confirmation flow (30s timeout), blocked tool enforcement, shell command pattern detection, and app name sanitisation. Hardened `pipeline/llm_agent.py` with safety rules in system prompt, tool name validation against hallucination, and pre-execution safety gates. Updated `pipeline/intent_router.py` with full confirmation flow for shutdown/restart/empty bin/lock. Hardened `skills/file_skill.py` with protected path validation. Added constraints #14 (Process Isolation) and #15 (Safety & Confirmation Flow) to Master Prompt.
- **[2026-04-05]**: Phase 5 Complete. Added `pipeline/memory.py` for SQLite DB initialization. Added tables: `conversation`, `command_log`, `preferences`, `aliases`. Wired `init_db()` and `log_command()` into `dna_main.py` to persist all text commands and errors reliably.

## 📂 Files Created / Modified
- `dna_main.py` — Entry point, main Wake→Listen→Route→Speak loop
- `pipeline/wake_word.py` — OpenWakeWord listener (ONNX)
- `pipeline/intent_router.py` — Regex SIMPLE_INTENTS + volume_up/down + confirmation flow for dangerous tools
- `pipeline/llm_agent.py` — Ollama fallback with safety validation gates
- `skills/system_skill.py` — 22 system tools (crash-free process launch with DETACHED_PROCESS flags)
- `skills/file_skill.py` — Dynamic folder explorer with protected path validation
- `skills/browser_skill.py` — Web automation tools
- `core/__init__.py` — Core package init
- `core/session.py` — Thread-safe session state
- `core/safety.py` — Safety & security: path protection, command sanitisation, confirmation gates
- `pipeline/memory.py` — SQLite memory database operations
- `test_phase2.py` — Intent router unit tests (35/35 pass)

## ⚠️ Active Constraints & Blockers
- **Constraint**: Strict compliance with `docs/Master_Development_Prompt.md` (now 15 constraints).
- **Constraint**: Dangerous tools (shutdown, restart, empty bin, lock) require spoken confirmation (30s timeout).
- **Constraint**: Process isolation — all app launches use `DETACHED_PROCESS` flags to prevent UI crashes.
- **Constraint**: Protected paths (`C:\Windows`, `C:\Program Files`, `AppData`) are blocked from file operations.
- **Resolved**: openwakeword model download, pycaw API mismatch.
- **Resolved**: Black screen / UI crash on app close (console window inheritance).
- **Note**: PyAutoGUI screenshot requires display. Media keys require active media player.

---
*To resume this project in a new session, ask Antigravity to: **"Read DNA_STATUS.md"***
