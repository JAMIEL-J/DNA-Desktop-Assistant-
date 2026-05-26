# DNA Persistent Memory

## Developer Profile
- **Name:** Jamiel J.
- **Education:** B.Tech Information Technology, M.I.E.T. Engineering College, Tiruchirappalli (Graduation: June 2026)
- **Location:** Pudukkottai, India
- **Contact:** +91 78453 01134 | jahirjamiel@gmail.com
- **GitHub:** [github.com/JAMIEL-J](https://github.com/JAMIEL-J)
- **LinkedIn:** [linkedin.com/in/jamiel-j](https://linkedin.com/in/jamiel-j)
- **Preferred Coding Style:** Direct, casual Tanglish/English, concise scannable bullet points, no fluff.
- **Coding Environment:** Uses VS Code, Git, and Google's agentic IDE (referred to as "antigravity").

## System Hardware Profile
- **Operating System:** Windows 11
- **Hardware Specifications:** Intel i3-1134G4, 8GB RAM (4GB used at startup), no dedicated GPU.

## Active Projects

### 1. DNA (Desktop Natural Assistant)
*Offline Windows 11 Voice Assistant backend and frontend.*
- **LLM Core:** Gemma 4 31B via Gemini Developer API (`gemma-4-31b-it`). Text & vision native (no Moondream).
- **STT (Speech-to-Text):** `faster-whisper` base model, `int8` quantization, VAD filter enabled, confidence gate `< -1.0` discarded.
- **TTS (Text-to-Speech):** Piper using `en_US-lessac-medium` voice.
- **Wake Word:** OpenWakeWord (`hey_jarvis` model).
- **Architecture:** Raw Gemini API (no LangChain). Tasks use dynamic "thinking mode" (ON: web search/analysis; OFF: default). Active window detection via `window_monitor.py`. Thread-safe session management via `core/session.py`.
- **Session Lifecycle:** `SLEEPING` ➔ `ACTIVE` (10-minute idle auto-sleep) ➔ `PROCESSING`. Dismissed via "Jarvis close/stop/bye/sleep". Always-active on startup.
- **Frontend UI:** Interactive Three.js neural network globe (Fibonacci sphere distribution, audio-reactive) connected to Python backend via WebSocket.
- **Notion Hub ID:** `330e3690-cfb3-80af-b31d-fce27b4ce974`

### 2. Vizzy (Governed Analytics Platform)
*Final Year Project (Submission: April 7, 2026).*
- **Frontend Stack:** React 19, Vite, TailwindCSS, Recharts, Zustand.
- **Backend Stack:** FastAPI, DuckDB, SQLModel, SQLGlot, pandas.
- **Dual-LLM Logic (Groq API):** NL2SQL + narrative insight generation.
- **Features:** KPI auto-dashboards, approval-gated cleaning, immutable versioning, audit logging, DuckDB analytics store (~104ms p95 on 1M rows).
- **Production URL:** `https://vizzy-ai-dqgw.vercel.app`
- **Source Code:** [github.com/JAMIEL-J/Vizzy-Analytics](https://github.com/JAMIEL-J/Vizzy-Analytics)

## Core Skills & Technical Expertise
- **Programming Languages:** Python (Pandas, NumPy, Scikit-learn, SQLModel, PyTorch), SQL (MySQL, BigQuery, DuckDB).
- **Machine Learning & Stats:** LightGBM, XGBoost, Random Forest, Logistic Regression, Prophet, SARIMAX, Quantile Regression, SMOTE.
- **Visualization:** Tableau, Power BI, Streamlit, Plotly, HTML/CSS/JS (Three.js).
- **Established Projects:**
  - *Fraud Detection:* LightGBM (99.76% recall, ROC-AUC 0.9993).
  - *Demand Forecasting:* XGBoost/Prophet/SARIMAX (4.01% WAPE).
  - *Churn Prediction:* Scikit-learn (F1-optimized threshold).
  - *Ancient Tamil Palm-Leaf OCR:* Hybrid CRNN pipeline (84.6% CRR).

## Career Targeting & Preferences
- **Target Roles:** Data Scientist, ML Analyst, Data Analyst (Hybrid/Remote).
- **Target Applications:** Capgemini Invent DA role (Job ID: 420154).
- **Feedback Style:** Prefers brutally honest, direct, and actionable critique on resumes (using LaTeX ATS templates), portfolios, or code.
