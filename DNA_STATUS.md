# DNA Project Status & Memory

## 🚀 Current Phase: Phase 17 — Suggestions & Behavioral Intelligence Foundation
**Goal**: Move from static automation to adaptive behavior using usage history, confidence scoring, and cooldown policies.
**Status**: ✅ Complete
**Current Task**: Suggestion policy engine, historical backfill, cross-session continuity, workflow templates, and deeper OS controls are fully integrated.

## 📋 Phase Tracker
| Phase | Goal | Status |
| --- | --- | --- |
| 1 | STT + TTS pipeline end-to-end | ✅ Complete |
| 2 | Wake word + system commands (open/volume/media) | ✅ Complete |
| 3 | Intent router — all simple commands without LLM | ✅ Complete |
| 4 | LLM agent — complex file and DA commands | ✅ Complete |
| 5 | SQLite memory + command logging | ✅ Complete |
| 6 | Session state + pronoun resolution (v2) | ✅ Complete |
| 7 | Plan executor — multi-step commands (v2) | ✅ Complete |
| 8 | Skill registry — auto-discovery (v2) | ✅ Complete |
| 9 | DuckDB + NL2SQL / NL2Py data router (v2) | ✅ Complete |
| 10 | Vision skill — Moondream (v2) | ✅ Complete |
| 11 | Proactive monitor — CPU / download alerts (v2) | ✅ Complete |
| 12 | Learning system — preferences + aliases (v2) | ✅ Complete |
| 13 | Tray icon + toast notifications (UI) | ✅ Complete |
| 14 | Stability, edge cases, error hardening | ✅ Complete |
| 15 | Personality & Humanization (Aide Persona) | ✅ Complete |
| 16 | Context, Workflow, and OS Expansion | ✅ Complete |
| 17 | Suggestion Engine & Usage Intelligence Foundation | ✅ Complete |

## 🧠 Memory Configuration (8GB RAM Optimization)
- **Target LLM:** Gemma 4 E2B (April 2026 Release) ~1.7GB
- **Target Vision:** Moondream ~1.1GB
- **Context Limit:** 2048 (Strict)
- **Virtual RAM:** 12GB SSD Page File (Required for i3 stability)

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
- **[2026-04-07]**: Phase 6 Complete. Added `pipeline/context_resolver.py` to resolve pronouns (it, this, that) using the session state. Hooked it into `intent_router.py`. Updated `system_skill.py` and `file_skill.py` to correctly update the session variables `active_app` and `active_file` upon usage. Transitioning to Phase 7.
- **[2026-04-07]**: Phase 7 Complete. Extracted `invoke_tool` and `execute_plan` into `pipeline/plan_executor.py`. Improved `use_prev_result` argument injection logic to dynamically bind previous tool steps' results based on the target tool's signature. Connected it with `llm_agent.py`. Transitioning to Phase 8.
- **[2026-04-07]**: Phase 8 Complete. Built `core/skill_registry.py` with `discover_skills()` and `get_tool_map()`. Refactored `skills/system_skill.py` to correctly house its related volume and brightness tools. Upgraded `pipeline/intent_router.py` to use dynamic skill mapping and hooked early loading into `dna_main.py`. Transitioning to Phase 9.
- **[2026-04-07]**: Phase 9 Complete. Created `skills/data_skill.py` with intelligent routing between DuckDB (>100K rows) and Pandas. Implemented NL2SQL and NL2Py via Ollama with robust safety filtering, schema injection, and session caching. Transitioning to Phase 10.
- **[2026-04-07]**: Phase 10 Complete. Created `skills/vision_skill.py` implementing `read_screen`. Added base64 image capture via pyautogui to interface directly with Ollama's `moondream` model API (added to `config.py`). Transitioning to Phase 11.
- **[2026-04-07]**: Phase 11 Complete. Created daemon background threads inside `core/proactive.py` that autonomously manage CPU bottleneck detection and downloaded files. Plugged into TTS securely, avoiding speaking over the user. Hooks integrated into `dna_main.py`. Transitioning to Phase 12.
- **[2026-04-07]**: Phase 12 Complete. Engineered `skills/learning_skill.py` to permit users to actively dictate preferences and app/folder aliases. Dynamically integrated mapping rules inside `skills/system_skill.py` and `skills/file_skill.py`. Plumbed preference awareness back into Ollama's payload construction via `pipeline/llm_agent.py`. Transitioning to Phase 13.
- **[2026-04-07]**: Phase 13 Complete. Created `ui/toast.py` wrapping the `plyer` library to invoke standard Windows 11 system notifications gracefully. Added `ui/tray.py` operating under a daemon polling routine through `pystray`. Safely wired instances back into `dna_main.py` and `core/proactive.py`. Transitioning to Phase 14.
- **[2026-04-07]**: Phase 14 Complete. Implemented a universally threaded lifecycle flag `is_running` natively within `core/session.py`. Hooked the wake-word block, proactive monitor thread loops, tray UI, and main `dna_main` sequence together so the entire application cleanly cascades to termination organically when stopped. All tasks fully validated.
- **[2026-04-10]**: **Phase 15 Complete (Personality & Humanization).** Created `core/personality.py` to house the "Loyal Digital Aide" persona. Updated the LLM system prompt in `pipeline/llm_agent.py` to follow an obedient and respectful tone. Developed a **Hybrid Humanization Path**: using the LLM for complex responses and a **Local Humanizer** (Python logic) for zero-latency rephrasing of regex tool results (e.g., "At once sir, volume set to 40"). Refined all greetings and prefixes to ensure natural TTS flow (removing redundant robotic pauses). Updated `dna_main.py` to acknowledge the user with dynamic, time-aware greetings ("Good afternoon sir, how can I be of assistance?").
- **[2026-04-10]**: UI system was redesigned to orb-only mode with frameless transparency and mic-level bubble, while preserving real-time state animation.
- **[2026-04-10]**: STT normalization and continuation logic were hardened to handle partial speech and phrase-splits (e.g., "what's app" -> "whatsapp", and multi-chunk continuation for incomplete utterances).
- **[2026-04-10]**: Lock-screen regex and dangerous-action confirmation flow were fixed so "lock my screen" and "confirm lock" route reliably without LLM ambiguity.
- **[2026-04-10]**: Endpointed speech capture implemented (pause-tolerant recording), replacing rigid fixed-window listening to avoid premature execution on short silence gaps.
- **[2026-04-13]**: **Phase 16 Complete (Context + Workflow + Deep OS V1).** Added workflow templates in `config.py` (`work mode`, `focus mode`, `end work`) and workflow trigger routing in `pipeline/intent_router.py` via `execute_plan`. Added cross-session persistence (`session_state`) with startup restore and shutdown save. Expanded system controls with `list_heavy_processes`, `kill_process`, and `get_system_health` in `skills/system_skill.py`.
- **[2026-04-13]**: Safety model expanded: `kill_process` added as dangerous tool with explicit confirm/cancel spoken flow.
- **[2026-04-13]**: **Phase 17 Complete (Suggestion Intelligence Foundation).** Added policy-controlled suggestion engine settings, scored startup suggestions (count/confidence/margin), cooldown suppression, and incremental usage backfill from historical `command_log` into `usage_patterns`.
- **[2026-04-13]**: Hybrid LLM posture finalized: local-first with optional cloud fallback available when API key is configured.
- **[2026-04-07]**: Memory Hardening for 8GB RAM Completed. Switched core engine to **Gemma 2 2B (Q4)** and limited `OLLAMA_CTX` to 2048 globally. Synchronized with **12GB SSD Virtual RAM (Page File)** swap strategy for absolute system stability on i3 hardware.
- **[2026-04-07]**: Memory Hardening for 8GB RAM Completed. Switched core engine to **Gemma 2 2B (Q4)** and limited `OLLAMA_CTX` to 2048 to prevent memory spikes on i3 hardware. Synchronized with **12GB SSD Virtual RAM (Page File)** swap strategy for guaranteed stability.

