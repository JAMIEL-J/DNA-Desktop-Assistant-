# 🧬 DNA (Desktop Natural Assistant)

> **Next-Generation Swarm Intelligence Operating System for Windows 11**

DNA is a professional-grade, privacy-first desktop voice assistant and multi-agent terminal operating system. Built for high-performance desktop automation and low-resource environments, DNA turns your computer into an intelligent, voice-guided command center powered by a swarm of specialized AI agents.

---

## 🌟 Product Highlights

- 🎙️ **Voice-First Intelligent Control**: Speech-driven desktop automation with real-time on-screen subtitle HUD overlay.
- 🤖 **Swarm Intelligence Architecture**: 7 specialized autonomous agents working in unison under a central orchestrator.
- 🖥️ **Matrix OS Terminal Interface**: Next-gen dark-mode Web UI featuring real-time CPU/RAM telemetry, active audio visualizers, and agent activity logs.
- 🔒 **Privacy-First & Offline Resilience**: Runs core speech recognition, system automation, and local SQL database querying completely offline.
- ⚡ **Ultra-Low Resource Footprint**: Engineered to operate smoothly on dual-core / quad-core low-RAM hardware (under 350MB RAM backend footprint).

---

## 🏛️ System Architecture Overview

```
                                ┌──────────────────────────────────────────────┐
                                │             User Voice & Matrix OS           │
                                └──────────────────────┬───────────────────────┘
                                                       │
                                                       ▼
                                ┌──────────────────────────────────────────────┐
                                │          Perception & Gateway Router         │
                                └──────────────────────┬───────────────────────┘
                                                       │
                                                       ▼
                                ┌──────────────────────────────────────────────┐
                                │         NEXUS Swarm Orchestrator             │
                                └──────┬───────────┬───────────┬───────────┬───┘
                                       │           │           │           │
           ┌───────────────────────────┼───────────┴───────────┼───────────┼───────────────────────────┐
           ▼                           ▼                       ▼           ▼                           ▼
┌────────────────────┐      ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│      CIPHER        │      │       FORGE        │  │       ARGUS        │  │       HERMES       │  │       TITAN        │
│   (Data Analyst)   │      │   (Career & ATS)   │  │  (Vision & OCR)    │  │   (Web & Search)   │  │ (System Monitor)   │
└────────────────────┘      └────────────────────┘  └────────────────────┘  └────────────────────┘  └────────────────────┘
```

DNA employs a decoupled, event-driven multi-agent architecture:

1. **Perception Engine**: Listens for user voice input with Voice Activity Detection (VAD) to filter noise, automatically routing simple OS commands to local execution and complex tasks to the agent swarm.
2. **NEXUS Orchestrator**: The central brain that coordinates specialist agents over a shared memory blackboard, ensuring sub-agents execute tasks cleanly upon request.
3. **Specialist Agent Swarm**: Dedicated sub-agents handle data analysis, resume tailoring, desktop vision, web research, and system metrics concurrently.
4. **Matrix OS Real-Time Bridge**: Streams hardware metrics, live audio transcripts, and agent logs straight to the interactive web dashboard.

---

## 🤖 The Specialist Agent Swarm

DNA operates through 7 specialized agents, each mastering a distinct domain:

- 🧠 **NEXUS (Swarm Orchestrator)**: System leader that dispatches user intent, resolves conversation context, and coordinates multi-agent workflows.
- 📊 **CIPHER (Data Analyst)**: Runs instant SQL database queries on CSV and Excel datasets, generates data summaries, and detects data patterns.
- 💼 **FORGE (Career & ATS Engine)**: Scrapes job listings, calculates applicant job-fit scores, and tailors ATS-friendly resumes.
- 👁️ **ARGUS (Desktop Vision)**: Inspects your desktop screen, reads terminal error messages, and summarizes active window context.
- 🌐 **HERMES (Web Intelligence)**: Gathers live web research, summarizes online news, and navigates technical documentation.
- ⚡ **TITAN (System Monitor)**: Tracks real-time CPU/RAM metrics, adjusts volume and screen brightness, and manages application lifecycles.
- 💬 **JARVIS (Conversational Engine)**: Manages multi-turn natural dialogue, answers general queries, and provides butler-style voice responses.

---

## 🚀 Key Operating Modes

- **Swarm Roll Call**: Spoken initialization routine where all 6 agents report their operational readiness on boot.
- **Natural Voice Job Search**: Speak queries like *"Find data analyst roles"* to trigger job aggregation and relevance ranking automatically.
- **Work & Focus Workflows**: Issue *"Work mode"* or *"Focus mode"* to instantly set up your workspace, open IDEs, adjust audio volume, and minimize background distractions.
- **Instant Data Analytics**: Ask *"Analyze salary in table"* to trigger automated SQL data profiling and business insights.

---

## ⚙️ Quick Start

### 1. Installation
```powershell
git clone https://github.com/JAMIEL-J/DNA-Desktop-Assistant-.git
cd DNA-Desktop-Assistant-
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Running DNA
```powershell
python dna_main.py
```
*DNA will initialize the agent swarm, start the WebSocket bridge, and launch the Matrix OS React interface in your browser.*

---

## 📜 License

DNA is released under the **MIT License**. Built with ❤️ for next-generation desktop automation.
