from services.config import settings
from typing import Optional
from google import genai

from services.llms.base import BaseLLM
from services.llms.factory import register_llm
from services.llms.types import LLMResponse


@register_llm("gemini")
class GeminiClient(BaseLLM):
    def __init__(self, model_name: Optional[str] = None, **kwargs):
        self.model_name = model_name or settings.llm.default_model
        if not settings.llm.google_api_key:
            raise ValueError("GOOGLE_API_KEY not set in .env file")
        self.client = genai.Client(api_key=settings.llm.google_api_key)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        try:
            contents = [prompt] 
            
            # config for SDK
            config = {
                "system_instruction": system_prompt,
            }
            if temperature is not None:
                config["temperature"] = temperature

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            
            usage = getattr(response, 'usage_metadata', None)
            total_tokens = usage.total_token_count if usage else None
            
            return LLMResponse(
                content=response.text,
                model=self.model_name,
                usage_tokens=total_tokens
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model_name
            )



# if __name__ == "__main__":
#     client = GeminiClient("gemini-2.5-flash")
#     print(client.generate("why is the sky blue?"))