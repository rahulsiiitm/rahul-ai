from typing import List, Any, Optional
from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: Optional[str] = ""
    parts: Optional[List[Any]] = None

class ChatRequest(BaseModel):
    messages: List[Message]
