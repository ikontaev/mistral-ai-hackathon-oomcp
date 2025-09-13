from fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool
def hello(name: str) -> str:
    """say hello"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)