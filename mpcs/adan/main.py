import base64
import csv
import stdlib
import jpyter
from threading import Thread
from typing import Any, Dict

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
stdlib.generators.register(mcp)
stdlib.storage.register(mcp)

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


if __name__ == "__main__":
    print(f"\n\n hello, friend. \n\n")
    mcp.run(transport="http", host="127.0.0.1", port=8000)