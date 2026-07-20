from datetime import datetime
from typing import Any, Callable, Dict, List

import httpx


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

# A dictionary to look up functions by name
TOOL_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "get_current_time": get_current_time,
    "get_github_profile": get_github_profile,
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
    }
]

# The list of Python functions for Gemini
GEMINI_TOOLS: List[Callable[..., Any]] = [get_current_time, get_github_profile]
