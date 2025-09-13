import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib


from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

COLLECTION_NAME="oomcp_tools"
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

@dataclass
class ToolMetadata:
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    examples: List[str]
    keywords: List[str]  

class QdrantToolSelector:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collection_name = "oomcp_tools"
        self.embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.embedding_dim = 384  # Dimension for all-MiniLM-L6-v2
        
        # Initialize Qdrant client
        self._init_qdrant_client()
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        # Tool registry
        self.tools_registry: Dict[str, ToolMetadata] = {}
        
    def _init_qdrant_client(self):
        """Initialize Qdrant client based on environment variables"""
        if os.getenv("QDRANT_URL") and os.getenv("QDRANT_API_KEY"):
            # Cloud Qdrant
            self.qdrant_client = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY")
            )
            print("🌩️  Connected to Qdrant Cloud")
        elif os.getenv("QDRANT_LOCAL_PATH"):
            # Local Qdrant
            self.qdrant_client = QdrantClient(path=os.getenv("QDRANT_LOCAL_PATH"))
            print("💾 Connected to Local Qdrant")
        else:
            # In-memory Qdrant for development
            self.qdrant_client = QdrantClient(":memory:")
            print("🧠 Using In-Memory Qdrant")
            
        # Create collection if it doesn't exist
        self._create_collection()
    
    def _create_collection(self):
        """Create the tools collection in Qdrant"""
        try:
            collections = self.qdrant_client.get_collections().collections
            if not any(col.name == self.collection_name for col in collections):
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Created collection: {self.collection_name}")
            else:
                print(f"📋 Collection already exists: {self.collection_name}")
        except Exception as e:
            print(f"❌ Error creating collection: {e}")
    
    def register_tool(self, name: str, description: str, category: str, 
                     parameters: Dict[str, Any] = None, examples: List[str] = None,
                     keywords: List[str] = None):
        """Register a tool with its metadata"""
        tool_metadata = ToolMetadata(
            name=name,
            description=description,
            category=category,
            parameters=parameters or {},
            examples=examples or [],
            keywords=keywords or []
        )
        self.tools_registry[name] = tool_metadata
        
    def embed_and_store_tools(self):
        """Embed all registered tools and store them in Qdrant"""
        points = []
        
        for tool_name, tool_meta in self.tools_registry.items():
            # Create comprehensive text for embedding
            text_for_embedding = self._create_tool_text(tool_meta)
            
            # Generate embedding
            embedding = self.embedding_model.encode(text_for_embedding).tolist()
            
            # Create point ID using hash of tool name
            point_id = int(hashlib.md5(tool_name.encode()).hexdigest()[:8], 16)
            
            # Create point with metadata
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "tool_name": tool_name,
                    "description": tool_meta.description,
                    "category": tool_meta.category,
                    "parameters": json.dumps(tool_meta.parameters),
                    "examples": tool_meta.examples,
                    "keywords": tool_meta.keywords,
                    "search_text": text_for_embedding
                }
            )
            points.append(point)
        
        # Store all points in Qdrant
        try:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            print(f"✅ Stored {len(points)} tools in Qdrant")
        except Exception as e:
            print(f"❌ Error storing tools: {e}")
    
    def _create_tool_text(self, tool_meta: ToolMetadata) -> str:
        """Create comprehensive text representation of a tool for embedding"""
        text_parts = [
            f"Tool: {tool_meta.name}",
            f"Category: {tool_meta.category}",
            f"Description: {tool_meta.description}"
        ]
        
        # Add parameter information
        if tool_meta.parameters:
            params_text = "Parameters: " + ", ".join(tool_meta.parameters.keys())
            text_parts.append(params_text)
        
        # Add examples
        if tool_meta.examples:
            examples_text = "Examples: " + " | ".join(tool_meta.examples)
            text_parts.append(examples_text)
        
        # Add keywords
        if tool_meta.keywords:
            keywords_text = "Keywords: " + " ".join(tool_meta.keywords)
            text_parts.append(keywords_text)
        
        return " | ".join(text_parts)
    
    def find_relevant_tools(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find the most relevant tools for a given query"""
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True
            )
            
            # Format results
            relevant_tools = []
            for result in search_results:
                tool_info = {
                    "tool_name": result.payload["tool_name"],
                    "description": result.payload["description"],
                    "category": result.payload["category"],
                    "relevance_score": result.score,
                    "examples": result.payload.get("examples", []),
                    "keywords": result.payload.get("keywords", [])
                }
                relevant_tools.append(tool_info)
            
            return relevant_tools
            
        except Exception as e:
            print(f"❌ Error finding relevant tools: {e}")
            return []
    
    def get_tool_suggestion(self, query: str) -> str:
        """Get a formatted suggestion of relevant tools for a query"""
        relevant_tools = self.find_relevant_tools(query, limit=3)
        
        if not relevant_tools:
            return "❌ No relevant tools found for your query."
        
        suggestion = f"🔍 **Top tools for:** '{query}'\n\n"
        
        for i, tool in enumerate(relevant_tools, 1):
            suggestion += f"**{i}. {tool['tool_name']}** (Score: {tool['relevance_score']:.3f})\n"
            suggestion += f"   📝 {tool['description']}\n"
            suggestion += f"   🏷️ Category: {tool['category']}\n"
            
            if tool['examples']:
                suggestion += f"   💡 Examples: {', '.join(tool['examples'][:2])}\n"
            if tool['keywords']:
                suggestion += f"   🔑 Keywords: {', '.join(tool['keywords'][:3])}\n"
            suggestion += "\n"
        
        return suggestion

    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all tools in a specific category"""
        category_tools = []
        for tool_name, tool_meta in self.tools_registry.items():
            if tool_meta.category.lower() == category.lower():
                category_tools.append({
                    "tool_name": tool_name,
                    "description": tool_meta.description,
                    "examples": tool_meta.examples[:2],
                    "keywords": tool_meta.keywords[:3]
                })
        return category_tools


def register(mcp, config):
    """Register the Qdrant tool selector with the MCP system"""
    
    # Initialize the tool selector
    selector = QdrantToolSelector(config)
    
    # Register all existing tools with metadata
    _register_all_tools(selector)
    
    # Embed and store tools in Qdrant
    selector.embed_and_store_tools()
    
    @mcp.tool
    def find_tools_for_task(query: str, max_tools: int = 5) -> str:
        """Find the most relevant tools for a specific task or query using semantic search"""
        try:
            relevant_tools = selector.find_relevant_tools(query, limit=max_tools)
            
            if not relevant_tools:
                return f"❌ No relevant tools found for: '{query}'"
            
            result = f"🎯 **Relevant tools for:** '{query}'\n\n"
            
            for i, tool in enumerate(relevant_tools, 1):
                result += f"**{i}. {tool['tool_name']}** (Relevance: {tool['relevance_score']:.3f})\n"
                result += f"   📝 {tool['description']}\n"
                result += f"   🏷️ Category: {tool['category']}\n"
                
                if tool['examples']:
                    result += f"   💡 Use cases: {', '.join(tool['examples'][:2])}\n"
                if tool['keywords']:
                    result += f"   🔑 Keywords: {', '.join(tool['keywords'][:3])}\n"
                result += "\n"
            
            return result
            
        except Exception as e:
            return f"❌ Error finding tools: {str(e)}"
    
    @mcp.tool
    def get_tool_recommendation(task_description: str) -> str:
        """Get intelligent tool recommendations based on what you want to accomplish"""
        return selector.get_tool_suggestion(task_description)
    
    @mcp.tool
    def list_tools_by_category(category: str) -> str:
        """List all tools in a specific category (file_system, cloud_infrastructure, networking, etc.)"""
        try:
            tools = selector.get_tools_by_category(category)
            if not tools:
                available_categories = list(set(tool.category for tool in selector.tools_registry.values()))
                return f"❌ No tools found in category '{category}'. Available categories: {', '.join(available_categories)}"
            
            result = f"🗂️ **Tools in category: {category}**\n\n"
            for i, tool in enumerate(tools, 1):
                result += f"**{i}. {tool['tool_name']}**\n"
                result += f"   📝 {tool['description']}\n"
                if tool['examples']:
                    result += f"   💡 Examples: {', '.join(tool['examples'])}\n"
                result += "\n"
            
            return result
        except Exception as e:
            return f"❌ Error listing tools by category: {str(e)}"
    
    @mcp.tool
    def refresh_tool_embeddings() -> str:
        """Refresh the tool embeddings in the vector database"""
        try:
            selector.embed_and_store_tools()
            return "✅ Tool embeddings refreshed successfully"
        except Exception as e:
            return f"❌ Error refreshing embeddings: {str(e)}"

    @mcp.tool
    def get_all_tool_categories() -> str:
        """Get a list of all available tool categories"""
        categories = list(set(tool.category for tool in selector.tools_registry.values()))
        result = "📂 **Available tool categories:**\n\n"
        for category in sorted(categories):
            tools_count = len([t for t in selector.tools_registry.values() if t.category == category])
            result += f"• **{category}** ({tools_count} tools)\n"
        return result

def _register_all_tools(selector: QdrantToolSelector):
    """Register ALL available tools with comprehensive metadata"""
    
    # =====================
    # FILE SYSTEM TOOLS
    # =====================
    selector.register_tool(
        "create_file", 
        "Create a new file with specified content at any path",
        "file_system",
        {"filepath": "str", "content": "str"},
        ["create a Python script", "save configuration file", "write documentation", "create HTML page"],
        ["create", "file", "write", "save", "new"]
    )
    
    selector.register_tool(
        "read_file",
        "Read and return the complete content of any file", 
        "file_system",
        {"filepath": "str"},
        ["read configuration", "load source code", "view file contents", "inspect logs"],
        ["read", "file", "content", "load", "view"]
    )
    
    selector.register_tool(
        "append_to_file",
        "Add content to the end of an existing file",
        "file_system",
        {"filepath": "str", "content": "str"},
        ["add logs to file", "append data", "update configuration", "add code snippet"],
        ["append", "add", "update", "extend"]
    )
    
    selector.register_tool(
        "delete_file",
        "Remove a file from the filesystem",
        "file_system",
        {"filepath": "str"},
        ["remove temporary file", "cleanup old data", "delete backup", "remove logs"],
        ["delete", "remove", "cleanup", "unlink"]
    )
    
    selector.register_tool(
        "list_files",
        "List files and directories with optional pattern filtering",
        "file_system", 
        {"directory": "str", "pattern": "str"},
        ["browse project files", "find all Python files", "list directory contents", "find *.json files"],
        ["list", "browse", "directory", "find", "search"]
    )
    
    selector.register_tool(
        "create_directory",
        "Create a new directory with all parent directories",
        "file_system",
        {"directory": "str"},
        ["make project folder", "create nested directories", "setup workspace", "organize files"],
        ["mkdir", "directory", "folder", "create"]
    )
    
    selector.register_tool(
        "copy_file",
        "Copy a file from source to destination location",
        "file_system",
        {"source": "str", "destination": "str"},
        ["backup configuration", "duplicate file", "copy template", "clone script"],
        ["copy", "duplicate", "backup", "clone"]
    )
    
    selector.register_tool(
        "move_file",
        "Move or rename a file from source to destination",
        "file_system",
        {"source": "str", "destination": "str"},
        ["rename file", "move to different folder", "reorganize files", "relocate data"],
        ["move", "rename", "relocate", "transfer"]
    )
    
    selector.register_tool(
        "find_files",
        "Search for files matching a pattern recursively",
        "file_system",
        {"pattern": "str", "directory": "str", "recursive": "bool"},
        ["find all Python files", "search for config files", "locate images", "find by extension"],
        ["find", "search", "locate", "pattern", "recursive"]
    )
    
    selector.register_tool(
        "get_file_info",
        "Get detailed metadata about a file or directory",
        "file_system",
        {"filepath": "str"},
        ["check file size", "view permissions", "get creation date", "file statistics"],
        ["info", "metadata", "stats", "properties", "details"]
    )
    
    # =====================
    # PYTHON EXECUTION
    # =====================
    selector.register_tool(
        "run_python",
        "Execute Python code directly and return output",
        "python_execution",
        {"code": "str", "cwd": "str"},
        ["run data analysis", "execute script", "test code snippet", "calculate results", "process data"],
        ["python", "execute", "run", "code", "script", "calculate"]
    )
    
    selector.register_tool(
        "install_package",
        "Install a Python package using pip",
        "python_execution",
        {"package": "str"}, 
        ["install numpy", "add dependencies", "setup packages", "install flask", "add libraries"],
        ["install", "pip", "package", "dependency", "library"]
    )
    
    selector.register_tool(
        "list_packages",
        "List all installed Python packages",
        "python_execution",
        {},
        ["check installed packages", "view dependencies", "audit environment", "package inventory"],
        ["packages", "dependencies", "pip list", "installed"]
    )
    
    # =====================
    # NETWORKING TOOLS
    # =====================
    selector.register_tool(
        "fetch",
        "Make HTTP requests to URLs with custom headers and data",
        "networking",
        {"url": "str", "method": "str", "headers": "str", "data": "str"},
        ["download file from URL", "API request", "web scraping", "check website status", "POST data"],
        ["http", "request", "api", "download", "web", "fetch", "curl"]
    )
    
    selector.register_tool(
        "start_web_server",
        "Start a simple HTTP server serving files from a directory",
        "networking",
        {"port": "int", "directory": "str"},
        ["serve static files", "local development server", "share files via HTTP", "host website"],
        ["server", "http", "serve", "static", "web", "host"]
    )
    
    selector.register_tool(
        "start_http_server",
        "Start an advanced HTTP server with custom route handling",
        "networking",
        {"port": "int"},
        ["create API server", "custom endpoints", "REST API", "web service", "backend server"],
        ["api", "server", "routes", "endpoints", "REST", "backend"]
    )
    
    selector.register_tool(
        "generate_http_server_endpoint",
        "Create a custom endpoint handler for the HTTP server",
        "networking",
        {"endpoint": "str", "code": "str"},
        ["create API endpoint", "handle POST requests", "custom route logic", "webhook handler"],
        ["endpoint", "route", "handler", "api", "webhook"]
    )
    
    selector.register_tool(
        "check_port",
        "Check if a network port is available or occupied",
        "networking",
        {"port": "int", "host": "str"},
        ["check if port 8080 is free", "test service availability", "port scanning", "network diagnostics"],
        ["port", "network", "check", "available", "occupied"]
    )
    
    # =====================
    # CLOUD INFRASTRUCTURE (Hetzner)
    # =====================
    selector.register_tool(
        "create_server",
        "Create a new Hetzner Cloud server instance",
        "cloud_infrastructure",
        {"name": "str", "server_type": "str", "image": "str", "location": "str"},
        ["deploy new server", "create Ubuntu VM", "launch cloud instance", "setup infrastructure", "provision server"],
        ["server", "cloud", "deploy", "vm", "instance", "hetzner"]
    )
    
    selector.register_tool(
        "list_servers", 
        "List all Hetzner Cloud servers and their status",
        "cloud_infrastructure",
        {},
        ["check my servers", "view infrastructure", "server inventory", "cloud resources"],
        ["servers", "infrastructure", "cloud", "inventory", "status"]
    )
    
    selector.register_tool(
        "delete_server",
        "Delete a Hetzner Cloud server permanently",
        "cloud_infrastructure", 
        {"server_id": "int"},
        ["remove server", "cleanup infrastructure", "delete VM", "destroy instance"],
        ["delete", "remove", "destroy", "cleanup", "terminate"]
    )
    
    selector.register_tool(
        "get_server_info",
        "Get detailed information about a specific server",
        "cloud_infrastructure",
        {"server_id": "int"},
        ["check server details", "view server IP", "server specifications", "instance info"],
        ["info", "details", "specifications", "status", "metadata"]
    )
    
    selector.register_tool(
        "start_server",
        "Power on a Hetzner Cloud server",
        "cloud_infrastructure",
        {"server_id": "int"},
        ["boot server", "power on instance", "start VM", "bring server online"],
        ["start", "boot", "power", "online", "activate"]
    )
    
    selector.register_tool(
        "stop_server",
        "Power off a Hetzner Cloud server",
        "cloud_infrastructure",
        {"server_id": "int"},
        ["shutdown server", "power off instance", "stop VM", "take server offline"],
        ["stop", "shutdown", "power off", "offline", "halt"]
    )
    
    selector.register_tool(
        "reboot_server",
        "Restart a Hetzner Cloud server",
        "cloud_infrastructure",
        {"server_id": "int"},
        ["restart server", "reboot instance", "reset VM", "refresh server"],
        ["reboot", "restart", "reset", "refresh", "cycle"]
    )
    
    selector.register_tool(
        "create_ssh_key",
        "Create a new SSH key for server access",
        "cloud_infrastructure",
        {"name": "str", "public_key": "str"},
        ["add SSH key for access", "setup server authentication", "manage access keys"],
        ["ssh", "key", "authentication", "access", "security"]
    )
    
    selector.register_tool(
        "list_ssh_keys",
        "List all SSH keys in your account",
        "cloud_infrastructure",
        {},
        ["view SSH keys", "manage access keys", "check authentication keys"],
        ["ssh", "keys", "authentication", "access", "list"]
    )
    
    # =====================
    # JUPYTER INTEGRATION
    # =====================
    selector.register_tool(
        "start_kernel",
        "Start a new Jupyter kernel for interactive code execution",
        "jupyter",
        {"kernel_name": "str", "path": "str"},
        ["start Python environment", "begin data analysis", "create notebook session", "interactive computing"],
        ["jupyter", "kernel", "notebook", "interactive", "python"]
    )
    
    selector.register_tool(
        "execute_code",
        "Execute code in a running Jupyter kernel",
        "jupyter",
        {"kernel_id": "str", "code": "str", "silent": "bool"},
        ["run analysis code", "execute notebook cell", "interactive computing", "data processing"],
        ["execute", "run", "code", "cell", "jupyter"]
    )
    
    selector.register_tool(
        "list_running_kernels",
        "List all currently active Jupyter kernels",
        "jupyter",
        {},
        ["check active sessions", "view running kernels", "kernel management"],
        ["kernels", "jupyter", "sessions", "active", "running"]
    )
    
    selector.register_tool(
        "create_notebook_with_code",
        "Create a new Jupyter notebook with predefined code cells",
        "jupyter",
        {"path": "str", "code_blocks": "list", "kernel_name": "str"},
        ["create analysis notebook", "setup data science workflow", "generate report template"],
        ["notebook", "create", "jupyter", "template", "analysis"]
    )
    
    # =====================
    # STORAGE TOOLS
    # =====================
    selector.register_tool(
        "put",
        "Store a key-value pair in the persistent database",
        "storage",
        {"key": "str", "value": "str", "db_path": "str"},
        ["save configuration", "store data", "cache results", "persist information", "save state"],
        ["store", "save", "cache", "persist", "database", "kv"]
    )
    
    selector.register_tool(
        "get", 
        "Retrieve a value by key from the persistent database",
        "storage",
        {"key": "str", "db_path": "str"},
        ["load configuration", "retrieve data", "get cached results", "load state"],
        ["get", "retrieve", "load", "fetch", "database", "kv"]
    )
    
    selector.register_tool(
        "list", 
        "List stored key-value pairs with pagination support",
        "storage",
        {"prefix": "str", "limit": "int", "start_after": "str", "db_path": "str"},
        ["browse stored data", "list all keys", "paginate through records", "search by prefix"],
        ["list", "browse", "search", "pagination", "keys"]
    )
    
    # =====================
    # SYSTEM OPERATIONS
    # =====================
    selector.register_tool(
        "run_shell",
        "Execute shell commands and return output",
        "system_operations",
        {"command": "str", "cwd": "str"},
        ["run git commands", "system administration", "execute CLI tools", "file operations", "ls command"],
        ["shell", "command", "bash", "cli", "terminal", "git"]
    )
    
    selector.register_tool(
        "get_system_info",
        "Get detailed system and environment information",
        "system_operations",
        {},
        ["check system specs", "environment details", "platform info", "diagnostics"],
        ["system", "info", "platform", "environment", "specs"]
    )
    
    # =====================
    # CONTENT GENERATION
    # =====================
    selector.register_tool(
        "generate_html",
        "Generate a complete HTML file with title and body content",
        "content_generation",
        {"title": "str", "body": "str", "name": "str"},
        ["create webpage", "generate HTML document", "build simple site", "create landing page"],
        ["html", "webpage", "generate", "create", "web", "site"]
    )
    
    # =====================
    # DATA ANALYSIS
    # =====================
    selector.register_tool(
        "read_csv",
        "Analyze CSV data from base64-encoded content with preview",
        "data_analysis",
        {"csv_content_base64": "str", "max_preview_rows": "int"},
        ["analyze spreadsheet", "process CSV data", "examine dataset", "data preview", "parse table"],
        ["csv", "data", "spreadsheet", "analyze", "table", "dataset"]
    )
    
    # =====================
    # COMMUNICATION
    # =====================
    selector.register_tool(
        "send_email",
        "Send emails with HTML content via Resend API",
        "communication",
        {"to": "str|list", "subject": "str", "html": "str", "from_email": "str"},
        ["send notification email", "email reports", "alert via email", "HTML newsletter"],
        ["email", "send", "notification", "communication", "mail"]
    )
    
    # =====================
    # UTILITY
    # =====================
    selector.register_tool(
        "hello",
        "Basic connectivity test and greeting function",
        "utility",
        {"name": "str"},
        ["test connection", "health check", "basic greeting", "system test"],
        ["hello", "test", "ping", "health", "connectivity"]
    )