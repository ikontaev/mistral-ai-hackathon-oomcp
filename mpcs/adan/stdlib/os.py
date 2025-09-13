from fastmcp import FastMCP
import os
import subprocess
import json
import shutil
import glob
from pathlib import Path
import tempfile
import sys
import socket
from threading import Thread
import time

def register(mcp): 
    @mcp.tool
    def run_shell(command: str, cwd: str = None) -> str:
        """Execute shell command and return output"""

        current_working_dir = os.getcwd()
        try:
            work_dir = cwd or current_working_dir
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=work_dir,
                capture_output=True, 
                text=True, 
                timeout=30
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
