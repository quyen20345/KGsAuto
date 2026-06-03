__all__ = ["GeminiClient", "OllamaClient", "OpenAICompatibleClient", "OpenAICompatibleProviderClient"]


def __getattr__(name: str):
    if name == "GeminiClient":
        from .gemini_client import GeminiClient

        return GeminiClient
    if name == "OllamaClient":
        from .ollama_client import OllamaClient

        return OllamaClient
    if name == "OpenAICompatibleClient":
        from .openai_compatible_client import OpenAICompatibleClient

        return OpenAICompatibleClient
    if name == "OpenAICompatibleProviderClient":
        from .openai_compatible_client import OpenAICompatibleProviderClient

        return OpenAICompatibleProviderClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
