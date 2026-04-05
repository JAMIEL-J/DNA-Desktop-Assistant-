# skills/system_skill.py
# ──────────────────────────────────────────────────────────────────────
# System-level tools: volume, brightness, media, app management, etc.
# v2 — Hardened against UI crashes + safety integration
# ──────────────────────────────────────────────────────────────────────

# 1. stdlib
import ctypes
import datetime
import logging
import os
import subprocess
import time

# 2. third-party
import pyautogui

# 3. internal
from config import APP_ALIASES, APP_PROPER_NAMES, APP_PROCESS_MAP
from core.safety import sanitise_app_name, is_path_protected

logger = logging.getLogger('dna.skill.system')

# ── Win32 Constants for crash-free process creation ────────────────
# These prevent the child process from inheriting our console window
# which is the root cause of the "black screen" on app close.
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

# Combined flags for maximum isolation
_LAUNCH_FLAGS = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def _safe_popen(args: list[str], shell: bool = False) -> subprocess.Popen | None:
    """Launch a process fully detached from our console.

    - Uses DETACHED_PROCESS so the child gets its own console (or none).
    - Redirects stdin/stdout/stderr to DEVNULL to avoid pipe deadlocks.
    - Returns the Popen object on success, None on failure.
    """
    try:
        proc = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_LAUNCH_FLAGS,
            close_fds=True,
            shell=shell,
            start_new_session=True,  # Fully detach from parent session
        )
        logger.debug('Launched PID %d: %s', proc.pid, args)
        return proc
    except FileNotFoundError:
        logger.warning('Executable not found: %s', args)
        return None
    except OSError as e:
        logger.error('OS error launching %s: %s', args, e)
        return None
    except Exception as e:
        logger.error('Failed to launch %s: %s', args, e)
        return None


def _safe_startfile(target: str) -> bool:
    """Use os.startfile with error handling.

    os.startfile is the safest way to open files / protocols on Windows
    because it delegates to the Shell (ShellExecute) which handles
    window creation correctly.
    """
    try:
        os.startfile(target)
        return True
    except OSError as e:
        logger.error('os.startfile failed for %s: %s', target, e)
        return False
    except Exception as e:
        logger.error('Unexpected error in startfile for %s: %s', target, e)
        return False


def _graceful_close(exe_name: str, display_name: str) -> str:
    """Try to close an app gracefully, falling back to force-kill.

    Chain: taskkill (graceful) → wait 2s → taskkill /F (forced)
    This avoids the abrupt termination that can leave orphan windows.
    """
    # Step 1: Graceful close (sends WM_CLOSE to all windows of the process)
    result = subprocess.run(
        ['taskkill', '/IM', exe_name, '/T'],
        capture_output=True, text=True, check=False,
        creationflags=CREATE_NO_WINDOW,
    )

    if result.returncode == 0:
        logger.info('Gracefully closed %s', exe_name)
        return f'Closed {display_name}.'

    # Step 2: If graceful close failed, wait briefly then force-kill
    time.sleep(1.0)

    result = subprocess.run(
        ['taskkill', '/IM', exe_name, '/F', '/T'],
        capture_output=True, text=True, check=False,
        creationflags=CREATE_NO_WINDOW,
    )

    if result.returncode == 0:
        logger.info('Force-killed %s', exe_name)
        return f'Closed {display_name}.'

    # Step 3: Check if process is actually not running
    err_msg = (result.stderr or '').strip().lower()
    if 'not found' in err_msg or result.returncode == 128:
        return f'{display_name} is not currently running.'

    logger.warning('taskkill failed for %s (rc=%d): %s',
                   exe_name, result.returncode, result.stderr)
    return f'Could not close {display_name}. It may require manual closing.'


# ════════════════════════════════════════════════════════════════════
# Volume Controls
# ════════════════════════════════════════════════════════════════════

def set_volume(level: str) -> str:
    """Set system volume to a percentage (0-100)."""
    try:
        target = int(level)
        if target < 0 or target > 100:
            return 'Volume must be between 0 and 100.'

        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        vol = device.EndpointVolume
        vol.SetMasterVolumeLevelScalar(target / 100.0, None)

        return f'Volume set to {target} percent.'
    except Exception as e:
        logger.error('set_volume failed: %s', e)
        return f'Could not set volume: {str(e)}'


