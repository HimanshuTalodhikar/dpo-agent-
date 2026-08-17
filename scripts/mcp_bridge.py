#!/usr/bin/env python3
"""Stdio to HTTP JSON-RPC Bridge for DPDP Agent MCP Server."""

import sys
import json
import urllib.request
import urllib.error

ALB_URL = "http://cloagent-alb-896741255.ap-south-1.elb.amazonaws.com"

def log(msg: str):
    sys.stderr.write(f"[dpdp-bridge] {msg}\n")
    sys.stderr.flush()

def http_get(path: str) -> dict:
    url = f"{ALB_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "DPDP-MCP-Bridge/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log(f"HTTP GET Error {path}: {e}")
        return {}

def http_post(path: str, data: dict) -> dict:
    url = f"{ALB_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "DPDP-MCP-Bridge/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            return json.loads(err_body)
        except Exception:
            return {"success": False, "error": f"HTTP Error {e.code}"}
    except Exception as e:
        log(f"HTTP POST Error {path}: {e}")
        return {"success": False, "error": str(e)}

def main():
    log("DPDP Agent Stdio Bridge Started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as e:
            log(f"Invalid JSON: {e}")
            continue

        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "dpdp-agent", "version": "0.1.0"}
                }
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            try:
                data = http_get("/mcp/tools")
                tools = data.get("tools", [])
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": tools}
                }
            except Exception as e:
                log(f"Error fetching tools: {e}")
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": []}
                }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            try:
                result_data = http_post(f"/mcp/tools/{tool_name}/call", arguments)
                text_out = json.dumps(result_data, indent=2)
            except Exception as e:
                log(f"Error calling tool {tool_name}: {e}")
                text_out = json.dumps({"success": False, "tool": tool_name, "error": str(e)}, indent=2)

            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": text_out}
                    ]
                }
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        elif req_id is not None:
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
