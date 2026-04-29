import asyncio
import json
import logging
import sys
import threading
import webbrowser
from pathlib import Path

import psutil
from core.session import snapshot as session_snapshot

logger = logging.getLogger('dna.ui.window')


class _WebSocketHub:
    def __init__(self, host: str = '127.0.0.1', port: int = 8765) -> None:
        self._host = host
        self._port = port
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name='DNAWebSocket', daemon=True)
        self._clients: set = set()
        self._lock = threading.Lock()
        self._server = None

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            import websockets
        except Exception as exc:
            logger.error('websockets is required for the live UI: %s', exc)
            return

        async def handler(websocket):
            with self._lock:
                self._clients.add(websocket)
            try:
                await websocket.wait_closed()
            finally:
                with self._lock:
                    self._clients.discard(websocket)

        async def start_server() -> None:
            self._server = await websockets.serve(handler, self._host, self._port)
            logger.info('WebSocket UI bridge listening on ws://%s:%s', self._host, self._port)

        self._loop.create_task(start_server())
        self._loop.run_forever()

    async def _broadcast(self, payload: dict) -> None:
        if not self._clients:
            return
        message = json.dumps(payload)
        dead = []
        for ws in list(self._clients):
            try:
                await ws.send(message)
            except Exception:
                dead.append(ws)
        if dead:
            with self._lock:
                for ws in dead:
                    self._clients.discard(ws)

    def broadcast(self, payload: dict) -> None:
        if not self._loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)


class AssistantWebWindow:
    def __init__(self, hub: _WebSocketHub):
        self._hub = hub
        self._last_state = None
        self._last_command = None
        self._last_result = None
        self._last_audio_level = None
        self._proc_primed = False
        self._running = False
        self._html_path = Path(__file__).resolve().parent / 'dna_ui.html'

    def start(self):
        self._running = True
        logger.info('Opening DNA UI in default browser...')
        webbrowser.open(f'file://{self._html_path.absolute()}')
        
        self._state_thread = threading.Thread(target=self._state_loop, daemon=True)
        self._metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        self._state_thread.start()
        self._metrics_thread.start()

    def stop(self):
        self._running = False

    def _state_loop(self):
        import time
        while self._running:
            try:
                self._push_state()
            except Exception:
                pass
            time.sleep(0.12)

    def _metrics_loop(self):
        import time
        while self._running:
            try:
                self._push_metrics()
            except Exception:
                pass
            time.sleep(2.0)

    def _snapshot(self) -> dict:
        return session_snapshot()

    def _map_state(self, snap: dict) -> str:
        assistant_state = str(snap.get('assistant_state') or 'sleeping').lower()
        is_speaking = bool(snap.get('is_speaking'))
        if assistant_state == 'sleeping':
            return 'sleeping'
        if assistant_state == 'processing':
            return 'processing'
        return 'speaking' if is_speaking else 'listening'

    def _push_state(self) -> None:
        snap = self._snapshot()
        state = self._map_state(snap)
        if state != self._last_state:
            self._hub.broadcast({'type': 'state', 'state': state})
            self._last_state = state

        command = str(snap.get('last_command') or '').strip()
        if command and command != self._last_command:
            self._hub.broadcast({'type': 'stt', 'text': command})
            self._last_command = command

        result = str(snap.get('last_result') or '').strip()
        if result and result != self._last_result:
            self._hub.broadcast({'type': 'tts', 'text': result})
            self._last_result = result

        audio_level = float(snap.get('mic_level') or 0.0)
        audio_level = max(0.0, min(1.0, audio_level))
        if self._last_audio_level is None or abs(audio_level - self._last_audio_level) > 0.02:
            self._hub.broadcast({'type': 'audio_level', 'level': audio_level})
            self._last_audio_level = audio_level

    def _push_metrics(self) -> None:
        metrics = self._collect_metrics()
        if metrics:
            self._hub.broadcast(metrics)

    def _collect_metrics(self) -> dict | None:
        if not self._proc_primed:
            for proc in psutil.process_iter():
                try:
                    proc.cpu_percent(None)
                except Exception:
                    continue
            psutil.cpu_percent(None)
            self._proc_primed = True
            return None

        cpu = psutil.cpu_percent(None)
        mem = psutil.virtual_memory()
        ram_gb = mem.used / (1024 ** 3)

        processes = []
        for proc in psutil.process_iter(['name', 'cpu_percent']):
            try:
                name = proc.info.get('name') or 'unknown'
                cpu_pct = float(proc.info.get('cpu_percent') or 0.0)
                processes.append((cpu_pct, name))
            except Exception:
                continue

        processes.sort(reverse=True)
        top = processes[:3]
        apps = [
            {'name': name, 'cpu': round(cpu_pct, 1)}
            for cpu_pct, name in top
        ]

        return {
            'type': 'metrics',
            'cpu': round(cpu, 1),
            'ram': round(ram_gb, 2),
            'latency_ms': None,
            'apps': apps,
            'total_apps': len(psutil.pids()),
        }


def run_assistant_window() -> bool:
    """Run the PySide6 Web UI event loop. Returns False if PySide6 is unavailable."""
    logger.info('Starting Web UI Hub...')
    hub = _WebSocketHub()
    hub.start()

    window = AssistantWebWindow(hub)
    window.start()

    try:
        import time
        from core.session import get as session_get
        while session_get('is_running', True):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        window.stop()
        
    return True
