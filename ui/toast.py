# ui/toast.py
# ──────────────────────────────────────────────────────────────────────
# Toast UI Notifications
# Emits native Windows interactive toasts using plyer organically.
# ──────────────────────────────────────────────────────────────────────

import logging
from plyer import notification

logger = logging.getLogger('dna.ui.toast')

def show_toast(title: str, message: str, timeout: int = 5):
    """
    Shows a passive Windows toast notification.
    """
    try:
        notification.notify(
            title=title,
            message=message,
            app_name='DNA Assistant',
            timeout=timeout,
        )
    except Exception as e:
        logger.error('Failed to show toast notification: %s', e)
