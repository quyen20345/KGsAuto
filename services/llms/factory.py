from importlib import import_module
from typing import Dict, Type

from services.llms.base import BaseLLM

# Registry for LLM clients
REGISTRY: Dict[str, Type[BaseLLM]] = {}
_CLIENTS_REGISTERED = False
_CLIENT_MODULES = (
    "services.llms.clients.gemini_client",
    "services.llms.clients.ollama_client",
    "services.llms.clients.proxypal_client",
    "services.llms.clients.router9_client",
)


def register_llm(name: str):
    """Decorator to register LLM clients."""
    def decorator(cls):
        REGISTRY[name] = cls
        return cls
    return decorator


def _ensure_clients_registered() -> None:
    """Import client modules once so decorators can populate the registry."""
    global _CLIENTS_REGISTERED
    if _CLIENTS_REGISTERED:
        return

    for module_path in _CLIENT_MODULES:
        import_module(module_path)

    _CLIENTS_REGISTERED = True


def get_llm(provider: str, **kwargs) -> BaseLLM:
    """Get LLM client by provider name."""
    _ensure_clients_registered()

    if provider not in REGISTRY:
        raise ValueError(f"Unsupported provider: {provider}. Available: {list(REGISTRY.keys())}")
    return REGISTRY[provider](**kwargs)
