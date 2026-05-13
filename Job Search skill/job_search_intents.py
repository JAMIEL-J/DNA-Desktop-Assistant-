# ═══════════════════════════════════════════════════════════════
# ADD TO config.py
# ═══════════════════════════════════════════════════════════════

JOB_ROLES          = ["data analyst", "data scientist", "business analyst",
                       "data engineer", "ml engineer"]
JOB_LOCATION       = "South India"
JOB_MAX_AGE_DAYS   = 14          # jobs posted in last 14 days
JOB_RESULTS_DIR    = "data/job_results"
JOB_EXPERIENCE_LEVEL = "fresher"


# ═══════════════════════════════════════════════════════════════
# UPDATE pipeline/session_manager.py
# Add JOB_SEARCH state to DNAState enum
# ═══════════════════════════════════════════════════════════════

# from enum import Enum
#
# class DNAState(Enum):
#     SLEEPING    = "sleeping"
#     ACTIVE      = "active"
#     ALWAYS_ACTIVE = "always_active"
#     PROCESSING  = "processing"
#     JOB_SEARCH  = "job_search"    # ← ADD THIS


# ═══════════════════════════════════════════════════════════════
# UPDATE pipeline/intent_router.py
# ═══════════════════════════════════════════════════════════════

# from skills import job_search_skill
# from skills.job_search_skill import is_job_search_active

# ── Job search MODE trigger (works from any state) ────────────
JOB_SEARCH_TRIGGER_INTENTS = {
    r"(job search mode|jarvis job search|start job search)":
        lambda m: job_search_skill.enter_job_search_mode("all"),

    r"(job search|search jobs).*(data analyst|analyst)":
        lambda m: job_search_skill.enter_job_search_mode("data analyst"),

    r"(job search|search jobs).*(data scien|scientist)":
        lambda m: job_search_skill.enter_job_search_mode("data scientist"),

    r"(job search|search jobs).*(business analyst|BA)":
        lambda m: job_search_skill.enter_job_search_mode("business analyst"),

    r"(job search|search jobs).*(data engineer|DE)":
        lambda m: job_search_skill.enter_job_search_mode("data engineer"),

    r"(job search|search jobs).*(ml|machine learning)":
        lambda m: job_search_skill.enter_job_search_mode("ml engineer"),
}

# ── In-session commands (only active when JOB_SEARCH mode is on) ──
JOB_SESSION_INTENTS = {
    r"\bnext\b":
        lambda m: job_search_skill.next_jobs(),

    r"\b(previous|back|prev)\b":
        lambda m: job_search_skill.previous_jobs(),

    r"open (number |job )?(\d+)":
        lambda m: job_search_skill.open_job(int(m.group(2))),

    r"(save|bookmark) (number |job )?(\d+)":
        lambda m: job_search_skill.save_current_job(int(m.group(3))),

    r"(save|bookmark) (this|that|it)":
        lambda m: job_search_skill.save_current_job(1),

    r"search (for )?(data analyst|data scientist|business analyst|data engineer|ml engineer)":
        lambda m: job_search_skill.search_role(m.group(2)),

    r"(exit|stop|end|quit|leave) job search":
        lambda m: job_search_skill.exit_job_search(),
}

# ── Updated route() function in intent_router.py ──────────────
#
# def route(command: str):
#     cmd = command.lower().strip()
#
#     # 1. Dismiss check first (existing)
#     if is_dismiss_command(cmd):
#         return None, "dismiss"
#
#     # 2. If in job search mode — route to job session intents
#     if is_job_search_active():
#         for pattern, handler in JOB_SESSION_INTENTS.items():
#             match = re.search(pattern, cmd)
#             if match:
#                 return handler(match), "simple"
#         # If no job session match, fall through to normal routing
#         # (so user can still do other commands during job search)
#
#     # 3. Job search trigger
#     for pattern, handler in JOB_SEARCH_TRIGGER_INTENTS.items():
#         match = re.search(pattern, cmd)
#         if match:
#             return handler(match), "simple"
#
#     # 4. Normal SIMPLE_INTENTS (existing)
#     for pattern, handler in SIMPLE_INTENTS.items():
#         match = re.search(pattern, cmd)
#         if match:
#             return handler(match), "simple"
#
#     # 5. LLM fallback (existing)
#     return None, "llm"


# ═══════════════════════════════════════════════════════════════
# EXAMPLE CONVERSATIONS
# ═══════════════════════════════════════════════════════════════

# [Enter job search mode]
# You : "Jarvis job search mode"
# DNA : "Entering job search mode. Searching for Data Analyst and
#        Data Science fresher roles in South India. One moment.
#        Found 28 fresher openings.
#        Showing jobs 1 to 5 of 28.
#        Number 1: Data Analyst at Zoho, Chennai.
#        Number 2: Junior Data Scientist at Infosys, Bangalore.
#        Number 3: Business Analyst at TCS, Hyderabad.
#        Number 4: Data Analyst at Freshworks, Chennai.
#        Number 5: ML Analyst at Wipro, Coimbatore.
#        Say next for more, open number to open a job,
#        save to bookmark, or exit job search to stop.
#        Full list saved to jobs_all_2026-04-15.csv."

# [Navigate]
# You : "Next"
# DNA : "Showing jobs 6 to 10 of 28. Number 6: ..."

# [Open a job]
# You : "Open number 3"
# DNA : "Opening Business Analyst at TCS in your browser."

# [Save a job]
# You : "Save number 2"
# DNA : "Saved Junior Data Scientist at Infosys. You have 1 saved job."

# [Switch role]
# You : "Search for data engineer"
# DNA : "Searching for Data Engineer fresher roles in South India..."

# [Exit]
# You : "Exit job search"
# DNA : "Exiting job search mode. You saved 3 jobs out of 28 found.
#        Check saved_jobs.csv in your job results folder."

# [Role-specific trigger]
# You : "Job search data analyst"
# DNA : "Entering job search mode. Searching for Data Analyst fresher roles..."


# ═══════════════════════════════════════════════════════════════
# INSTALL
# ═══════════════════════════════════════════════════════════════

# pip install beautifulsoup4 requests feedparser
# feedparser + requests already in requirements from news/jobs skill
# beautifulsoup4 may need adding:
# pip install beautifulsoup4
