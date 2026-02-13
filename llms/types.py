from dataclasses import dataclass
from typing import Optional

@dataclass
class Message:
    role: str
    content: str

@dataclass
class LLMResponse:
    content: str
    model: str
    usage_tokens: Optional[int] = None 