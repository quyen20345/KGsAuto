from typing import Optional
from google import genai

from llms.base import BaseLLM
from llms.factory import register_llm
from llms.types import LLMResponse
from config import Config


@register_llm("gemini")
class GeminiClient(BaseLLM):
    def __init__(self, model_name: Optional[str] = None, **kwargs):
        self.model_name = model_name or Config.DEFAULT_MODEL
        # self.temperature = kwargs.get("temperature", Config.DEFAULT_TEMPERATURE)
        # self.top_p = kwargs.get("top_p", Config.DEFAULT_TOP_P)
        # self.max_tokens = kwargs.get("max_tokens", Config.DEFAULT_MAX_TOKENS)

        if not Config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set in .env file")
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        try:
            contents = [prompt] 
            
            # config for SDK
            config = {
                "system_instruction": system_prompt, 
                # "temperature": self.temperature,
            }

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