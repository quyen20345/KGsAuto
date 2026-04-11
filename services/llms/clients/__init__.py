# Import all clients to trigger the @register_llm decorator
from .gemini_client import GeminiClient
from .ollama_client import OllamaClient
from .proxypal_client import ProxypalClient

__all__ = ["GeminiClient", "OllamaClient", "ProxypalClient"]
