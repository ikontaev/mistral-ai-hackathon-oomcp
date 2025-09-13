from fastmcp import FastMCP
import os

mcp = FastMCP("OOMCP")

@mcp.tool
def hello(name: str) -> str:
    """say hello"""
    return f"Hello, {name}!"

    
@mcp.tool
def run_python(code: str, cwd: str = ".") -> str:
    """execute python code and return
    the output of the execution"""
    import io
    import contextlib
    import traceback

    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            # basic "sandbox" with empty dic
            local_env = {}
            exec(code, {}, local_env)
        return buffer.getvalue() or "✔️ Código ejecutado sin salida."
    except Exception:
        return "❌ Error:\n" + traceback.format_exc()

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)