def get_volume() -> str:
    """Get current system volume level."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        vol = device.EndpointVolume
        current = round(vol.GetMasterVolumeLevelScalar() * 100)

        return f'Volume is at {current} percent.'
    except Exception as e:
        logger.error('get_volume failed: %s', e)
        return f'Could not get volume: {str(e)}'


# ════════════════════════════════════════════════════════════════════
# Brightness Controls
# ════════════════════════════════════════════════════════════════════

def set_brightness(level: str) -> str:
    """Set screen brightness (0-100)."""
    try:
        target = int(level)
        if target < 0 or target > 100:
            return 'Brightness must be between 0 and 100.'

        cmd = f'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {target})"'
        subprocess.run(cmd, shell=True, check=True,
                       creationflags=CREATE_NO_WINDOW)
        return f'Brightness set to {target} percent.'
    except Exception as e:
        logger.error('set_brightness failed: %s', e)
        return f'Could not set brightness: {str(e)}'


def get_brightness() -> str:
    """Get current screen brightness level."""
    try:
        cmd = 'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                check=True, creationflags=CREATE_NO_WINDOW)
        current = int(result.stdout.strip())
        return f'Brightness is at {current} percent.'
    except Exception as e:
        logger.error('get_brightness failed: %s', e)
        return f'Could not get brightness: {str(e)}'


# ════════════════════════════════════════════════════════════════════
# Mute / Audio Controls
# ════════════════════════════════════════════════════════════════════

def mute_toggle() -> str:
    """Toggle system mute on/off."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        vol = device.EndpointVolume
        current_mute = vol.GetMute()
        vol.SetMute(not current_mute, None)

        state = 'muted' if not current_mute else 'unmuted'
        return f'System is now {state}.'
    except Exception as e:
        logger.error('mute_toggle failed: %s', e)
        return f'Could not toggle mute: {str(e)}'


def mute() -> str:
    """Mute system audio."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        vol = device.EndpointVolume
        vol.SetMute(True, None)
        return 'System is now muted.'
    except Exception as e:
        logger.error('mute failed: %s', e)
        return f'Could not mute: {str(e)}'


def unmute() -> str:
    """Unmute system audio."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        vol = device.EndpointVolume
        vol.SetMute(False, None)
        return 'System is now unmuted.'
    except Exception as e:
        logger.error('unmute failed: %s', e)
        return f'Could not unmute: {str(e)}'


# ════════════════════════════════════════════════════════════════════
# Media Controls
# ════════════════════════════════════════════════════════════════════

def media_play_pause() -> str:
    """Toggle media play/pause."""
    try:
        pyautogui.press('playpause')
        return 'Toggled play pause.'
    except Exception as e:
        logger.error('media_play_pause failed: %s', e)
        return f'Could not toggle play pause: {str(e)}'


def media_next() -> str:
    """Skip to next media track."""
    try:
        pyautogui.press('nexttrack')
        return 'Skipped to next track.'
    except Exception as e:
        logger.error('media_next failed: %s', e)
        return f'Could not skip track: {str(e)}'


def media_previous() -> str:
    """Go to previous media track."""
    try:
        pyautogui.press('prevtrack')
        return 'Went to previous track.'
    except Exception as e:
        logger.error('media_previous failed: %s', e)
        return f'Could not go to previous track: {str(e)}'


# ════════════════════════════════════════════════════════════════════
# App Launch & Close — CRASH-FREE
# ════════════════════════════════════════════════════════════════════

