# NOT REUQUIRED FOR MAIN FUNCTIONS
import json
import os
import subprocess
from typing import Dict, List, Optional, Union

import httpx
from fastmcp import FastMCP
from hcloud import Client
from hcloud.images import Image
from hcloud.server_types import ServerType
from pydantic import BaseModel, Field


class DeployConfig(BaseModel):
    """Configuration for deployment"""

    github_url: str = Field(..., description="GitHub repository URL")
    server_id: str = Field(..., description="Hetzner server ID to deploy to")
    image_name: Optional[str] = Field(
        None, description="Docker image name (defaults to repo name)"
    )
    port_mapping: Optional[str] = Field(
        "8080:8000", description="Port mapping (host:container)"
    )
    env_vars: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Environment variables"
    )


def register(mcp: FastMCP, config):
    # Initialize Hetzner Cloud client
    hcloud_token = os.getenv("HCLOUD_TOKEN")
    if not hcloud_token:
        hcloud_token = ""

    client = Client(token=hcloud_token)

    @mcp.tool
    def create_server(
        name: str,
        server_type: str = "cx22",
        image: str = "ubuntu-22.04",
        location: Optional[str] = None,
        ssh_keys: Optional[List[str]] = None,
        user_data: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a new Hetzner Cloud server"""
        try:
            # Convert SSH key names/IDs to SSH key objects if provided
            ssh_key_objects = None
            if ssh_keys:
                ssh_key_objects = []
                for key_identifier in ssh_keys:
                    try:
                        # Try to get by ID first
                        key = client.ssh_keys.get_by_id(int(key_identifier))
                    except:
                        try:
                            # If not an ID, try to get by name
                            key = client.ssh_keys.get_by_name(key_identifier)
                        except:
                            continue
                    if key:
                        ssh_key_objects.append(key)

            response = client.servers.create(
                name=name,
                server_type=ServerType(name=server_type),
                image=Image(name=image),
                location=location,
                ssh_keys=ssh_key_objects,
                user_data=user_data,
                labels=labels,
            )

            server = response.server
            return (
                f"✅ Server created: {server.name} (ID: {server.id})\n"
                f"Status: {server.status}\n"
                f"IPv4: {server.public_net.ipv4.ip if server.public_net and server.public_net.ipv4 else 'N/A'}\n"
                f"Root password: {response.root_password}"
            )
        except Exception as e:
            return f"❌ Error creating server: {str(e)}"

    @mcp.tool
    def list_servers() -> str:
        """List all Hetzner Cloud servers"""
        try:
            servers = client.servers.get_all()
            if not servers:
                return "ℹ️ No servers found"

            result = ["📋 Hetzner Cloud Servers:"]
            for server in servers:
                ip = (
                    server.public_net.ipv4.ip
                    if server.public_net and server.public_net.ipv4
                    else "N/A"
                )
                result.append(
                    f"ID: {server.id}, Name: {server.name}, "
                    f"Status: {server.status}, IP: {ip}, "
                    f"Type: {server.server_type.name}, "
                    f"Created: {server.created}"
                )
            return "\n".join(result)
        except Exception as e:
            return f"❌ Error listing servers: {str(e)}"

    @mcp.tool
    def delete_server(server_id: Union[int, str]) -> str:
        """Delete a Hetzner Cloud server"""
        try:
            server = client.servers.get_by_id(int(server_id))
            if not server:
                return f"❌ Server with ID {server_id} not found"

            server.delete()
            return f"✅ Server {server.name} (ID: {server.id}) deleted"
        except Exception as e:
            return f"❌ Error deleting server: {str(e)}"

    @mcp.tool
    def get_server_info(server_id: Union[int, str]) -> str:
        """Get detailed information about a server"""
        try:
            server = client.servers.get_by_id(int(server_id))
            if not server:
                return f"❌ Server with ID {server_id} not found"

            ipv4 = (
                server.public_net.ipv4.ip
                if server.public_net and server.public_net.ipv4
                else "N/A"
            )
            ipv6 = (
                server.public_net.ipv6.ip
                if server.public_net and server.public_net.ipv6
                else "N/A"
            )

            info = {
                "ID": server.id,
                "Name": server.name,
                "Status": server.status,
                "Created": server.created,
                "Server Type": server.server_type,
                "Datacenter": server.datacenter.name if server.datacenter else "N/A",
                "IPv4": ipv4,
                "IPv6": ipv6,
                "Backup Window": server.backup_window,
                "Rescue Enabled": server.rescue_enabled,
                "Labels": server.labels,
            }

            return "ℹ️ Server Information:\n" + "\n".join(
                f"{k}: {v}" for k, v in info.items()
            )
        except Exception as e:
            return f"❌ Error getting server info: {str(e)}"

    @mcp.tool
    def start_server(server_id: Union[int, str]) -> str:
        """Start a Hetzner Cloud server"""
        try:
            server = client.servers.get_by_id(int(server_id))
            if not server:
                return f"❌ Server with ID {server_id} not found"

            action = server.power_on()
            return f"✅ Starting server {server.name} (ID: {server.id})"
        except Exception as e:
            return f"❌ Error starting server: {str(e)}"

    @mcp.tool
    def stop_server(server_id: Union[int, str]) -> str:
        """Stop a Hetzner Cloud server"""
        try:
            server = client.servers.get_by_id(int(server_id))
            if not server:
                return f"❌ Server with ID {server_id} not found"

            action = server.power_off()
            return f"✅ Stopping server {server.name} (ID: {server.id})"
        except Exception as e:
            return f"❌ Error stopping server: {str(e)}"

    @mcp.tool
    def reboot_server(server_id: Union[int, str]) -> str:
        """Reboot a Hetzner Cloud server"""
        try:
            server = client.servers.get_by_id(int(server_id))
            if not server:
                return f"❌ Server with ID {server_id} not found"

            action = server.reboot()
            return f"✅ Rebooting server {server.name} (ID: {server.id})"
        except Exception as e:
            return f"❌ Error rebooting server: {str(e)}"

    @mcp.tool
    def create_ssh_key(name: str, public_key: str) -> str:
        """Create a new SSH key"""
        try:
            ssh_key = client.ssh_keys.create(name=name, public_key=public_key)
            return (
                f"✅ SSH key created: {ssh_key.name}\n"
                f"ID: {ssh_key.id}\n"
                f"Fingerprint: {ssh_key.fingerprint}"
            )
        except Exception as e:
            return f"❌ Error creating SSH key: {str(e)}"

    @mcp.tool
    def list_ssh_keys() -> str:
        """List all SSH keys"""
        try:
            keys = client.ssh_keys.get_all()
            if not keys:
                return "ℹ️ No SSH keys found"

            result = ["🔑 SSH Keys:"]
            for key in keys:
                result.append(
                    f"ID: {key.id}, Name: {key.name}, "
                    f"Fingerprint: {key.fingerprint}, "
                    f"Created: {key.created}"
                )
            return "\n".join(result)
        except Exception as e:
            return f"❌ Error listing SSH keys: {str(e)}"

    @mcp.tool
    def delete_ssh_key(key_id: Union[int, str]) -> str:
        """Delete an SSH key"""
        try:
            key = client.ssh_keys.get_by_id(int(key_id))
            if not key:
                return f"❌ SSH key with ID {key_id} not found"

            key.delete()
            return f"✅ SSH key {key.name} (ID: {key.id}) deleted"
        except Exception as e:
            return f"❌ Error deleting SSH key: {str(e)}"

    @mcp.tool
    def create_firewall(
        name: str,
        firewall_type: str = "ipv4",
        rules: Optional[List[Dict]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a new firewall"""
        try:
            # Convert rules to the format expected by the API
            api_rules = []
            if rules:
                for rule in rules:
                    api_rules.append(
                        {
                            "direction": rule.get("direction", "in"),
                            "protocol": rule.get("protocol"),
                            "port": rule.get("port"),
                            "source_ips": rule.get("source_ips", []),
                            "destination_ips": rule.get("destination_ips", []),
                            "description": rule.get("description", ""),
                        }
                    )

            response = client.firewalls.create(
                name=name, firewall_type=firewall_type, labels=labels, apis=api_rules
            )

            firewall = response.firewall
            return (
                f"✅ Firewall created: {firewall.name} (ID: {firewall.id})\n"
                f"Type: {firewall.firewall_type}"
            )
        except Exception as e:
            return f"❌ Error creating firewall: {str(e)}"

    @mcp.tool
    def list_firewalls() -> str:
        """List all firewalls"""
        try:
            firewalls = client.firewalls.get_all()
            if not firewalls:
                return "ℹ️ No firewalls found"

            result = ["🔥 Firewalls:"]
            for fw in firewalls:
                result.append(
                    f"ID: {fw.id}, Name: {fw.name}, "
                    f"Type: {fw.firewall_type}, "
                    f"Created: {fw.created}"
                )
            return "\n".join(result)
        except Exception as e:
            return f"❌ Error listing firewalls: {str(e)}"

    @mcp.tool
    def delete_firewall(firewall_id: Union[int, str]) -> str:
        """Delete a firewall"""
        try:
            firewall = client.firewalls.get_by_id(int(firewall_id))
            if not firewall:
                return f"❌ Firewall with ID {firewall_id} not found"

            firewall.delete()
            return f"✅ Firewall {firewall.name} (ID: {firewall.id}) deleted"
        except Exception as e:
            return f"❌ Error deleting firewall: {str(e)}"

    @mcp.tool
    def list_server_types() -> str:
        """List available server types"""
        try:
            types = client.server_types.get_all()
            if not types:
                return "ℹ️ No server types found"

            result = ["🖥️ Server Types:"]
            for st in types:
                result.append(
                    f"Name: {st.name}, "
                    f"Cores: {st.cores}, "
                    f"Memory: {st.memory}GB, "
                    f"Disk: {st.disk}GB, "
                    f"Price: {st.prices[0].price_monthly.gross} {st.prices[0].price_monthly.currency}"
                )
            return "\n".join(result)
        except Exception as e:
            return f"❌ Error listing server types: {str(e)}"

    @mcp.tool
    def list_images() -> str:
        """List available images"""
        try:
            images = client.images.get_all()
            if not images:
                return "ℹ️ No images found"

            result = ["💾 Images:"]
            for img in images:
                result.append(
                    f"Name: {img.name}, "
                    f"Type: {img.type}, "
                    f"Description: {img.description}, "
                    f"Created: {img.created}"
                )
            return "\n".join(result)
        except Exception as e:
            return f"❌ Error listing images: {str(e)}"

    @mcp.tool
    def deploy_from_github(
        github_url: str, server_id: str, port_mapping: str = "8080:8000"
    ) -> str:
        """Generate deployment script for GitHub repo to Hetzner server"""
        try:
            # Validate GitHub URL
            if not github_url.startswith(("https://github.com/", "http://github.com/")):
                return "❌ Error: Invalid GitHub URL format"

            # Extract repo info from URL
            url_parts = (
                github_url.replace("https://github.com/", "")
                .replace("http://github.com/", "")
                .strip("/")
            )
            if "/" not in url_parts:
                return "❌ Error: Invalid GitHub URL format"

            owner, repo = url_parts.split("/", 1)
            repo = repo.split("/")[0]  # Remove any trailing paths

            # Check if Dockerfile exists in the repo
            dockerfile_url = (
                f"https://api.github.com/repos/{owner}/{repo}/contents/Dockerfile"
            )
            with httpx.Client() as client_http:
                response = client_http.get(dockerfile_url)
                if response.status_code == 404:
                    return "❌ Error: Dockerfile not found in repository"
                elif response.status_code != 200:
                    return f"❌ Error: Failed to check repository (status: {response.status_code})"

            # Get server info
            server = client.servers.get_by_id(int(server_id))
            if not server:
                return f"❌ Server with ID {server_id} not found"

            server_ip = (
                server.public_net.ipv4.ip
                if server.public_net and server.public_net.ipv4
                else None
            )
            if not server_ip:
                return "❌ Server has no public IP address"

            image_name = repo.lower()
            script_filename = f"deploy_{repo}_{server_id}.sh"

            # Create deployment script
            deploy_script = f"""#!/bin/bash
set -e

echo "🚀 Starting deployment of {github_url}"

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Clone repository
echo "📥 Cloning repository..."
rm -rf /tmp/{repo}
git clone {github_url} /tmp/{repo}
cd /tmp/{repo}

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t {image_name} .

# Stop existing container if running
echo "🛑 Stopping existing container..."
docker stop {image_name} 2>/dev/null || true
docker rm {image_name} 2>/dev/null || true

# Run new container
echo "▶️ Starting new container..."
docker run -d --name {image_name} -p {port_mapping} --restart unless-stopped {image_name}

echo "✅ Deployment complete!"
echo "🌐 Application accessible at http://{server_ip}:{port_mapping.split(":")[0]}"
"""

            # Save script to local file
            script_path = f"/tmp/{script_filename}"
            with open(script_path, "w") as f:
                f.write(deploy_script)

            return f"""✅ Deployment script created for {github_url}

📋 Deployment Details:
- Repository: {owner}/{repo}
- Server: {server.name} ({server_ip})
- Port mapping: {port_mapping}
- Script: {script_path}

📝 To deploy, copy and run the script on your server:

1. Copy script to server:
   scp {script_path} root@{server_ip}:/tmp/

2. Execute on server:
   ssh root@{server_ip} 'chmod +x /tmp/{script_filename} && /tmp/{script_filename}'

🌐 After deployment, app will be accessible at: http://{server_ip}:{port_mapping.split(":")[0]}
"""

        except Exception as e:
            return f"❌ Error creating deployment script: {str(e)}"
