# DNA Master Prompt - Rebuild Blueprint

Version: 3.0
Date: 2026-04-13
Owner: Jamiel J.

This document is the rebuild contract for DNA.
If followed exactly, the project can be rebuilt from scratch with correct architecture, safety, and behavior.

---

## 1) Mission and Scope

PROJECT: DNA (Desktop Natural Assistant)
TYPE: Hybrid local-first, privacy-first Windows voice assistant
TARGET: Single-user desktop operator with safe tool execution

Core principle:
- Fast local operation first
- Optional cloud fallback only when configured
- Deterministic tool routing for simple commands
- Safety gate before any risky action

---

## 2) Rebuild Outcome Definition

A rebuild is correct only if all are true:
1. Voice loop works end-to-end: listen -> transcribe -> route -> execute -> speak.
2. Regex intents handle common commands without LLM.
3. Complex/ambiguous commands route through LLM planner safely.
4. Dangerous tools require spoken confirmation and timeout correctly.
5. Skill registry auto-discovers all tool modules dynamically.
6. Memory persists command logs, preferences, aliases, session state, and usage patterns.
7. Startup suggestion engine uses evidence thresholds and cooldown.
8. UI, tray, and proactive monitors run without crashing main loop.

---

## 3) Hard Constraints

1. Hardware first
- Must run on i3-class CPU, 8 GB RAM, no GPU.
- Avoid large always-on models.

2. No external agent frameworks
- Do not use LangChain/LlamaIndex/AutoGen/CrewAI.
- Use direct Python orchestration and direct API calls.

3. Hybrid local-first policy
- Local inference is default.
- Cloud fallback allowed only when API key exists.
- Core operations must not depend on cloud.

4. Windows 11 compatibility
- Use pathlib/os-safe path handling.
- Use Windows-safe subprocess/process flags.

5. Safety-first execution
- Block unsafe tool names and dangerous shell patterns.
- Require explicit confirmation for dangerous actions.

6. No placeholder logic
- No pass/TODO stubs in production behavior.

7. Config as source of truth
- Constants and thresholds must live in config.py.

8. Thread safety
- Shared session state through core/session.py with lock.

---

## 4) Required Runtime Stack

- Wake: openwakeword
- STT: faster-whisper
- TTS: piper-tts
- LLM local: Gemma 4 E2B via Ollama
- LLM fallback: Gemini when key configured
- Data: DuckDB + pandas + numpy + matplotlib
- Vision: Moondream via Ollama
- Automation: pyautogui
- Audio control: pycaw
- Persistence: sqlite3
- Desktop UX: PySide6 + pystray + plyer

---

## 5) Canonical Folder Structure

Create exactly this structure:

DNA-Assistant/
- config.py
- dna_main.py
- requirements.txt
- pipeline/
  - wake_word.py
  - stt.py
  - tts.py
  - intent_router.py
  - llm_agent.py
  - plan_executor.py
  - context_resolver.py
  - memory.py
- core/
  - session.py
  - safety.py
  - personality.py
  - skill_registry.py
  - proactive.py
- skills/
  - system_skill.py
  - file_skill.py
  - data_skill.py
  - vision_skill.py
  - browser_skill.py
  - learning_skill.py
- ui/
  - window.py
  - tray.py
  - toast.py
- data/
- logs/
- docs/

---

## 6) Module Contracts (Must Match)

config.py
- All constants and tunables live here.
- Includes model settings, audio thresholds, workflow templates, suggestion policy, and paths.

core/session.py
- Thread-safe key-value session state.
- Required keys: active_app, active_file, assistant_state, is_listening, is_speaking, mic_level, is_running, last_command, last_result.

core/safety.py
- DANGEROUS_TOOLS and BLOCKED_TOOLS policy.
- Path protection helpers.
- Argument/app name sanitization.
- Human-readable warning text for dangerous tools.

core/skill_registry.py
- Discover all *_skill.py modules.
- Merge exported TOOLS dictionaries into one tool map.

pipeline/intent_router.py
- Order: confirmation handling -> workflow trigger -> regex intents -> LLM fallback.
- Must call safety checks before direct execution.

pipeline/plan_executor.py
- Validate tool safety before execution.
- Execute step-by-step plan safely.

pipeline/llm_agent.py
- Local-first route.
- Optional cloud fallback when configured.
- Strict JSON parse and tool-name validation against tool map.

pipeline/memory.py
- SQLite init and CRUD for:
  - command_log
  - preferences
  - aliases
  - session_state
  - usage_patterns