def open_app(app_name: str) -> str:
    """Open an application by name (crash-free).

    Launch strategy by app type:
      1. shell:AppsFolder (UWP/Store apps) → explorer.exe via _safe_popen
      2. Protocol handlers (whatsapp:, ms-settings:) → os.startfile
      3. Direct executables (.exe paths) → _safe_popen
      4. Short names (notepad, calc) → os.startfile fallback
    """
    try:
        # ── Sanitise input ──
        safe_name = sanitise_app_name(app_name)
        if safe_name is None:
            return 'That application name looks invalid. Please try again.'

        name = safe_name.lower().strip()
        display_name = APP_PROPER_NAMES.get(name, app_name.title())
        executable = APP_ALIASES.get(name)

        if executable:
            if 'shell:AppsFolder' in executable:
                # UWP / Store apps — explorer is the only reliable launcher.
                # Using _safe_popen with full detachment prevents the
                # explorer window from inheriting our console.
                proc = _safe_popen(['explorer.exe', executable])
                if proc is None:
                    return f'Could not launch {display_name}. The app may not be installed.'
                return f'Opening {display_name}.'

            elif executable.endswith(':') or '://' in executable:
                # Protocol handler (whatsapp:, ms-settings:, https://...)
                if _safe_startfile(executable):
                    return f'Opening {display_name}.'
                return f'Could not open {display_name}.'

            else:
                # Direct executable path or short name
                proc = _safe_popen([executable])
                if proc is None:
                    # Fallback: try os.startfile which handles more edge cases
                    if _safe_startfile(executable):
                        return f'Opening {display_name}.'
                    return f'Could not find or launch {display_name}.'
                return f'Opening {display_name}.'

        else:
            # Unknown app — try os.startfile which delegates to Windows Shell
            if hasattr(os, 'startfile'):
                if _safe_startfile(name):
                    return f'Trying to open {display_name}.'

            # Last resort: check PATH
            import shutil
            resolved = shutil.which(name)
            if resolved:
                proc = _safe_popen([resolved])
                if proc:
                    return f'Trying to open {display_name}.'

            return f'Could not find {display_name}. You can add it to the config.'

    except Exception as e:
        logger.error('open_app failed: %s', e, exc_info=True)
        return f'Could not open {app_name}: {str(e)}'


def close_app(app_name: str) -> str:
    """Close an application by name (graceful → forced fallback)."""
    try:
        # ── Sanitise input ──
        safe_name = sanitise_app_name(app_name)
        if safe_name is None:
            return 'That application name looks invalid. Please try again.'

        name = safe_name.lower().strip()
        display_name = APP_PROPER_NAMES.get(name, app_name.title())

        # Determine the target process name
        exe_name = APP_PROCESS_MAP.get(name)

        if not exe_name:
            path_or_name = APP_ALIASES.get(name, f'{name}.exe')
            exe_name = os.path.basename(path_or_name)

            # Filter out protocol-style links
            if ':' in exe_name or '!' in exe_name or ' ' in exe_name:
                exe_name = f'{name}.exe'

        return _graceful_close(exe_name, display_name)

    except Exception as e:
        logger.error('close_app failed: %s', e, exc_info=True)
        return f'Could not close {app_name}: {str(e)}'


def close_active_window() -> str:
    """Close the currently active window using Alt+F4."""
    try:
        pyautogui.hotkey('alt', 'f4')
        return 'Attempted to close the active window.'
    except Exception as e:
        logger.error('close_active_window failed: %s', e)
        return f'Could not close active window: {str(e)}'


# ════════════════════════════════════════════════════════════════════
# Screenshots
# ════════════════════════════════════════════════════════════════════

def take_screenshot() -> str:
    """Take a screenshot and save to Desktop."""
    try:
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'screenshot_{timestamp}.png'
        filepath = os.path.join(desktop, filename)

        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)

        return f'Screenshot saved to your Desktop as {filename}.'
    except Exception as e:
        logger.error('take_screenshot failed: %s', e)
        return f'Could not take screenshot: {str(e)}'


# ════════════════════════════════════════════════════════════════════
# Time & Date
# ════════════════════════════════════════════════════════════════════

def get_time() -> str:
    """Get the current time."""
    try:
        now = datetime.datetime.now()
        time_str = now.strftime('%I:%M %p')
        return f'The current time is {time_str}.'
    except Exception as e:
        logger.error('get_time failed: %s', e)
        return f'Could not get the time: {str(e)}'


def get_date() -> str:
    """Get the current date."""
    try:
        now = datetime.datetime.now()
        date_str = now.strftime('%A, %B %d, %Y')
        return f'Today is {date_str}.'
    except Exception as e:
        logger.error('get_date failed: %s', e)
        return f'Could not get the date: {str(e)}'


