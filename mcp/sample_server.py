# mcp/sample_server.py
# ──────────────────────────────────────────────────────────────────────
# Sample stdio MCP Server for testing JSON-RPC tool host
# ──────────────────────────────────────────────────────────────────────

import json
import sys

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line.strip())
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "echo_tool",
                                "description": "Echoes back input text",
                                "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}
                            }
                        ]
                    }
                }
            elif method == "tools/call":
                name = params.get("name")
                args = params.get("arguments", {})
                if name == "echo_tool":
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"content": f"Echo: {args.get('text', '')}"}
                    }
                else:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Tool '{name}' not found"}
                    }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method '{method}' not found"}
                }

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Server error: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
