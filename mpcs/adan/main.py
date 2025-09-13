import base64
import csv
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import sys
import stdlib
import jpyter
from threading import Thread
from typing import Any, Dict

import httpx
from fastmcp import FastMCP

mcp = FastMCP("OOMCP")

# map of spaces 
CONFIG = {
    "children": []
}

# load std_lib
stdlib.fs.register(mcp)
stdlib.net.register(mcp)
stdlib.python.register(mcp)
stdlib.os.register(mcp)
jpyter.jupyter.register(mcp)


@mcp.tool
def hello(name: str) -> str:
    """Say hello - basic connectivity test"""
    return f"Hello, friend."

@mcp.tool
def generate_html(title: str, body: str, name: str) -> str:
    """Generate a simple HTML file based on title and body content inside a template and it writes to filesystem with
    params:
    title: str
    body: str
    name: str (without .html extension)
    """
    try:
        html_content = f"""<!DOCTYPE html>
<html lang="en"> 
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body>
    {body}
</body>
</html>"""
        with open(f"{name}.html", "w") as f:
            f.write(html_content)
        return f"{name}.html"
    except Exception as e:
        return f"❌ Error generating HTML: {str(e)}"
    




@mcp.tool
def fetch(url: str, method: str = "GET", headers: str = None, data: str = None) -> str:
    """Fetch data from a URL using httpx - returns response as text"""
    try:
        request_headers = {}
        if headers:
            try:
                request_headers = json.loads(headers)
            except json.JSONDecodeError:
                return "❌ Error: headers must be valid JSON string"

        request_data = None
        if data:
            request_data = data

        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method=method.upper(),
                url=url,
                headers=request_headers,
                content=request_data,
            )

        content = response.text
        result = {
            "status": response.status_code,
            "headers": dict(response.headers),
            "content": content,
            "content_length": len(content),
        }

        return json.dumps(result, indent=2)

    except httpx.HTTPError as e:
        return f"❌ HTTP Error: {str(e)}"
    except Exception as e:
        return f"❌ Error fetching URL: {str(e)}"


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


if __name__ == "__main__":
    print(f"\n\n hello, friend. \n\n")
    mcp.run(transport="http", host="127.0.0.1", port=8000)