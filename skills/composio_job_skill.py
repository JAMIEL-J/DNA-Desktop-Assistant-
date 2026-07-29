# skills/composio_job_skill.py
"""
DNA Composio Job Skill — Direct SDK Integration for Gmail & Google Sheets

Features:
- Direct SDK execution via composio-core (no MCP gateway overhead).
- Single-slot `_pending` state guarded by collision rejection and 60-second expiration timeout.
- Explicit max-1-retry limit (no infinite loops or silent retries).
- Calendar-day usage tracking with loud failure on limit breach.
- `dry_run` support for zero-side-effect test plan execution.
"""

import time
import logging
from config import COMPOSIO_API_KEY, COMPOSIO_DAILY_LIMIT, ORGANIZER_CONFIRM_TIMEOUT
from core.usage_tracker import check_daily_limit, log_usage

logger = logging.getLogger('dna.skill.composio_job')

# Single-slot pending action state
_pending = {
    "action_type": None,  # "email" or "sheet"
    "payload": None,
    "expires_at": 0.0
}

def _clear_pending():
    _pending["action_type"] = None
    _pending["payload"] = None
    _pending["expires_at"] = 0.0

def has_pending() -> bool:
    """Check if there is an unexpired pending Composio action awaiting confirmation."""
    return bool(_pending["action_type"]) and time.time() < _pending["expires_at"]

def preview_application_email(to_email: str, subject: str, body: str) -> str:
    """
    Prepares a job application email draft, speaks preview summary, and sets pending state.
    Rejects collision if another action is pending.
    """
    if has_pending():
        return f"You already have a pending {_pending['action_type']} action awaiting confirmation. Please confirm or cancel it first, sir."

    _pending["action_type"] = "email"
    _pending["payload"] = {
        "to": to_email,
        "subject": subject,
        "body": body
    }
    _pending["expires_at"] = time.time() + ORGANIZER_CONFIRM_TIMEOUT

    return (f"I have prepared a job application email to {to_email} with subject '{subject}'. "
            f"Shall I send this email? Say yes to confirm or no to cancel.")

def preview_log_sheet(spreadsheet_id: str, row_data: list) -> str:
    """
    Prepares a job log entry for Google Sheets, speaks preview summary, and sets pending state.
    Rejects collision if another action is pending.
    """
    if has_pending():
        return f"You already have a pending {_pending['action_type']} action awaiting confirmation. Please confirm or cancel it first, sir."

    _pending["action_type"] = "sheet"
    _pending["payload"] = {
        "spreadsheet_id": spreadsheet_id,
        "row_data": row_data
    }
    _pending["expires_at"] = time.time() + ORGANIZER_CONFIRM_TIMEOUT

    return (f"I have prepared to log this application to your Google Sheet ({spreadsheet_id[:8]}...). "
            f"Shall I append this entry? Say yes to confirm or no to cancel.")

def cancel_composio_action() -> str:
    """Cancel any pending Composio action."""
    if _pending["action_type"]:
        action_type = _pending["action_type"]
        _clear_pending()
        return f"Cancelled pending {action_type} action. Nothing was sent or logged."
    return "No pending action to cancel."

def confirm_composio_action(dry_run: bool = False) -> str:
    """
    Executes the pending Composio action after user confirmation.
    Includes timeout check, daily limit check, max-1-retry limit, and dry_run mode.
    """
    if not _pending["action_type"]:
        return "No pending application action. Please prepare an email or sheet log first."

    if time.time() > _pending["expires_at"]:
        _clear_pending()
        return "That confirmation request has expired, sir. Please preview the email or sheet log again."

    action_type = _pending["action_type"]
    payload = _pending["payload"]
    _clear_pending()

    # 1. Daily limit check
    allowed, current_count = check_daily_limit("composio", COMPOSIO_DAILY_LIMIT)
    if not allowed:
        error_msg = f"Composio daily tool execution limit reached ({current_count}/{COMPOSIO_DAILY_LIMIT} runs today). Action aborted."
        logger.error(error_msg)
        return f"[VOICE SPOKEN ERROR]: {error_msg}"

    # 2. Dry Run path (No external side-effects)
    if dry_run:
        logger.info("[DRY RUN] Executing Composio action type='%s' payload=%s", action_type, payload)
        log_usage("composio", f"dry_run_{action_type}", 1)
        if action_type == "email":
            return f"[DRY RUN] Would send email to {payload['to']} with subject '{payload['subject']}'."
        else:
            return f"[DRY RUN] Would append row {payload['row_data']} to spreadsheet {payload['spreadsheet_id']}."

    # 3. Direct SDK Execution with Max 1 Retry
    if not COMPOSIO_API_KEY:
        return "[VOICE SPOKEN ERROR]: COMPOSIO_API_KEY not configured in environment."

    try:
        from composio import ComposioToolSet, App
        toolset = ComposioToolSet(api_key=COMPOSIO_API_KEY)

        last_error = None
        for attempt in range(2):  # Attempt 0 (initial) + Attempt 1 (max 1 retry)
            try:
                if action_type == "email":
                    res = toolset.execute_action(
                        action=App.GMAIL.GMAIL_SEND_EMAIL,
                        params={
                            "recipient_email": payload["to"],
                            "subject": payload["subject"],
                            "body": payload["body"]
                        }
                    )
                    log_usage("composio", "send_email", 1)
                    return f"Successfully sent job application email to {payload['to']}."

                elif action_type == "sheet":
                    res = toolset.execute_action(
                        action=App.GOOGLESHEETS.GOOGLESHEETS_APPEND_VALUES,
                        params={
                            "spreadsheet_id": payload["spreadsheet_id"],
                            "values": [payload["row_data"]]
                        }
                    )
                    log_usage("composio", "append_sheet", 1)
                    return f"Successfully logged application row to Google Sheet."

            except Exception as ex:
                last_error = ex
                logger.warning("Composio execution attempt %d failed: %s", attempt + 1, ex)
                if attempt == 0:
                    time.sleep(0.5)  # brief pause before 1 single retry

        # If loop finishes, both attempts failed
        error_msg = f"Composio action execution failed after 1 retry: {str(last_error)}"
        logger.error(error_msg)
        return f"[VOICE SPOKEN ERROR]: {error_msg}"

    except Exception as e:
        logger.error("Composio SDK initialization failed: %s", e, exc_info=True)
        return f"[VOICE SPOKEN ERROR]: Composio error: {str(e)}"
