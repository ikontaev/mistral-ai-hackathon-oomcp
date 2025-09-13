from fastmcp import FastMCP
import os
import requests
import json
import time
from typing import Optional, Dict, Any, List, Union

def register(mcp: FastMCP):
    """Register Jupyter API tools with MCP server"""
    # Use internal URL when running inside docker network, external URL when accessing from outside
    jupyter_url = os.getenv("INTERNAL_JUPYTER_URL", os.getenv("JUPYTER_URL", "http://localhost:8888"))
    jupyter_token = os.getenv("INTERNAL_JUPYTER_TOKEN", os.getenv("JUPYTER_TOKEN", ""))

    if not jupyter_token:
        print("⚠️ Warning: JUPYTER_TOKEN not set. Jupyter tools will not work without authentication.")
        return

    # Base headers for all requests
    base_headers = {
        "Authorization": f"token {jupyter_token}",
        "Content-Type": "application/json"
    }

    # If using HTTPS, we need to verify SSL unless it's a local development environment
    verify_ssl = True
    if jupyter_url.startswith(('http://localhost', 'http://127.0.0.1', 'http://jupyter')):
        verify_ssl = False

    def _make_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Helper function to make requests to Jupyter API"""
        url = f"{jupyter_url.rstrip('/')}/api{endpoint}"
        try:
            response = requests.request(
                method,
                url,
                headers=base_headers,
                verify=verify_ssl,
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else {"status": "success"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}

    @mcp.tool
    def list_available_kernels() -> str:
        """List all available kernel specs that can be launched"""
        result = _make_request("GET", "/kernelspecs")
        return json.dumps(result, indent=2)

    @mcp.tool
    def start_kernel(kernel_name: str = "python3", path: str = "") -> str:
        """
        Start a new kernel with optional working directory path
        Returns kernel ID that can be used for execution
        """
        data = {"name": kernel_name}
        if path:
            data["path"] = path
        result = _make_request("POST", "/kernels", json=data)
        return json.dumps(result, indent=2)

    @mcp.tool
    def execute_code(kernel_id: str, code: str, silent: bool = False) -> str:
        """
        Execute code in a running kernel
        Returns execution results including output and status
        """
        data = {
            "code": code,
            "silent": silent
        }
        result = _make_request("POST", f"/kernels/{kernel_id}/execute", json=data)
        return json.dumps(result, indent=2)

    @mcp.tool
    def execute_code_with_results(kernel_id: str, code: str, timeout: int = 30) -> str:
        """
        Execute code and wait for results with timeout
        Returns complete execution results including outputs
        """
        # First execute the code
        execute_response = _make_request(
            "POST",
            f"/kernels/{kernel_id}/execute",
            json={"code": code}
        )

        if execute_response.get("status") == "failed":
            return json.dumps(execute_response, indent=2)

        # Get the execution message ID to poll for results
        msg_id = execute_response.get("metadata", {}).get("id")
        if not msg_id:
            return json.dumps({
                "error": "No message ID returned from execution",
                "status": "failed"
            }, indent=2)

        # Poll for results
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = _make_request("GET", f"/kernels/{kernel_id}/channels?session_id={msg_id}")
            if result.get("status") == "failed":
                return json.dumps(result, indent=2)

            if result.get("content"):
                return json.dumps(result, indent=2)
            time.sleep(0.5)

        return json.dumps({
            "error": f"Timeout after {timeout} seconds waiting for results",
            "status": "timeout"
        }, indent=2)

    @mcp.tool
    def get_kernel_status(kernel_id: str) -> str:
        """Get status and information about a running kernel"""
        result = _make_request("GET", f"/kernels/{kernel_id}")
        return json.dumps(result, indent=2)

    @mcp.tool
    def interrupt_kernel(kernel_id: str) -> str:
        """Interrupt running code in a kernel"""
        result = _make_request("POST", f"/kernels/{kernel_id}/interrupt")
        return json.dumps(result, indent=2)

    @mcp.tool
    def restart_kernel(kernel_id: str) -> str:
        """Restart a kernel (clears all variables and state)"""
        result = _make_request("POST", f"/kernels/{kernel_id}/restart")
        return json.dumps(result, indent=2)

    @mcp.tool
    def shutdown_kernel(kernel_id: str) -> str:
        """Shutdown a kernel completely"""
        result = _make_request("DELETE", f"/kernels/{kernel_id}")
        return json.dumps(result, indent=2)

    @mcp.tool
    def list_running_kernels() -> str:
        """List all currently running kernels"""
        result = _make_request("GET", "/kernels")
        return json.dumps(result, indent=2)

    @mcp.tool
    def create_notebook_with_code(path: str, code_blocks: List[str], kernel_name: str = "python3") -> str:
        """
        Create a new notebook with multiple code blocks
        Each code block will be in its own cell
        """
        # Create empty notebook first
        notebook_data = {
            "cells": [],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 4
        }

        # Add each code block as a separate cell
        for code in code_blocks:
            notebook_data["cells"].append({
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": code.splitlines(True),
                "outputs": []
            })

        # Create the notebook file
        result = _make_request(
            "PUT",
            f"/contents/{path.lstrip('/')}",
            json={
                "content": notebook_data,
                "type": "notebook",
                "format": "json"
            }
        )

        # Optionally start a kernel for this notebook
        if result.get("status") != "failed":
            kernel_result = start_kernel(kernel_name, os.path.dirname(path))
            return json.dumps({
                "notebook": result,
                "kernel": json.loads(kernel_result) if kernel_result else None
            }, indent=2)

        return json.dumps(result, indent=2)

    @mcp.tool
    def execute_notebook_cells(kernel_id: str, notebook_path: str) -> str:
        """
        Execute all code cells in a notebook using the specified kernel
        Returns execution results for each cell
        """
        # First get the notebook content
        notebook_result = _make_request("GET", f"/contents/{notebook_path.lstrip('/')}")
        if notebook_result.get("status") == "failed":
            return json.dumps(notebook_result, indent=2)

        notebook = notebook_result.get("content", {})
        if not notebook:
            return json.dumps({"error": "No notebook content found", "status": "failed"}, indent=2)

        # Execute each code cell
        results = []
        for i, cell in enumerate(notebook.get("cells", [])):
            if cell.get("cell_type") == "code":
                code = "".join(cell.get("source", []))
                result = execute_code_with_results(kernel_id, code)
                results.append({
                    "cell_index": i,
                    "code": code,
                    "result": json.loads(result)
                })

        return json.dumps({
            "notebook_path": notebook_path,
            "kernel_id": kernel_id,
            "execution_results": results
        }, indent=2)