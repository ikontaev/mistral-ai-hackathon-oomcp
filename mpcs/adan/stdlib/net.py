from fastmcp import FastMCP
import os
import json
import socket
from threading import Thread
import httpx
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import shutil

def register(mcp, config): 
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
    def start_http_server(port: int = 8080) -> str:
        """Start a minimal HTTP server that loads 1st-level routes from a directory."""
        try:
            # prepare routing system
            routes_dir = config["space_path"] + "/routes"
            handler_template = os.path.join(config["root_path"], "data/templates/api_handler.template")
            os.makedirs(routes_dir, exist_ok=True)
            shutil.copy(handler_template, os.path.join(routes_dir, "__default__.py"))

            # check port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", port)) == 0:
                    return f"❌ Port {port} is already in use"

            # ---- helpers internos ----
            class Request:
                def __init__(self, handler: BaseHTTPRequestHandler):
                    self._h = handler
                    parsed = urlparse(handler.path)
                    self.method = handler.command.upper()
                    self.path = parsed.path
                    self.query = {k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(parsed.query).items()}
                    self.headers = dict(handler.headers.items())
                    self._body = None
                    self._text = None
                    self._json = None

                @property
                def body(self) -> bytes:
                    if self._body is None:
                        length = int(self.headers.get("Content-Length", "0") or 0)
                        self._body = self._h.rfile.read(length) if length > 0 else b""
                    return self._body

                @property
                def text(self) -> str:
                    if self._text is None:
                        self._text = self.body.decode("utf-8", errors="replace")
                    return self._text

                @property
                def json(self):
                    if self._json is None:
                        try:
                            self._json = json.loads(self.text) if self.text else None
                        except Exception:
                            self._json = None
                    return self._json

            def _resolve_first_level_route(method: str, path: str) -> str | None:
                """
                Map:
                GET /           -> routes/index.get.py or routes/index.py
                GET /health     -> routes/health.get.py or routes/health.py
                Only first-level: '/name'. No '/a/b'.
                """
                name = path.strip("/")
                if name == "":
                    name = "__default__"

                # solo primer nivel: rechazar si contiene más '/'
                if "/" in name or "\\" in name or name.startswith(".") or ".." in name:
                    return None

                candidates = [f"{name}.{method.lower()}.py", f"{name}.py"]
                for file in candidates:
                    full = os.path.join(routes_dir, file)
                    if os.path.isfile(full):
                        return full
                return None

            def _run_handler(file_path: str, req: Request):
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                ns = {}
                exec(compile(code, file_path, "exec"), ns, ns)
                if "handle" not in ns or not callable(ns["handle"]):
                    raise RuntimeError(f"Missing handle(req) in {os.path.relpath(file_path)}")
                return ns["handle"](req)

            class Handler(BaseHTTPRequestHandler):
                server_version = "FastMCP-HTTP-Flat/1.0"

                def _send(self, code: int, body, headers: dict | None = None):
                    headers = headers or {}
                    # normalizar body -> bytes y content-type
                    ctype = headers.get("Content-Type")
                    if isinstance(body, (dict, list)):
                        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
                        ctype = ctype or "application/json; charset=utf-8"
                    elif isinstance(body, (bytes, bytearray)):
                        payload = bytes(body)
                        ctype = ctype or "application/octet-stream"
                    elif isinstance(body, str):
                        payload = body.encode("utf-8")
                        ctype = ctype or "text/plain; charset=utf-8"
                    elif body is None:
                        payload = b""
                        ctype = ctype or "text/plain; charset=utf-8"
                    else:
                        payload = repr(body).encode("utf-8")
                        ctype = ctype or "text/plain; charset=utf-8"

                    self.send_response(code)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                    self.send_header("Content-Type", ctype)
                    for k, v in headers.items():
                        if k.lower() != "content-type":
                            self.send_header(k, v)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    if self.command != "HEAD":
                        self.wfile.write(payload)

                def do_OPTIONS(self):
                    self.send_response(204)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                    self.end_headers()

                def _dispatch(self):
                    try:
                        req = Request(self)
                        route_file = _resolve_first_level_route(req.method, req.path)
                        if route_file:
                            result = _run_handler(route_file, req)
                            headers = {}
                            if isinstance(result, tuple) and len(result) in (2, 3):
                                status = int(result[0])
                                body = result[1]
                                if len(result) == 3 and isinstance(result[2], dict):
                                    headers = result[2]
                            else:
                                status = 200
                                body = result
                            return self._send(status, body, headers)

                        # 404 si no existe handler
                        return self._send(404, {"error": "Not found", "path": self.path})
                    except Exception as e:
                        tb = traceback.format_exc(limit=2)
                        return self._send(500, {"error": str(e), "trace": tb})

                # métodos
                def do_GET(self):     self._dispatch()
                def do_HEAD(self):    self._dispatch()
                def do_POST(self):    self._dispatch()
                def do_PUT(self):     self._dispatch()
                def do_PATCH(self):   self._dispatch()
                def do_DELETE(self):  self._dispatch()

                def log_message(self, format, *args):
                    pass  # silenciar logs

            # lanzar en background
            def run_server():
                httpd = ThreadingHTTPServer(("", port), Handler)
                httpd.daemon_threads = True
                httpd.serve_forever()

            thread = Thread(target=run_server, daemon=True)
            thread.start()

            return (
                f"✔️ HTTP server started on port {port}\n"
                f"   Routes dir: {os.path.abspath(routes_dir)}\n"
                f"   First-level only. Examples:\n"
                f"     - {routes_dir}/index.get.py  -> GET /\n"
                f"     - {routes_dir}/index.py      -> any method /\n"
                f"     - {routes_dir}/health.py     -> GET /health\n"
                f"     - {routes_dir}/echo.post.py  -> POST /echo"
            )
        except Exception as e:
            return f"❌ Error starting HTTP server: {e}"

    @mcp.tool
    def generate_http_server_endpoint(endpoint: str = "__default__", code: str = "def handle(req): return {\"ok\": True, \"msg\": \"default endpoint\"}") -> str:
        """
        generate a endpoint for an http server with the following params:
        endpoint: single string with the endpoint of the server 
        code: a python code with the following structure
            ```
            def handle(req):
                # here return anything wanted
            ```
        
        the http server endpoint is created within this tool
        """
        try:
            routes_dir = os.path.join(config["space_path"], "routes", endpoint+".py")
            with open(routes_dir, 'w', encoding='utf-8') as f:
                f.write(code)
            return endpoint 
        except Exception as e:
            return f"❌ Error starting generating endpoint: {e}"
 

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
