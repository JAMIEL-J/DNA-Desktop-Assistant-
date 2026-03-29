# 1. stdlib
import datetime
import logging
import os
import subprocess

# 2. third-party
import pyautogui

# 3. internal
from config import APP_ALIASES

logger = logging.getLogger('dna.skill.system')


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


def set_brightness(level: str) -> str:
    """Set screen brightness (0-100)."""
    try:
        target = int(level)
        if target < 0 or target > 100:
            return 'Brightness must be between 0 and 100.'

        # Use PowerShell to set brightness
        cmd = f'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {target})"'
        subprocess.run(cmd, shell=True, check=True)
        return f'Brightness set to {target} percent.'
    except Exception as e:
        logger.error('set_brightness failed: %s', e)
        return f'Could not set brightness: {str(e)}'


def get_brightness() -> str:
    """Get current screen brightness level."""
    try:
        # Use PowerShell to get brightness
        cmd = 'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        current = int(result.stdout.strip())
        return f'Brightness is at {current} percent.'
    except Exception as e:
        logger.error('get_brightness failed: %s', e)
        return f'Could not get brightness: {str(e)}'


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


def open_app(app_name: str) -> str:
    """Open an application by name."""
    try:
        import re
        name = app_name.lower().strip()
        if re.search(r'[&|;<>\'"]', name):
            return "Application name contains invalid characters."

        executable = APP_ALIASES.get(name)

        if executable:
            if hasattr(os, 'startfile'):
                os.startfile(executable)
            else:
                subprocess.Popen(
                    [executable],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            return f'Opening {app_name}.'
        else:
            # Try opening via Windows search / start menu
            if hasattr(os, 'startfile'):
                os.startfile(name)
            else:
                import shutil
                resolved = shutil.which(name)
                if resolved:
                    subprocess.Popen(
                        [resolved],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            return f'Trying to open {app_name}.'

    except Exception as e:
        logger.error('open_app failed: %s', e)
        return f'Could not open {app_name}: {str(e)}'


def close_app(app_name: str) -> str:
    """Close an application by name."""
    try:
        name = app_name.lower().strip()
        # Use taskkill to close the process
        exe = APP_ALIASES.get(name, f'{name}.exe')
        if '\\' in exe:
            exe = os.path.basename(exe)
        subprocess.run(
            ['taskkill', '/IM', exe, '/F'],
            capture_output=True,
            check=False,
        )
        return f'Closed {app_name}.'
    except Exception as e:
        logger.error('close_app failed: %s', e)
        return f'Could not close {app_name}: {str(e)}'


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
        )
        return f'Computer will shut down in {seconds} seconds.'
    except Exception as e:
        logger.error('shutdown failed: %s', e)
        return f'Could not schedule shutdown: {str(e)}'


def cancel_shutdown() -> str:
    """Cancel a scheduled shutdown."""
    try:
        subprocess.run(['shutdown', '/a'], check=True)
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
        )
        return f'Computer will restart in {seconds} seconds.'
    except Exception as e:
        logger.error('restart failed: %s', e)
        return f'Could not schedule restart: {str(e)}'


def lock_screen() -> str:
    """Lock the computer screen."""
    try:
        subprocess.run(
            ['rundll32.exe', 'user32.dll,LockWorkStation'],
            check=True,
        )
        return 'Screen locked.'
    except Exception as e:
        logger.error('lock_screen failed: %s', e)
        return f'Could not lock screen: {str(e)}'

def empty_recycle_bin() -> str:
    """Empty the Windows Recycle Bin."""
    try:
        # Use PowerShell to empty the bin
        cmd = 'PowerShell Clear-RecycleBin -Force -Confirm:$false -ErrorAction SilentlyContinue'
        subprocess.run(cmd, shell=True, check=True)
        return 'Recycle bin emptied.'
    except Exception as e:
        logger.error('empty_recycle_bin failed: %s', e)
        return 'Could not empty the recycle bin. It might already be empty.'


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


# Skill module contract: expose all tools via TOOLS dict
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
