# 📄 PRD — Product Requirements Document

## 1. Project Overview
**DNA (Desktop Natural Assistant)** is a privacy-first, fully offline voice assistant for Windows. It is designed to run on mid-range hardware (Intel i3, 8GB RAM) without requiring an internet connection or a dedicated GPU.

## 2. Problem Statement
Existing voice assistants (Siri, Alexa, Cortana) depend on cloud processing, raising significant privacy concerns and requiring constant internet access. They often struggle with deep system integration and complex desktop automation.

## 3. Goals & Objectives
- **Privacy:** 100% offline processing. No data leaves the machine.
- **Speed:** Near-instant response via optimized local models.
- **Hardware Efficient:** Optimized for 8GB RAM and CPU-only execution.
- **Deep Integration:** Direct control over Windows OS, files, and local databases.

## 4. Key Features (v1)
- **Wake Word Detection:** Responds to "DNA" or "Hey DNA".
- **STT (Speech-to-Text):** High-accuracy offline transcription.
- **LLM Agent:** Uses `Qwen3.5:2b` via Ollama for intent logic.
- **Command Execution:** Secure NL2Py (Natural Language to Python) for system tasks.
- **TTS (Text-to-Speech):** Natural-sounding local voice responses.

## 5. Technical Constraints
- **OS:** Windows 10/11.
- **Hardware:** 8GB RAM, i3 CPU (minimal).
- **Environment:** Python 3.10+, Ollama.
