from importlib import import_module
from typing import Dict, Type

from apps.pipeline_api.core.llms.base import BaseLLM

# Registry for LLM clients
REGISTRY: Dict[str, Type[BaseLLM]] = {}
_CLIENTS_REGISTERED = False
_CLIENT_MODULES = (
    "apps.pipeline_api.core.llms.clients.gemini_client",
    "apps.pipeline_api.core.llms.clients.ollama_client",
    "apps.pipeline_api.core.llms.clients.openai_compatible_client",
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