- Incremental backfill from command_log into usage_patterns.
- Scored startup suggestion function with confidence/cooldown.

skills/*
- Every skill exports TOOLS dict.
- Every tool returns spoken-friendly string and catches exceptions.

dna_main.py
- Boot sequence initializes DB, restores session, discovers skills, starts monitors/tray/UI, and launches assistant loop.
- Assistant loop drives listen/transcribe/route/speak lifecycle.
- Saves session snapshot on shutdown.

---

## 7) Safety and Confirmation Contract

Dangerous actions require confirmation phrases and timeout:
- shutdown_computer
- restart_computer
- empty_recycle_bin
- lock_screen
- kill_process

Rules:
1. First command returns warning only.
2. Pending action expires after timeout.
3. confirm executes pending action.
4. cancel aborts pending action.
5. Unrelated command clears pending state.

Blocked tools never execute.

---

## 8) STT and Voice Behavior Contract

Required behavior:
1. Endpointed recording: tolerate short pauses.
2. Detect incomplete utterances and capture continuation.
3. Normalize noisy transcripts safely.
4. Avoid over-aggressive VAD clipping.

Expected user experience:
- Short pauses do not trigger early execution.
- Commands like open whatsapp and what is current system status are captured reliably.

---

## 9) Workflow and Suggestion Contract

Workflow templates:
- work mode
- focus mode
- end work

Behavior:
- Router must detect workflow phrase and execute predefined plan immediately.

Suggestion engine:
1. Track usage patterns by hour/day/tool/app.
2. Compute startup suggestion from usage scores.
3. Require min evidence and min confidence.
4. Require top-result margin over second candidate.
5. Respect cooldown to avoid repetition.
6. Backfill historical command logs incrementally.

---

## 10) Build Sequence (From Zero)

Phase 1: Core skeleton and config
- Create folder structure and config constants.
- Implement core/session.py and logging bootstrap.

Phase 2: Voice pipeline
- Implement wake_word.py, stt.py, tts.py.
- Verify listen/transcribe/speak loop.

Phase 3: Intent + tools baseline
- Implement system_skill.py baseline tools.
- Add regex intents and direct routing.

Phase 4: LLM fallback and planner
- Implement llm_agent.py and plan_executor.py.
- Add strict JSON parser and tool validation.

Phase 5: Memory persistence
- Implement pipeline/memory.py with SQLite init and command log.

Phase 6: Context and skill registry
- Add context resolver and dynamic skill discovery.

Phase 7: Data and vision skills
- Add data_skill.py and vision_skill.py.

Phase 8: Safety hardening
- Implement core/safety.py and confirmation flow.

Phase 9: UX and proactive services
- Add tray, toast, orb UI, proactive monitors.

Phase 10: Learning and suggestions
- Add preferences/aliases learning.
- Add usage pattern tracking and suggestion engine.

Phase 11: Workflow templates and deep OS controls
- Add workflow execution and advanced system controls.

---

## 11) Definition of Done by Capability

A capability is done only when:
1. Functionality works in real runtime path.
2. Safety checks are enforced.
3. Failure paths return human-readable spoken messages.
4. Changes compile successfully.
5. No regression in core voice loop.

---

## 12) Required Verification Checklist

Run after every major update:
1. Syntax compile for modified files.
2. Intent smoke tests:
- open app
- lock screen -> confirm/cancel flow
- kill process -> confirm flow
- workflow trigger
3. LLM fallback sanity test for unknown command.
4. Memory writes verified in SQLite tables.
5. Startup without crash and graceful shutdown.

---

## 13) Prompt Template to Start Any New Coding Session

Paste this block:

We are rebuilding DNA from scratch under the DNA Master Prompt Rebuild Blueprint.
Current phase: [phase]
Current task: [specific objective]
Files to implement: [list]
Constraints: Windows-only, hybrid local-first, no external agent frameworks, safety-gated execution.
Deliverables:
1) Working code
2) Compile validation
3) Short smoke-test evidence

---

## 14) Non-Negotiable Engineering Style

- Keep functions small and deterministic.
- Use explicit logging for critical path and failures.
- Do not silently swallow safety-relevant errors.
- Keep spoken responses concise and natural.
- Prefer robust defaults in config with env overrides.

---

## 15) Current Project State Snapshot

Completed capability envelope:
- Phases 1 through 17 implemented.
- Includes workflows, cross-session persistence, deep OS controls, usage intelligence, and scored startup suggestions.

This prompt is now the canonical rebuild spec.