## 📂 Files Created / Modified
- `dna_main.py` — Entry point, main Wake→Listen→Route→Speak loop
- `pipeline/wake_word.py` — OpenWakeWord listener (ONNX)
- `pipeline/context_resolver.py` — Pronoun resolution based on session state (v2)
- `pipeline/intent_router.py` — Regex SIMPLE_INTENTS + volume_up/down + confirmation flow for dangerous tools
- `pipeline/llm_agent.py` — Ollama fallback with safety validation gates
- `pipeline/plan_executor.py` — Runs multi-step JSON tool plans with smart argument injection
- `core/skill_registry.py` — Auto-discovers and centralizes tool capabilities
- `skills/system_skill.py` — 26 system tools (sets active_app on execution)
- `skills/file_skill.py` — Dynamic folder explorer with protected path validation
- `skills/browser_skill.py` — Web automation tools
- `skills/data_skill.py` — NL2SQL/NL2Py analyzer with automatic DuckDB vs Pandas routing
- `skills/vision_skill.py` — Moondream local screen analysis capabilities
- `core/proactive.py` — Daemon thread manager for system resource monitoring and alerts
- `ui/tray.py` — Background interactive System Tray Icon engine
- `ui/toast.py` — Windows toast integration
- `core/personality.py` — Aide Persona engine, system prompt hub, and local humanizer (NEW)
- `core/__init__.py` — Core package init
- `core/session.py` — Thread-safe session state
- `core/safety.py` — Safety & security: path protection, command sanitisation, confirmation gates
- `pipeline/memory.py` — SQLite memory database operations
- `pipeline/memory.py` — SQLite memory + session persistence + usage intelligence + scored suggestions
- `test_phase2.py` — Intent router unit tests (35/35 pass)

## ⚠️ Active Constraints & Blockers
- **Constraint**: Strict compliance with `docs/Master_Development_Prompt.md` (now 16 constraints).
- **Constraint**: Dangerous tools (shutdown, restart, empty bin, lock) require spoken confirmation (30s timeout).
- **Constraint**: Dangerous process termination (`kill_process`) requires spoken confirmation.
- **Constraint**: Process isolation — all app launches use `DETACHED_PROCESS` flags to prevent UI crashes.
- **Constraint**: Protected paths (`C:\Windows`, `C:\Program Files`, `AppData`) are blocked from file operations.
- **Constraint**: Hybrid LLM mode is local-first; cloud fallback is optional and key-gated.
- **Resolved**: openwakeword model download, pycaw API mismatch.
- **Resolved**: Black screen / UI crash on app close (console window inheritance).
- **Note**: PyAutoGUI screenshot requires display. Media keys require active media player.

---
*To resume this project in a new session, ask Antigravity to: **"Read DNA_STATUS.md"***
