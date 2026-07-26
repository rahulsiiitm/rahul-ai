from datetime import datetime
from typing import Any, Callable, Dict, List

import httpx
import os

def get_current_time() -> str:
    """Returns the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_github_profile(username: str) -> str:
    """Fetches public information about a GitHub user, including public repos and followers.
    
    Args:
        username: The GitHub username to look up.
    """
    try:
        r = httpx.get(f"https://api.github.com/users/{username}", timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            return (f"User: {data.get('login')} | Name: {data.get('name')} | "
                    f"Public Repos: {data.get('public_repos')} | "
                    f"Followers: {data.get('followers')} | "
                    f"Bio: {data.get('bio')}")
        return f"Could not fetch profile, status code: {r.status_code}"
    except Exception as e:
        return f"Error fetching github profile: {str(e)}"

def notify_chief_of_lead(email: str, message: str) -> str:
    """Notifies Rahul about a new lead or hiring inquiry.
    
    Args:
        email: The email address of the visitor.
        message: The context or message from the visitor about why they are reaching out.
    """
    webhook_url = os.environ.get("LEAD_WEBHOOK_URL")
    print(f"[LEAD EXTRACTED] Email: {email} | Intent: {message}")
    
    if not webhook_url:
        return "Webhook URL not configured in backend, but lead was logged successfully to the server console."
        
    try:
        # Assuming standard Discord/Slack webhook format
        payload = {
            "content": f"🚨 **New Lead from Zero Bot!**\n**Email:** {email}\n**Message:** {message}"
        }
        r = httpx.post(webhook_url, json=payload, timeout=10.0)
        if r.status_code in [200, 204]:
            return "Lead successfully forwarded to the Chief."
        return f"Failed to send lead, status code: {r.status_code}"
    except Exception as e:
        return f"Error sending lead: {str(e)}"


# A dictionary to look up functions by name
TOOL_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "get_current_time": get_current_time,
    "get_github_profile": get_github_profile,
    "notify_chief_of_lead": notify_chief_of_lead,
}

# The schemas for OpenAI / xAI
OPENAI_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Returns the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_github_profile",
            "description": "Fetches public information about a GitHub user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "The GitHub username to look up."
                    }
                },
                "required": ["username"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notify_chief_of_lead",
            "description": "Notifies Rahul about a new lead or hiring inquiry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "The email address of the visitor."
                    },
                    "message": {
                        "type": "string",
                        "description": "The context or message from the visitor about why they are reaching out."
                    }
                },
                "required": ["email", "message"]
            }
        }
    }
]

# The list of Python functions for Gemini
GEMINI_TOOLS: List[Callable[..., Any]] = [get_current_time, get_github_profile, notify_chief_of_lead]
