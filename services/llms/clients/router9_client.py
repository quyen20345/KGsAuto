import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from services.llms.base import BaseLLM
from services.llms.factory import register_llm
from services.llms.types import LLMResponse

load_dotenv()


@register_llm("9router")
class Router9Client(BaseLLM):
    def __init__(self, model_name: Optional[str] = None, **kwargs):
        self.model_name = model_name
        self.host = kwargs.get("host") or os.getenv("ROUTER9_BASE_URL") or "http://localhost:20128/v1"
        self.api_key = kwargs.get("api_key") or os.getenv("ROUTER9_API_KEY") or "sk-2c8a5a86cb957baf-oo8f99-366bc10b"

        if not self.api_key:
            raise ValueError("ROUTER9_API_KEY is not set")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.host,
            timeout=None,
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        try:
            messages: List[Dict[str, str]] = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if prompt:
                messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
            )

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
                    "9router returned empty assistant content "
                    f"(finish_reason={finish_reason})."
                )

            return LLMResponse(
                content=content,
                model=response_model,
                usage_tokens=usage_tokens,
            )
        except Exception as e:
            return LLMResponse(
                content=f"9router Error (host={self.host}): {str(e)}",
                model=self.model_name,
            )

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


if __name__ == "__main__":
    demo_model = os.getenv("ROUTER9_MODEL", "cx/gpt-5.3-codex")
    client = Router9Client(demo_model)
    print(client.generate("why is the sky blue?"))
