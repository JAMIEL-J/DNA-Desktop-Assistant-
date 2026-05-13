# ═══════════════════════════════════════════════════════════════
# ADD TO config.py
# ═══════════════════════════════════════════════════════════════

# Screen / Vision
SCREENSHOTS_DIR      = "data/screenshots"   # where screen captures are saved

# Window Monitor
WINDOW_MONITOR_INTERVAL = 2     # seconds between active window checks
WINDOW_ALERT_DELAY      = 15    # seconds on same window before alert fires


# ═══════════════════════════════════════════════════════════════
# ADD TO pipeline/intent_router.py SIMPLE_INTENTS
# (import screen_skill at top)
# ═══════════════════════════════════════════════════════════════

# from skills import screen_skill

SCREEN_INTENTS = {
    # Read / describe screen
    r"what('s| is) on (my )?screen":
        lambda m: screen_skill.read_screen("What is on this screen?"),

    r"(describe|read|look at) (my )?screen":
        lambda m: screen_skill.describe_screen(),

    r"(any |what |is there an? )error(s)? (on|showing|visible)":
        lambda m: screen_skill.find_error_on_screen(),

    r"what (window|app) (am i|is) (in|open|active)":
        lambda m: screen_skill.get_active_window(),

    r"(list|show|what are) (my |all )?(open )?(windows|apps)":
        lambda m: screen_skill.list_open_windows(),

    # Typing
    r"type (.+) (in|into|on) claude":
        lambda m: screen_skill.type_into_claude(m.group(1)),

    r"type (.+) (in|into) (vs ?code|vscode|code)":
        lambda m: screen_skill.type_into_vscode(m.group(1)),

    r"type (.+) and (send|submit|enter)":
        lambda m: screen_skill.type_and_send(m.group(1)),

    r"type (.+)":
        lambda m: screen_skill.type_text(m.group(1)),
}

# Add SCREEN_INTENTS into SIMPLE_INTENTS dict


# ═══════════════════════════════════════════════════════════════
# ADD TO dna_main.py — startup_sequence()
# ═══════════════════════════════════════════════════════════════

# from core.window_monitor import WindowMonitor, get_current_context

# In startup_sequence() or main():
#   WindowMonitor().start()


# ═══════════════════════════════════════════════════════════════
# ADD TO pipeline/llm_agent.py — inject window context into prompt
# ═══════════════════════════════════════════════════════════════

# from core.window_monitor import get_current_context

# In ask_llm(), add window context to system prompt:
#
# context = get_current_context()
# context_line = f"\nCurrent user context: {context}" if context else ""
#
# system_prompt = build_system_prompt(thinking) + context_line

# This means when user says "help me with this" while on Internshala,
# Gemma knows they're on a job portal and responds accordingly.


# ═══════════════════════════════════════════════════════════════
# EXAMPLE CONVERSATIONS
# ═══════════════════════════════════════════════════════════════

# [Screen reading]
# You: "What's on my screen?"
# DNA: takes screenshot → sends to Gemma 4 vision
# DNA: "You have VS Code open with a Python file. There's a syntax error
#       on line 42 — NameError: name df is not defined."

# [Error detection]
# You: "What error is showing?"
# DNA: "There is a red error box showing FileNotFoundError:
#       No such file or directory: data/sales.csv"

# [Typing into Claude]
# You: "Type what are the latest Claude updates into Claude"
# DNA: focuses Claude window → clicks input → types the question
# DNA: "Typed into Claude."

# [Typing and sending]
# You: "Type hello world and send"
# DNA: types "hello world" + presses Enter
# DNA: "Typed and sent."

# [Proactive job portal alert — automatic, no command needed]
# [User opens Internshala, stays 15 seconds]
# DNA: "Looks like you're on Internshala.
#       Want me to search for fresher Data Analyst openings?"

# [Proactive Claude alert]
# [User opens Claude, stays 15 seconds]
# DNA: "Claude is open. Want me to type something for you?"

# [Window context in LLM]
# You: "Help me with what I'm doing"
# Gemma sees: "User is currently in Visual Studio Code (coding context)."
# DNA: "You're in VS Code. Want me to run your current script,
#       open a file, or help with something specific?"


# ═══════════════════════════════════════════════════════════════
# INSTALL — no new packages needed
# pyautogui and pygetwindow already in requirements
# Pillow already in requirements
# google-generativeai already in requirements
# ═══════════════════════════════════════════════════════════════
