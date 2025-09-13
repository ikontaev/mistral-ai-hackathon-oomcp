# NOT REUQUIRED FOR MAIN FUNCTIONS
from fastmcp import FastMCP
from hcloud import Client
from hcloud.server_types import ServerType
from hcloud.images import Image
import os
from typing import Optional, List, Dict, Union

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
        labels: Optional[Dict[str, str]] = None
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
                labels=labels
            )

            server = response.server
            return (f"✅ Server created: {server.name} (ID: {server.id})\n"
                   f"Status: {server.status}\n"
                   f"IPv4: {server.public_net.ipv4.ip if server.public_net and server.public_net.ipv4 else 'N/A'}\n"
                   f"Root password: {response.root_password}")
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
                ip = server.public_net.ipv4.ip if server.public_net and server.public_net.ipv4 else "N/A"
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

            ipv4 = server.public_net.ipv4.ip if server.public_net and server.public_net.ipv4 else "N/A"
            ipv6 = server.public_net.ipv6.ip if server.public_net and server.public_net.ipv6 else "N/A"

            info = {
                "ID": server.id,
                "Name": server.name,
                "Status": server.status,
                "Created": server.created,
                "Server Type": server.server_type.name,
                "Datacenter": server.datacenter.name if server.datacenter else "N/A",
                "IPv4": ipv4,
                "IPv6": ipv6,
                "Backup Window": server.backup_window,
                "Rescue Enabled": server.rescue_enabled,
                "Protection": {
                    "Delete": server.protection.delete,
                    "Rebuild": server.protection.rebuild
                },
                "Labels": server.labels
            }

            return "ℹ️ Server Information:\n" + "\n".join(f"{k}: {v}" for k, v in info.items())
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
            return (f"✅ SSH key created: {ssh_key.name}\n"
                   f"ID: {ssh_key.id}\n"
                   f"Fingerprint: {ssh_key.fingerprint}")
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
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a new firewall"""
        try:
            # Convert rules to the format expected by the API
            api_rules = []
            if rules:
                for rule in rules:
                    api_rules.append({
                        "direction": rule.get("direction", "in"),
                        "protocol": rule.get("protocol"),
                        "port": rule.get("port"),
                        "source_ips": rule.get("source_ips", []),
                        "destination_ips": rule.get("destination_ips", []),
                        "description": rule.get("description", "")
                    })

            response = client.firewalls.create(
                name=name,
                firewall_type=firewall_type,
                labels=labels,
                apis=api_rules
            )

            firewall = response.firewall
            return (f"✅ Firewall created: {firewall.name} (ID: {firewall.id})\n"
                   f"Type: {firewall.firewall_type}")
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