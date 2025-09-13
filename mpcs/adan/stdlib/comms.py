from fastmcp import FastMCP
import os
import json
import socket
from threading import Thread
import httpx
from typing import Union, List



def register(mcp): 
    @mcp.tool
    def send_email(
        to: Union[str, List[str]] = "noreplycristiansanchez@gmail.com",
        subject: str = "FastMCP / Resend test",
        html: str = "<h1>It works</h1><p>Sent via FastMCP + Resend.</p>",
        from_email: str = "Sender <verification@vultures.dev>",
    ) -> str:
        """Send an email given the following params: to, subject, html, from."""
        try:
            api_key = "re_UpgtLin8_4dUPGUUCngHNcJ2pKmkFCwEo"
            if not api_key:
                return "❌ Missing RESEND_API_KEY environment variable"

            # validar campos mínimos
            if not to:
                return "❌ 'to' is required"
            if not subject:
                return "❌ 'subject' is required"
            if not html:
                return "❌ 'html' is required"
            if not from_email:
                return "❌ 'from' is required"

            # normalizar destinatarios
            if isinstance(to, str):
                recipients = [r.strip() for r in to.split(",") if r.strip()]
            elif isinstance(to, (list, tuple)):
                recipients = [str(r).strip() for r in to if str(r).strip()]
            else:
                return "❌ 'to' must be a string or list of strings"

            if not recipients:
                return "❌ 'to' has no valid recipients"

            payload = {
                "from": from_email,
                "to": recipients,
                "subject": subject,
                "html": html,
            }

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    content=json.dumps(payload),
                )

            if resp.status_code in (200, 201):
                try:
                    data = resp.json()
                    email_id = data.get("id") or data.get("data", {}).get("id")
                except Exception:
                    email_id = None
                ok = f"✔️ Email sent to {', '.join(recipients)}"
                return ok + (f" (id: {email_id})" if email_id else "")
            else:
                try:
                    j = resp.json()
                    err = j.get("error") or j.get("message") or str(j)
                except Exception:
                    err = resp.text[:500]
                return f"🔴 Resend error {resp.status_code}: {err}"

        except httpx.HTTPError as e:
            return f"❌ HTTP error: {e}"
        except Exception as e:
            return f"❌ Unexpected error: {e}"



        
