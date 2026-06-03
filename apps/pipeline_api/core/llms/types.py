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
    
@dataclass
class APIKeyEntry:
    provider: str
    api_key: str
    failure_count: int=0
    cooldown_until: float=0.0
    total_requests: int=0