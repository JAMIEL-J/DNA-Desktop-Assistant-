# ui/tray.py
# ──────────────────────────────────────────────────────────────────────
# Systray Notification Area Icon
# Runs a daemon tray instance indicating DNA's listening state visually.
# ──────────────────────────────────────────────────────────────────────

import logging
import threading
import time

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None

from core.session import get as session_get, update as session_update

logger = logging.getLogger('dna.ui.tray')
_icon_instance = None

def _create_icon(state: str):
    """
    Generate a dynamic 64x64 icon visually depicting `state`.
    Green -> Listening actively
    Gray -> Idling
    """
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    color = '#10B981' if state == 'listening' else '#6B7280'
    draw.ellipse((8, 8, 56, 56), fill=color)
    
    return image

def _state_poller(icon):
    """Polls DNA's state and repaints the tray icon minimally."""
    last_state = 'idle'
    
    while icon.visible:
        is_listening = session_get('is_listening')
        current_state = 'listening' if is_listening else 'idle'
        
        if current_state != last_state:
            try:
                icon.icon = _create_icon(current_state)
                last_state = current_state
            except Exception:
                pass
        time.sleep(0.5)

def _setup_icon(icon):
    """Callback hook triggered when pystray registers properly."""
    icon.visible = True
    poller_thread = threading.Thread(target=_state_poller, args=(icon,), daemon=True, name="TrayPoller")
    poller_thread.start()

def _run_tray():
    """Initialises blocking loop for pystray internally within our tray thread."""
    global _icon_instance
    if not pystray:
        logger.warning('pystray or PIL not installed. Skipping tray icon creation.')
        return

    try:
        _icon_instance = pystray.Icon(
            "DNA",
            _create_icon('idle'),
            "DNA Assistant",
            menu=pystray.Menu(
                pystray.MenuItem("Exit DNA", lambda: _exit_dna())
            )
        )
        _icon_instance.run(setup=_setup_icon)
    except Exception as e:
        logger.error('Tray icon failed to launch: %s', e)

def _exit_dna():
    """Menu callback that tries to collapse DNA organically."""
    global _icon_instance
    logger.info('Tray exit requested. Shutting down...')
    session_update('is_running', False)
    if _icon_instance:
        _icon_instance.stop()

def start_tray():
    """Hook invoked in `dna_main` to safely daemonise the tray engine."""
    thread = threading.Thread(target=_run_tray, daemon=True, name="TrayThread")
    thread.start()
    logger.info('System tray presence established.')
