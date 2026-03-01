from llms import BaseLLM
from typing import Optional, List, Dict
from openai import OpenAI
from config import Config
from llms import LLMResponse, Message

class ProxypalClient(BaseLLM):
    def __init__(self, model_name : Optional[str] = None, **kwargs):
        self.model_name = model_name
        self.host = kwargs.get("host", "http://localhost:8317/v1")
        self.client = OpenAI(
            api_key = Config.PROXYPAL_KEY or 'proxypal-local',
            base_url = self.host,
            timeout = None,
        )
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        try:
            messages: List[Dict[str, str]] = []

            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            if prompt:
                messages.append({
                        'role': 'user',
                        'content': prompt
                    })

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
            )

            usage_tokens = response.usage.total_tokens if response.usage else None 

            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.model_name,
                usage_tokens=usage_tokens
            )
        except Exception as e:
            return LLMResponse(
                f"Proxypal Error: {str(e)}", 
                model=self.model_name
            )
            
            
# if __name__=="__main__":
#   client = ProxypalClient("gemini-2.5-flash") # gemini-2.5-flash gemini-claude-sonnet-4-5
#   print(client.generate("why is the sky blue?"))