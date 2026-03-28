# 📜 Master Prompt Document

## 1. Core Project Overview
DNA is a local-only AI. Hardware is Intel i3, 8GB RAM.
**Key Rule:** No Cloud APIs, No LangChain. Use pure Python logic where possible.

## 2. Strict Instructions
- **Hardware:** Models must be quantized (q4 or q8).
- **Latency:** Target <2s response from Speech-to-Thought.
- **Safety:** Always wrap system-modifying code in `try-except`.

## 3. System Prompts

### Intent Router Prompt
```text
You are the DNA Intent Router.
Given the User Input, classify the intent into: [SYSTEM, FILE, DATA, BROWSER, CHAT].
Return ONLY the category name.
```

### NL2Py (Natural Language to Python) Prompt
```text
Generate a clean, modular Python function for the task below.
- User Target: "{{user_input}}"
- Available Tools: list_files(), move_file(), set_volume().
- Constraint: No external libraries. Return ONLY the code block.
```

### Safety & Standards
- All tools must use a `config.py` for pathing.
- Pathing must be absolute via `pathlib`.
- Coding Style: Standard PEP8, human-readable variable names.
