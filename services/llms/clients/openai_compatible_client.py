from typing import Dict, List, Optional

from openai import AsyncOpenAI, OpenAI

from services.config import OPENAI_COMPATIBLE_MODEL as _DEFAULT_OPENAI_MODEL
from services.config import settings
from services.llms.base import BaseLLM
from services.llms.factory import register_llm
from services.llms.types import LLMResponse


class OpenAICompatibleClient(BaseLLM):
    provider_name = "openai-compatible"
    api_key_env: Optional[str] = None
    base_url_env: Optional[str] = None
    default_base_url: Optional[str] = None
    default_api_key: Optional[str] = None

    def __init__(self, model_name: Optional[str] = None, **kwargs):
        self.model_name = model_name
        self.temperature = kwargs.get("temperature")
        self.host = kwargs.get("host") or kwargs.get("base_url") or self._setting(self.base_url_env) or self.default_base_url
        self.api_key = kwargs.get("api_key") or self._setting(self.api_key_env) or self.default_api_key

        if not self.host:
            raise ValueError(f"{self.provider_name} base URL is not set")
        if not self.api_key:
            raise ValueError(f"{self.provider_name} API key is not set")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.host,
            timeout=None,
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        try:
            messages: List[Dict[str, str]] = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if prompt:
                messages.append({"role": "user", "content": prompt})

            request_kwargs = {
                "model": self.model_name,
                "messages": messages,
            }
            effective_temperature = self.temperature if temperature is None else temperature
            if effective_temperature is not None:
                request_kwargs["temperature"] = effective_temperature

            response = self.client.chat.completions.create(**request_kwargs)

            usage_tokens = response.usage.total_tokens if response.usage else None
            response_model = getattr(response, "model", None) or self.model_name

            message = response.choices[0].message if response.choices else None
            content = message.content if message else None
            if not content and message is not None:
                content = getattr(message, "reasoning_content", None)
            if not content:
                content = self._extract_text_from_message_parts(message)
            if content is None:
                finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                content = (
                    f"{self.provider_name} returned empty assistant content "
                    f"(finish_reason={finish_reason})."
                )

            return LLMResponse(
                content=content,
                model=response_model,
                usage_tokens=usage_tokens,
            )
        except Exception as e:
            return LLMResponse(
                content=f"{self.provider_name} Error (host={self.host}): {str(e)}",
                model=self.model_name,
            )

    async def agenerate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Async generate text from prompt using AsyncOpenAI."""
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.host,
            timeout=None,
        )
        try:
            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if prompt:
                messages.append({"role": "user", "content": prompt})

            request_kwargs = {
                "model": self.model_name,
                "messages": messages,
            }
            effective_temperature = self.temperature if temperature is None else temperature
            if effective_temperature is not None:
                request_kwargs["temperature"] = effective_temperature

            response = await client.chat.completions.create(**request_kwargs)

            usage_tokens = response.usage.total_tokens if response.usage else None
            response_model = getattr(response, "model", None) or self.model_name

            message = response.choices[0].message if response.choices else None
            content = message.content if message else None
            if not content and message is not None:
                content = getattr(message, "reasoning_content", None)
            if not content:
                content = self._extract_text_from_message_parts(message)
            if content is None:
                finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                content = (
                    f"{self.provider_name} returned empty assistant content "
                    f"(finish_reason={finish_reason})."
                )

            return LLMResponse(
                content=content,
                model=response_model,
                usage_tokens=usage_tokens,
            )
        except Exception as e:
            return LLMResponse(
                content=f"{self.provider_name} Error (host={self.host}): {str(e)}",
                model=self.model_name,
            )
        finally:
            try:
                await client.close()
            except Exception:
                pass

    @staticmethod
    def _setting(name: Optional[str]) -> Optional[str]:
        values = {
            "OPENAI_COMPATIBLE_API_KEY": settings.llm.openai_compatible_api_key,
            "OPENAI_COMPATIBLE_BASE_URL": settings.llm.openai_compatible_base_url,
            "OPENAI_API_KEY": settings.llm.openai_api_key,
            "OPENAI_BASE_URL": settings.llm.openai_base_url,
            "GOOGLE_API_KEY": settings.llm.google_api_key,
        }
        return values.get(name) if name else None

    @staticmethod
    def _extract_text_from_message_parts(message) -> Optional[str]:
        if message is None:
            return None

        parts = getattr(message, "content", None)
        if isinstance(parts, str):
            return parts

        if not isinstance(parts, list):
            return None

        text_chunks = []
        for part in parts:
            if isinstance(part, dict):
                if part.get("type") == "text" and isinstance(part.get("text"), str):
                    text_chunks.append(part["text"])
            else:
                part_type = getattr(part, "type", None)
                part_text = getattr(part, "text", None)
                if part_type == "text" and isinstance(part_text, str):
                    text_chunks.append(part_text)

        return "".join(text_chunks) if text_chunks else None


@register_llm("OpenAICompatible")
class OpenAICompatibleProviderClient(OpenAICompatibleClient):
    provider_name = "OpenAICompatible"
    api_key_env = "OPENAI_COMPATIBLE_API_KEY"
    base_url_env = "OPENAI_COMPATIBLE_BASE_URL"
    default_base_url = settings.llm.openai_compatible_base_url or "http://localhost:20128/v1"


if __name__ == "__main__":
    demo_model = _DEFAULT_OPENAI_MODEL or "cx/gpt-5.3-codex"
    client = OpenAICompatibleProviderClient(demo_model)
    print(client.generate("why is the sky blue?"))
