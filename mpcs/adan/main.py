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
from threading import Thread
from typing import Any, Dict

from fastmcp import FastMCP

mcp = FastMCP("OOMCP")

# Working directory state
current_working_dir = os.getcwd()


@mcp.tool
def hello(name: str) -> str:
    """Say hello - basic connectivity test"""
    return f"Hello, {name}! OOMCP is running and ready."


@mcp.tool
def run_python(code: str, cwd: str = None) -> str:
    """Execute python code and return the output"""
    import contextlib
    import io
    import traceback

    # Change to specified directory if provided
    original_cwd = os.getcwd()
    if cwd:
        try:
            os.chdir(cwd)
        except Exception as e:
            return f"❌ Error changing directory: {str(e)}"

    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            # Create a more complete execution environment
            exec_env = {
                "__builtins__": __builtins__,
                "os": os,
                "sys": sys,
                "json": json,
                "Path": Path,
            }
            exec(code, exec_env)
        result = buffer.getvalue()
        return result or "✔️ Code executed successfully (no output)."
    except Exception:
        return "❌ Error:\n" + traceback.format_exc()
    finally:
        # Restore original directory
        os.chdir(original_cwd)


@mcp.tool
def run_shell(command: str, cwd: str = None) -> str:
    """Execute shell command and return output"""
    try:
        work_dir = cwd or current_working_dir
        result = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = f"Exit code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output
    except subprocess.TimeoutExpired:
        return "❌ Command timed out (30s limit)"
    except Exception as e:
        return f"❌ Error executing command: {str(e)}"


@mcp.tool
def create_file(filepath: str, content: str) -> str:
    """Create a new file with specified content"""
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✔️ File created: {filepath}"
    except Exception as e:
        return f"❌ Error creating file: {str(e)}"


@mcp.tool
def read_file(filepath: str) -> str:
    """Read content from a file"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return f"📄 Content of {filepath}:\n{content}"
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"


@mcp.tool
def append_to_file(filepath: str, content: str) -> str:
    """Append content to an existing file"""
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(content)
        return f"✔️ Content appended to: {filepath}"
    except Exception as e:
        return f"❌ Error appending to file: {str(e)}"


@mcp.tool
def delete_file(filepath: str) -> str:
    """Delete a file"""
    try:
        os.remove(filepath)
        return f"✔️ File deleted: {filepath}"
    except Exception as e:
        return f"❌ Error deleting file: {str(e)}"


@mcp.tool
def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List files in a directory with optional pattern matching"""
    try:
        path = Path(directory)
        if not path.exists():
            return f"❌ Directory does not exist: {directory}"

        files = []
        for item in glob.glob(os.path.join(directory, pattern)):
            item_path = Path(item)
            if item_path.is_file():
                size = item_path.stat().st_size
                files.append(f"📄 {item_path.name} ({size} bytes)")
            elif item_path.is_dir():
                files.append(f"📁 {item_path.name}/")

        if not files:
            return f"📂 No files found in {directory} matching '{pattern}'"

        return f"📂 Files in {directory}:\n" + "\n".join(files)
    except Exception as e:
        return f"❌ Error listing files: {str(e)}"


@mcp.tool
def create_directory(directory: str) -> str:
    """Create a new directory"""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return f"✔️ Directory created: {directory}"
    except Exception as e:
        return f"❌ Error creating directory: {str(e)}"


@mcp.tool
def change_directory(directory: str) -> str:
    """Change the current working directory"""
    global current_working_dir
    try:
        os.chdir(directory)
        current_working_dir = os.getcwd()
        return f"✔️ Changed to directory: {current_working_dir}"
    except Exception as e:
        return f"❌ Error changing directory: {str(e)}"


@mcp.tool
def get_current_directory() -> str:
    """Get the current working directory"""
    return f"📍 Current directory: {os.getcwd()}"


@mcp.tool
def copy_file(source: str, destination: str) -> str:
    """Copy a file from source to destination"""
    try:
        shutil.copy2(source, destination)
        return f"✔️ File copied from {source} to {destination}"
    except Exception as e:
        return f"❌ Error copying file: {str(e)}"


