from fastmcp import FastMCP
import os
import json
import socket
from threading import Thread
import httpx

def register(mcp): 
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
    def start_web_server(port: int = 8080, directory: str = ".") -> str:
        """Start a simple web server in the background with fallback to index.html"""
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

