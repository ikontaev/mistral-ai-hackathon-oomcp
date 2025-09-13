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

def register(mcp, config): 
    @mcp.tool
    def create_file(filepath: str, content: str) -> str:
        """Create a new file with specified content"""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✔️ File created: {filepath}"
        except Exception as e:
            return f"❌ Error creating file: {str(e)}"

    @mcp.tool
    def read_file(filepath: str) -> str:
        """Read content from a file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"📄 Content of {filepath}:\n{content}"
        except Exception as e:
            return f"❌ Error reading file: {str(e)}"

    @mcp.tool
    def append_to_file(filepath: str, content: str) -> str:
        """Append content to an existing file"""
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
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
    def create_temp_file(content: str, suffix: str = ".txt") -> str:
        """Create a temporary file with content"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
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
            
            return f"🔍 Found {len(matches)} files matching '{pattern}':\n" + "\n".join(matches)
        except Exception as e:
            return f"❌ Error searching files: {str(e)}"

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
            
            return f"ℹ️ File Information for {filepath}:\n" + "\n".join(f"{k}: {v}" for k, v in info.items())
        except Exception as e:
            return f"❌ Error getting file info: {str(e)}"