@mcp.tool
def move_file(source: str, destination: str) -> str:
    """Move/rename a file from source to destination"""
    try:
        shutil.move(source, destination)
        return f"✔️ File moved from {source} to {destination}"
    except Exception as e:
        return f"❌ Error moving file: {str(e)}"


@mcp.tool
def install_package(package: str) -> str:
    """Install a Python package using pip"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return f"✔️ Package installed: {package}\n{result.stdout}"
        else:
            return f"❌ Failed to install {package}:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return f"❌ Package installation timed out: {package}"
    except Exception as e:
        return f"❌ Error installing package: {str(e)}"


@mcp.tool
def list_packages() -> str:
    """List installed Python packages"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list"], capture_output=True, text=True
        )
        return f"📦 Installed packages:\n{result.stdout}"
    except Exception as e:
        return f"❌ Error listing packages: {str(e)}"


@mcp.tool
def get_system_info() -> str:
    """Get system information"""
    import platform

    info = {
        "Platform": platform.platform(),
        "Python Version": platform.python_version(),
        "Architecture": platform.architecture()[0],
        "Machine": platform.machine(),
        "Current Directory": os.getcwd(),
        "Environment Variables": len(os.environ),
    }
    return "🖥️ System Information:\n" + "\n".join(f"{k}: {v}" for k, v in info.items())


@mcp.tool
def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """Create a temporary file with content"""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(content)
            temp_path = f.name
        return f"✔️ Temporary file created: {temp_path}"
    except Exception as e:
        return f"❌ Error creating temporary file: {str(e)}"


@mcp.tool
def find_files(pattern: str, directory: str = ".", recursive: bool = True) -> str:
    """Find files matching a pattern"""
    try:
        matches = []
        search_pattern = f"**/{pattern}" if recursive else pattern
        for match in Path(directory).glob(search_pattern):
            matches.append(str(match))

        if not matches:
            return f"🔍 No files found matching '{pattern}' in {directory}"

        return f"🔍 Found {len(matches)} files matching '{pattern}':\n" + "\n".join(
            matches
        )
    except Exception as e:
        return f"❌ Error searching files: {str(e)}"


@mcp.tool
def check_port(port: int, host: str = "localhost") -> str:
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex((host, port))
            if result == 0:
                return f"🔴 Port {port} is occupied on {host}"
            else:
                return f"🟢 Port {port} is available on {host}"
    except Exception as e:
        return f"❌ Error checking port: {str(e)}"


@mcp.tool
def start_http_server(port: int = 8080, directory: str = ".") -> str:
    """Start a simple HTTP server in the background"""
    try:

        def run_server():
            os.chdir(directory)
            import http.server
            import socketserver

            handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", port), handler) as httpd:
                httpd.serve_forever()

        # Check if port is available first
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) == 0:
                return f"❌ Port {port} is already in use"

        # Start server in background thread
        thread = Thread(target=run_server, daemon=True)
        thread.start()

        return f"✔️ HTTP server started on port {port} serving directory: {directory}\nAccess at: http://localhost:{port}"
    except Exception as e:
        return f"❌ Error starting HTTP server: {str(e)}"


@mcp.tool
def get_file_info(filepath: str) -> str:
    """Get detailed information about a file"""
    try:
        path = Path(filepath)
        if not path.exists():
            return f"❌ File does not exist: {filepath}"

        stat = path.stat()
        info = {
            "Path": str(path.absolute()),
            "Size": f"{stat.st_size} bytes",
            "Type": "Directory" if path.is_dir() else "File",
            "Modified": time.ctime(stat.st_mtime),
            "Created": time.ctime(stat.st_ctime),
            "Permissions": oct(stat.st_mode)[-3:],
        }

        return f"ℹ️ File Information for {filepath}:\n" + "\n".join(
            f"{k}: {v}" for k, v in info.items()
        )
    except Exception as e:
        return f"❌ Error getting file info: {str(e)}"


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
    print("🚀 Starting OOMCP Server...")
    print(f"📍 Working directory: {current_working_dir}")
    mcp.run(transport="http", host="0.0.0.0", port=8000)