# ════════════════════════════════════════════════════════════════════
# Power Management — REQUIRES CONFIRMATION (handled by router)
# ════════════════════════════════════════════════════════════════════

def shutdown_computer(delay: str = '60') -> str:
    """Schedule a shutdown with a delay in seconds."""
    try:
        seconds = int(delay)
        if seconds < 0:
            logger.error('Invalid shutdown delay: %d', seconds)
            return 'Delay must be a non-negative number.'
        subprocess.run(
            ['shutdown', '/s', '/t', str(seconds)],
            check=True,
            creationflags=CREATE_NO_WINDOW,
        )
        return f'Computer will shut down in {seconds} seconds.'
    except Exception as e:
        logger.error('shutdown failed: %s', e)
        return f'Could not schedule shutdown: {str(e)}'


def cancel_shutdown() -> str:
    """Cancel a scheduled shutdown."""
    try:
        subprocess.run(['shutdown', '/a'], check=True,
                       creationflags=CREATE_NO_WINDOW)
        return 'Shutdown cancelled.'
    except Exception as e:
        logger.error('cancel_shutdown failed: %s', e)
        return f'Could not cancel shutdown: {str(e)}'


def restart_computer(delay: str = '60') -> str:
    """Schedule a restart with a delay in seconds."""
    try:
        seconds = int(delay)
        if seconds < 0:
            logger.error('Invalid restart delay: %d', seconds)
            return 'Delay must be a non-negative number.'
        subprocess.run(
            ['shutdown', '/r', '/t', str(seconds)],
            check=True,
            creationflags=CREATE_NO_WINDOW,
        )
        return f'Computer will restart in {seconds} seconds.'
    except Exception as e:
        logger.error('restart failed: %s', e)
        return f'Could not schedule restart: {str(e)}'


def lock_screen() -> str:
    """Lock the computer screen."""
    try:
        # Use ctypes for more reliable lock (avoids subprocess window flash)
        ctypes.windll.user32.LockWorkStation()
        return 'Screen locked.'
    except Exception as e:
        logger.error('lock_screen failed: %s', e)
        return f'Could not lock screen: {str(e)}'


def empty_recycle_bin() -> str:
    """Empty the Windows Recycle Bin."""
    try:
        cmd = 'PowerShell Clear-RecycleBin -Force -Confirm:$false -ErrorAction SilentlyContinue'
        subprocess.run(cmd, shell=True, check=True,
                       creationflags=CREATE_NO_WINDOW)
        return 'Recycle bin emptied.'
    except Exception as e:
        logger.error('empty_recycle_bin failed: %s', e)
        return 'Could not empty the recycle bin. It might already be empty.'


# ════════════════════════════════════════════════════════════════════
# System Status
# ════════════════════════════════════════════════════════════════════

def get_system_status() -> str:
    """Get current CPU and RAM usage."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        return f'Your CPU usage is at {cpu} percent and your RAM usage is at {ram} percent.'
    except Exception as e:
        logger.error('get_system_status failed: %s', e)
        return f'Could not get system status: {str(e)}'


# ════════════════════════════════════════════════════════════════════
# Tool Registry
# ════════════════════════════════════════════════════════════════════

TOOLS = {
    'set_volume': set_volume,
    'get_volume': get_volume,
    'mute': mute,
    'unmute': unmute,
    'mute_toggle': mute_toggle,
    'media_play_pause': media_play_pause,
    'media_next': media_next,
    'media_previous': media_previous,
    'open_app': open_app,
    'close_app': close_app,
    'close_active_window': close_active_window,
    'take_screenshot': take_screenshot,
    'get_time': get_time,
    'get_date': get_date,
    'shutdown_computer': shutdown_computer,
    'cancel_shutdown': cancel_shutdown,
    'restart_computer': restart_computer,
    'lock_screen': lock_screen,
    'empty_recycle_bin': empty_recycle_bin,
    'get_system_status': get_system_status,
    'set_brightness': set_brightness,
    'get_brightness': get_brightness,
}
