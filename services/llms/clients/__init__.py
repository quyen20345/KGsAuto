__all__ = ["GeminiClient", "OllamaClient", "ProxypalClient", "Router9Client"]


def __getattr__(name: str):
    if name == "GeminiClient":
        from .gemini_client import GeminiClient

        return GeminiClient
    if name == "OllamaClient":
        from .ollama_client import OllamaClient

        return OllamaClient
    if name == "ProxypalClient":
        from .proxypal_client import ProxypalClient

        return ProxypalClient
    if name == "Router9Client":
        from .router9_client import Router9Client

        return Router9Client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
