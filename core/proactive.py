# core/proactive.py
# ──────────────────────────────────────────────────────────────────────
# Proactive Monitor — Background threads for CPU and Downloads alerts.
# Non-intrusive monitoring using is_listening to avoid speaking over the user.
# ──────────────────────────────────────────────────────────────────────

import logging
import time
import threading
from pathlib import Path
import psutil

from core.session import get as session_get
from pipeline.tts import speak_async
from ui.toast import show_toast

logger = logging.getLogger('dna.core.proactive')

_last_cpu_alert = 0.0
_last_download_alert = 0.0

# Monitoring intervals and thresholds
CPU_POLL_INTERVAL = 2         # seconds between CPU checks
CPU_ALERT_THRESHOLD = 90.0    # percent CPU to trigger alert

# Cooldowns in seconds
CPU_ALERT_COOLDOWN = 300      # 5 minutes
DOWNLOAD_ALERT_COOLDOWN = 60  # 1 minute

def _monitor_cpu():
    """Monitor CPU usage. Alert if >90% for a sustained period (10 seconds)."""
    global _last_cpu_alert
    high_cpu_count = 0

    while session_get('is_running', True):
        try:
            # interval=None gets point-in-time usage (since last call)
            cpu = psutil.cpu_percent(interval=CPU_POLL_INTERVAL)

            if cpu >= CPU_ALERT_THRESHOLD:
                high_cpu_count += 1
            else:
                high_cpu_count = 0

            # Trigger condition: 5 consecutive reads of >90% (10 seconds total)
            if high_cpu_count >= 5:
                now = time.time()
                if (now - _last_cpu_alert) > CPU_ALERT_COOLDOWN:
                    logger.warning("High CPU detected: %.1f%%", cpu)
                    
                    msg = f"Warning. Your CPU usage is unusually high, at {int(cpu)} percent."
                    show_toast("High CPU Usage", f"CPU utilization is at {int(cpu)}%")

                    # Only alert if the user isn't actively speaking/listening to DNA
                    if not session_get('is_listening'):
                        speak_async(msg)
                    
                    _last_cpu_alert = now
                high_cpu_count = 0

        except Exception as e:
            logger.error("CPU monitor error: %s", e)
            time.sleep(10)


def _monitor_downloads():
    """Monitor Downloads folder for completed files."""
    global _last_download_alert
    downloads_dir = Path.home() / 'Downloads'
    
    if not downloads_dir.exists():
        logger.warning('Downloads directory not found (%s). Monitor disabled.', downloads_dir)
        return

    def _get_files() -> set[str]:
        try:
            files = set()
            for f in downloads_dir.iterdir():
                # Ignore common incomplete flags
                if f.is_file() and not f.name.endswith(('.crdownload', '.tmp', '.part')):
                    files.add(str(f.resolve()))
            return files
        except Exception:
            return set()

    # Initial state (don't alert on existing files at startup)
    known_files = set(_get_files())

    while session_get('is_running', True):
        try:
            time.sleep(3)
            current_files = set(_get_files())
            
            # Identify newly arrived, fully formed files
            new_files = current_files - known_files

            if new_files:
                known_files.update(new_files)
                now = time.time()

                # Cooldown check prevents spamming if multiple files finish simultaneously
                if (now - _last_download_alert) > DOWNLOAD_ALERT_COOLDOWN:
                    if len(new_files) == 1:
                        new_name = Path(list(new_files)[0]).name
                        msg = f"Your download is complete: {new_name}"
                        show_toast("Download Complete", new_name)
                    else:
                        msg = f"{len(new_files)} new files have finished downloading."
                        show_toast("Downloads Complete", f"{len(new_files)} files have finished downloading.")
                        
                    if not session_get('is_listening'):
                        speak_async(msg)
                    
                    _last_download_alert = now

            # If files were deleted/moved, we must remove them from `known_files` 
            # so that if they are re-downloaded, they trigger an alert again.
            known_files.intersection_update(current_files)

        except Exception as e:
            logger.error("Download monitor error: %s", e)
            time.sleep(10)


def start_proactive_monitors():
    """Start all background monitor threads."""
    logger.info("Starting proactive background monitors...")

    cpu_thread = threading.Thread(target=_monitor_cpu, daemon=True, name="CPUMonitor")
    cpu_thread.start()

    dl_thread = threading.Thread(target=_monitor_downloads, daemon=True, name="DownloadMonitor")
    dl_thread.start()

    logger.info("Proactive monitors running.")
