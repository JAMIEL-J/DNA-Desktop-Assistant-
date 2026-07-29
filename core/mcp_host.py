# core/mcp_host.py
# ──────────────────────────────────────────────────────────────────────
# MCP Subprocess Host — JSON-RPC 2.0 stdio runner for swappable tool servers
# ──────────────────────────────────────────────────────────────────────

import json
import logging
import subprocess
import sys
from typing import Any, Optional

logger = logging.getLogger("dna.mcp.host")

class MCPHost:
    """Manages an external MCP server process via JSON-RPC over stdio."""
    
    def __init__(self, command: list[str]):
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0

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

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def send_request(self, method: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Send a JSON-RPC 2.0 request to the subprocess and return the result."""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("MCP server process is not running.")

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
        if self.process and self.process.poll() is None:
            logger.info("Stopping MCP server process.")
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
