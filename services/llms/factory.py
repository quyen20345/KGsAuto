from typing import Dict, Type
from services.llms.base import BaseLLM

# Registry for LLM clients
REGISTRY: Dict[str, Type[BaseLLM]] = {}


def register_llm(name: str):
    """Decorator to register LLM clients."""
    def decorator(cls):
        REGISTRY[name] = cls
        return cls
    return decorator


def get_llm(provider: str, **kwargs) -> BaseLLM:
    """Get LLM client by provider name."""
    if provider not in REGISTRY:
        raise ValueError(f"Unsupported provider: {provider}. Available: {list(REGISTRY.keys())}")
    return REGISTRY[provider](**kwargs)
