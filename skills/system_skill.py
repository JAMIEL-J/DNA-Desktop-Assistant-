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
from core.session import update as session_update, get as session_get
from pipeline.memory import get_aliases

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

    CRITICAL: explorer.exe is NEVER killed via taskkill because it IS the
    Windows desktop shell.  Killing it nukes the taskbar, Start menu, and
    desktop icons — causing a black screen.  Explorer folder windows are
    closed through the dedicated _close_explorer_windows() helper instead.
    """
    # ── Guard: NEVER taskkill explorer.exe ──
    if exe_name.lower() == 'explorer.exe':
        return _close_explorer_windows(display_name)

    # Step 1: Graceful close (sends WM_CLOSE to all windows of the process)
    result = subprocess.run(
        ['taskkill', '/IM', exe_name, '/T'],
        capture_output=True, text=True, check=False,
        creationflags=CREATE_NO_WINDOW,
    )

    if result.returncode == 0:
        logger.info('Gracefully closed %s', exe_name)
        if session_get('active_app') == display_name:
            session_update('active_app', None)
        return 'Alright, closed it.'

    # Step 2: If graceful close failed, wait briefly then force-kill
    time.sleep(1.0)

    result = subprocess.run(
        ['taskkill', '/IM', exe_name, '/F', '/T'],
        capture_output=True, text=True, check=False,
        creationflags=CREATE_NO_WINDOW,
    )

    if result.returncode == 0:
        logger.info('Force-killed %s', exe_name)
        if session_get('active_app') == display_name:
            session_update('active_app', None)
        return 'Done, closed it.'

    # Step 3: Check if process is actually not running
    err_msg = (result.stderr or '').strip().lower()
    if 'not found' in err_msg or result.returncode == 128:
        return 'It\'s not even running.'

    logger.warning('taskkill failed for %s (rc=%d): %s',
                   exe_name, result.returncode, result.stderr)
    return f'Could not close {display_name}. It may require manual closing.'


# ── Explorer-safe window closing ──────────────────────────────────
# Uses the Shell.Application COM object to enumerate ONLY File Explorer
# folder windows, then closes them individually without touching the
# desktop shell process.

def _close_explorer_windows(display_name: str = 'File Explorer') -> str:
    """Close all File Explorer folder windows WITHOUT killing the shell.

    Uses Shell.Application COM to iterate open Explorer windows and
    close each one via .Quit().  The desktop shell (taskbar, Start menu,
    desktop icons) is *not* an Explorer window in this API, so it
    remains untouched.

    Returns a human-readable result string.
    """
    try:
        import comtypes.client  # noqa: F811

        shell = comtypes.client.CreateObject('Shell.Application')
        windows = shell.Windows()
        count = windows.Count

        if count == 0:
            return f'{display_name} has no open folder windows.'

        closed = 0
        # Iterate in reverse so closing doesn't shift indices
        for i in range(count - 1, -1, -1):
            try:
                win = windows.Item(i)
                if win is None:
                    continue
                win.Quit()
                closed += 1
            except Exception:
                # Some windows may refuse; skip them
                continue

        if closed == 0:
            return f'There aren\'t any open {display_name} windows.'
        elif closed == 1:
            return f'Closed 1 {display_name} window.'
        else:
            return f'Alright, closed {closed} {display_name} windows.'

    except ImportError:
        # comtypes not installed — fall back to pyautogui Alt+F4 approach
        logger.warning('comtypes not available, trying PowerShell COM fallback')
        return _close_explorer_windows_ps(display_name)
    except Exception as e:
        logger.error('COM-based explorer close failed: %s', e)
        return _close_explorer_windows_ps(display_name)


def _close_explorer_windows_ps(display_name: str = 'File Explorer') -> str:
    """PowerShell fallback: close Explorer folder windows via COM script.

    This is used when comtypes is not installed.  The PowerShell one-liner
    achieves the same safe behaviour: enumerate Shell.Application.Windows()
    and call Quit() on each, without touching the desktop shell.
    """
    try:
        ps_script = (
            '(New-Object -ComObject Shell.Application).Windows() '
            '| ForEach-Object { $_.Quit() }'
        )
        result = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_script],
            capture_output=True, text=True, check=False,
            creationflags=CREATE_NO_WINDOW,
            timeout=10,
        )

        if result.returncode == 0:
            logger.info('Closed Explorer windows via PowerShell COM fallback')
            return f'Closed {display_name} windows.'

        logger.warning('PS fallback returned rc=%d: %s', result.returncode, result.stderr)
        return f'Could not close {display_name}. Try closing it manually.'

    except subprocess.TimeoutExpired:
        logger.error('PowerShell COM fallback timed out')
        return f'Timed out trying to close {display_name}.'
    except Exception as e:
        logger.error('PowerShell COM fallback failed: %s', e)
        return f'Could not close {display_name}: {str(e)}'


def _recover_explorer_shell() -> str:
    """Emergency: restart the Windows shell if it was accidentally killed.

    This is a safety net — it starts a new explorer.exe process which
    Windows automatically recognises as the shell restart.  The taskbar,
    Start menu, and desktop icons will reappear.
    """
    try:
        _safe_popen(['explorer.exe'])
        logger.info('Explorer shell recovery launched')
        return 'Alright, I\'ve restored the taskbar.'
    except Exception as e:
        logger.error('Shell recovery failed: %s', e)
        return f'Could not restart the Windows shell: {str(e)}'


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

        return f'Alright, volume set to {target} percent.'
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

        return f'Volume\'s at {current} percent right now.'
    except Exception as e:
        logger.error('get_volume failed: %s', e)
        return f'Could not get volume: {str(e)}'


def volume_up() -> str:
    """Increase volume by 10 percent."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        vol = device.EndpointVolume
        current = vol.GetMasterVolumeLevelScalar()
        new_level = min(1.0, current + 0.1)
        vol.SetMasterVolumeLevelScalar(new_level, None)
        return f'Sure, turning it up to {round(new_level * 100)} percent.'
    except Exception as e:
        return f'Could not increase volume: {str(e)}'


