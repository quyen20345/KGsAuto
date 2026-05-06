from abc import ABC, abstractmethod
from typing import Optional
from services.llms.types import LLMResponse

class BaseLLM(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text from prompt."""
        pass

    async def agenerate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Async generate text from prompt. Default: run sync in thread."""
        import asyncio
        return await asyncio.to_thread(self.generate, prompt, system_prompt)
