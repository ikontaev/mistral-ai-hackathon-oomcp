from fastmcp import FastMCP
import subprocess
from pathlib import Path
import sys
import os

def register(mcp, config):    
    @mcp.tool
    def run_python(code: str, cwd: str = None) -> str:
        """Execute python code and return the output"""
        import io
        import contextlib
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
                    '__builtins__': __builtins__,
                    'os': os,
                    'sys': sys,
                    'json': json,
                    'Path': Path,
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
    def install_package(package: str) -> str:
        """Install a Python package using pip"""
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True, timeout=60)
            
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
            result = subprocess.run([
                sys.executable, "-m", "pip", "list"
            ], capture_output=True, text=True)
            return f"📦 Installed packages:\n{result.stdout}"
        except Exception as e:
            return f"❌ Error listing packages: {str(e)}"
 