def volume_down() -> str:
    """Decrease volume by 10 percent."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        vol = device.EndpointVolume
        current = vol.GetMasterVolumeLevelScalar()
        new_level = max(0.0, current - 0.1)
        vol.SetMasterVolumeLevelScalar(new_level, None)
        return f'Alright, turning it down to {round(new_level * 100)} percent.'
    except Exception as e:
        return f'Could not decrease volume: {str(e)}'


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
        return 'Sure, brightness adjusted.'
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


def brightness_up() -> str:
    """Increase brightness by 10 percent."""
    try:
        cmd_get = 'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"'
        result = subprocess.run(cmd_get, shell=True, capture_output=True, text=True,
                                check=True, creationflags=CREATE_NO_WINDOW)
        current = int(result.stdout.strip() if result.stdout.strip() else '50')
        new_level = min(100, current + 10)
        cmd_set = f'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {new_level})"'
        subprocess.run(cmd_set, shell=True, check=True,
                       creationflags=CREATE_NO_WINDOW)
        return f'Setting brightness up to {new_level} percent.'
    except Exception:
        return 'Could not increase brightness.'


def brightness_down() -> str:
    """Decrease brightness by 10 percent."""
    try:
        cmd_get = 'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"'
        result = subprocess.run(cmd_get, shell=True, capture_output=True, text=True,
                                check=True, creationflags=CREATE_NO_WINDOW)
        current = int(result.stdout.strip() if result.stdout.strip() else '50')
        new_level = max(0, current - 10)
        cmd_set = f'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {new_level})"'
        subprocess.run(cmd_set, shell=True, check=True,
                       creationflags=CREATE_NO_WINDOW)
        return f'Dimming it down to {new_level} percent.'
    except Exception:
        return 'Could not decrease brightness.'


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

        state = 'Alright, muted.' if not current_mute else 'Sure, unmuted.'
        return state
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
        return 'Got it, muting the sound.'
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
        return 'Sound\'s back on.'
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
        return 'Alright, toggled play-pause.'
    except Exception as e:
        logger.error('media_play_pause failed: %s', e)
        return f'Could not toggle play pause: {str(e)}'


def media_next() -> str:
    """Skip to next media track."""
    try:
        pyautogui.press('nexttrack')
        return 'Skipping forward.'
    except Exception as e:
        logger.error('media_next failed: %s', e)
        return f'Could not skip track: {str(e)}'


def media_previous() -> str:
    """Go to previous media track."""
    try:
        pyautogui.press('prevtrack')
        return 'Alright, going back a track.'
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
        db_aliases = get_aliases()
        executable = db_aliases.get(name) or APP_ALIASES.get(name)

        if executable:
            if 'shell:AppsFolder' in executable:
                # UWP / Store apps — explorer is the only reliable launcher.
                # Using _safe_popen with full detachment prevents the
                # explorer window from inheriting our console.
                proc = _safe_popen(['explorer.exe', executable])
                if proc is None:
                    return f'It looks like {display_name} isn\'t installed.'
                session_update('active_app', display_name)
                return f'Opening up {display_name} for you.'

            elif executable.endswith(':') or '://' in executable:
                # Protocol handler (whatsapp:, ms-settings:, https://...)
                if _safe_startfile(executable):
                    session_update('active_app', display_name)
                    return f'Opening {display_name}.'
                return f'Could not open {display_name}.'

            else:
                # Direct executable path or short name
                proc = _safe_popen([executable])
                if proc is None:
                    # Fallback: try os.startfile which handles more edge cases
                    if _safe_startfile(executable):
                        session_update('active_app', display_name)
                        return f'Opening {display_name}.'
                    return f'Could not find or launch {display_name}.'
                session_update('active_app', display_name)
                return f'Opening {display_name}.'

        else:
            # Unknown app — try os.startfile which delegates to Windows Shell
            if hasattr(os, 'startfile'):
                if _safe_startfile(name):
                    session_update('active_app', display_name)
                    return f'Trying to open {display_name}.'

            # Last resort: check PATH
            import shutil
            resolved = shutil.which(name)
            if resolved:
                proc = _safe_popen([resolved])
                if proc:
                    session_update('active_app', display_name)
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
            db_aliases = get_aliases()
            path_or_name = db_aliases.get(name) or APP_ALIASES.get(name, f'{name}.exe')
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
        session_update('active_app', None)
        return 'Sure, closing the window.'
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
        # Fallback if Desktop doesn't exist
        if not os.path.exists(desktop):
            desktop = os.path.join(os.path.dirname(os.path.dirname(__file__)))
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'screenshot_{timestamp}.png'
        filepath = os.path.join(desktop, filename)

        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        
        if os.path.exists(filepath):
            logger.info('Screenshot saved to: %s', filepath)
            return f'Got it! Screenshot saved to your desktop as {filename}.'
        else:
            return 'Hmm, something went wrong. The screenshot did not save.'
    except Exception as e:
        logger.error('take_screenshot failed: %s', e)
        return 'Sorry, I had trouble capturing the screen.'


# ════════════════════════════════════════════════════════════════════
# Time & Date
# ════════════════════════════════════════════════════════════════════

def get_time() -> str:
    """Get the current time."""
    try:
        now = datetime.datetime.now()
        time_str = now.strftime('%I:%M %p')
        return f'It\'s {time_str}.'
    except Exception as e:
        logger.error('get_time failed: %s', e)
        return f'Could not get the time: {str(e)}'


def get_date() -> str:
    """Get the current date."""
    try:
        now = datetime.datetime.now()
        date_str = now.strftime('%A, %B %d')
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
        return 'Alright, shutdown cancelled.'
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
        return 'Got it, screen locked.'
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
        return f'CPU\'s at {cpu} percent, RAM\'s at {ram}.'
    except Exception as e:
        logger.error('get_system_status failed: %s', e)
        return f'Could not get system status: {str(e)}'


# ════════════════════════════════════════════════════════════════════
# Tool Registry
# ════════════════════════════════════════════════════════════════════

TOOLS = {
    'set_volume': set_volume,
    'get_volume': get_volume,
    'volume_up': volume_up,
    'volume_down': volume_down,
    'mute': mute,
    'unmute': unmute,
    'mute_toggle': mute_toggle,
    'media_play_pause': media_play_pause,
    'media_next': media_next,
    'media_previous': media_previous,
    'open_app': open_app,
    'close_app': close_app,
    'close_active_window': close_active_window,
    'close_explorer_windows': _close_explorer_windows,
    'recover_explorer_shell': _recover_explorer_shell,
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
    'brightness_up': brightness_up,
    'brightness_down': brightness_down,
}
