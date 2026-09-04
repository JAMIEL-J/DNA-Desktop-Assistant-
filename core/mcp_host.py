# core/mcp_host.py
# ──────────────────────────────────────────────────────────────────────
# MCP Subprocess Host — JSON-RPC 2.0 stdio runner for swappable tool servers
# ──────────────────────────────────────────────────────────────────────

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
from typing import Any, Optional

logger = logging.getLogger("dna.mcp.host")

class MCPHost:
    """Manages an external MCP server process via JSON-RPC over stdio."""

    def __init__(self, command: list[str]):
        self.command = self._resolve_command(command)
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._connected = False

    @staticmethod
    def _resolve_command(command: list[str]) -> list[str]:
        """Resolve bare tool names (npx/npm/node) on Windows where Popen
        needs the full `npx.cmd` path (bare `npx` raises FileNotFoundError)."""
        if not command:
            return command
        if os.name == "nt" and command[0].lower() in ("npx", "npm", "node"):
            resolved = shutil.which(command[0])
            if resolved:
                return [resolved] + list(command[1:])
            logger.warning("Could not resolve %s on PATH; launch may fail.", command[0])
        return list(command)

    def start(self) -> None:
        """Start the MCP server subprocess."""
        try:
            logger.info("Starting MCP server process: %s", self.command)
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except Exception as e:
            logger.error("Failed to start MCP server: %s", e)
            raise RuntimeError(f"MCP server launch failed: {e}")

    @property
    def is_running(self) -> bool:
        """True while the server subprocess is alive."""
        return bool(self.process and self.process.poll() is None)

    def __enter__(self) -> "MCPHost":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def connect(self) -> dict[str, Any]:
        """Start (if needed) + MCP initialize handshake.

        Tolerant of simple servers (e.g. mcp/sample_server.py) that do not
        implement `initialize`: falls back to unconnected mode and skips the
        `notifications/initialized` notice so no stale reply poisons the
        stream for the next request.
        """
        if not self.is_running:
            self.start()
        if self._connected:
            return {}
        try:
            info = self.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "dna-mcp-host", "version": "1.0"},
            })
            self._connected = True
            try:
                self.send_notification("notifications/initialized")
            except Exception as e:
                logger.debug("initialized notification failed (ignored): %s", e)
            return info
        except RuntimeError as e:
            if "Method 'initialize' not found" in str(e) or "-32601" in str(e):
                logger.debug("Server has no initialize handshake; using plain JSON-RPC.")
                self._connected = False
                return {}
            raise

    def ensure_connected(self) -> None:
        """Connect if not already connected. Safe to call repeatedly."""
        if not self._connected:
            self.connect()

    def send_notification(self, method: str, params: Optional[dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        if not self.is_running:
            raise RuntimeError("MCP server process is not running.")
        assert self.process is not None and self.process.stdin is not None
        with self._lock:
            self.process.stdin.write(json.dumps({
                "jsonrpc": "2.0", "method": method, "params": params or {},
            }) + "\n")
            self.process.stdin.flush()

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def send_request(self, method: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Send a JSON-RPC 2.0 request to the subprocess and return the result."""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("MCP server process is not running.")

        with self._lock:
            req_id = self._next_id()
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params or {}
            }

            json_str = json.dumps(payload) + "\n"
            assert self.process.stdin is not None
            self.process.stdin.write(json_str)
            self.process.stdin.flush()

            assert self.process.stdout is not None
            response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("MCP server closed stream unexpectedly.")

        try:
            resp = json.loads(response_line.strip())
            if "error" in resp:
                raise RuntimeError(f"MCP JSON-RPC Error: {resp['error']}")
            return resp.get("result", {})
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse MCP response: {response_line.strip()} | Error: {e}")

    def list_tools(self) -> list[dict[str, Any]]:
        """Query available tools from the MCP server."""
        res = self.send_request("tools/list")
        return res.get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a tool on the MCP server."""
        res = self.send_request("tools/call", {"name": name, "arguments": arguments})
        return res.get("content", res)

    def stop(self) -> None:
        """Terminate the MCP server process."""
        self._connected = False
        if self.process and self.process.poll() is None:
            logger.info("Stopping MCP server process.")
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
