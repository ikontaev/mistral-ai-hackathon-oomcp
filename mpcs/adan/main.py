import base64
import csv
import stdlib
from threading import Thread
from typing import Any, Dict
from fastmcp import Client
import asyncio
import os

from fastmcp import FastMCP

mcp = FastMCP("OOMCP")

# Determine root path based on environment
if os.environ.get('DOCKER_ENV'):
    # Running in Docker container
    CONFIG = {
        "root_path": "/app",
        "space_path": "/app/spaces/random",
        "children": []
    }
else:
    # Running locally
    CONFIG = {
        "root_path": "../..",
        "space_path": "../../spaces/random",
        "children": []
    }
# Create space directory if it doesn't exist
os.makedirs(CONFIG["space_path"], exist_ok=True)
print(f"Using space path: {CONFIG['space_path']}")

# load std_lib
stdlib.hetzner.register(mcp, CONFIG)
stdlib.fs.register(mcp, CONFIG)
stdlib.jpter.register(mcp, CONFIG)
stdlib.net.register(mcp, CONFIG)
stdlib.python.register(mcp, CONFIG)
stdlib.os.register(mcp, CONFIG)
stdlib.generators.register(mcp, CONFIG)
stdlib.storage.register(mcp, CONFIG)
stdlib.comms.register(mcp, CONFIG)

JUPYTER_TOKEN = os.environ.get("JUPYTER_TOKEN", "")

@mcp.tool
def jupyter_iframe() -> str:
    """Return an iframe for JupyterHub embedded view"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JupyterHub Embedded View</title>
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
        }}
        .iframe-container {{
            width: 100%;
            height: 100vh;
            border: none;
        }}
    </style>
</head>
<body>
    <iframe
        class="iframe-container"
        src="https://jupyter.ethux.net/login?token={JUPYTER_TOKEN}"
        allowfullscreen>
    </iframe>
</body>
</html>"""

@mcp.tool
def hello(name: str) -> str:
    """Say hello - basic connectivity test"""
    return f"Hello, friend."

@mcp.tool
def read_csv(csv_content_base64: str, max_preview_rows: int = 5) -> str:
    """Analyze CSV data from base64-encoded CSV content and return a summary"""
    if not csv_content_base64 or not isinstance(csv_content_base64, str):
        return "Error: provide a base64 encoded CSV content string."

    try:
        csv_content = base64.b64decode(csv_content_base64).decode("utf-8")
    except Exception as e:
        return f"Error decoding base64: {e}"

    try:
        from io import StringIO

        f = StringIO(csv_content)
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return "CSV is empty."

        preview = []
        for i, row in enumerate(reader):
            if i >= max_preview_rows:
                break
            # ensure same length as header
            if len(row) < len(header):
                row += [""] * (len(header) - len(row))
            preview.append(row)

    except Exception as e:
        return f"Error reading CSV: {e}"

    lines = []
    lines.append("CSV Analysis Summary")
    lines.append(f"Columns ({len(header)}): {', '.join(header)}")
    lines.append(f"Preview ({len(preview)} rows):")
    lines.append(", ".join(header))
    for r in preview:
        lines.append(", ".join(r))
    return "\n".join(lines)

async def list_tools():
    """List all available tools using FastMCP client"""
    try:
        async with Client("http://localhost:8000/mcp") as client:
            tools = await client.list_tools()
            print("\nAvailable MCP Tools:")
            for tool in tools:
                # Access tool properties directly
                print(f"  - {tool.name}: {tool.description}")
                print(f"    Schema: {tool.schema}")
            return tools
    except Exception as e:
        print(f"Error listing tools: {e}")
        return []

def run_server():
    """Run the MCP server"""
    mcp.run(transport="http", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    print(f"\n\n hello, friend. \n\n")
    print(f"Using space path: {CONFIG['space_path']}")

    # Start server in a separate thread
    import threading
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give server time to start
    import time
    time.sleep(2)

    # List available tools
    asyncio.run(list_tools())

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServer stopped")