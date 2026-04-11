from typing import Optional 
from ollama import Client
from services.llms.base import BaseLLM
from services.llms.factory import register_llm
from services.llms.types import LLMResponse, Message
import os

@register_llm("ollama")
class OllamaClient(BaseLLM):
  def __init__(self, model_name: Optional[str] = None, **kwargs):
    self.model_name = model_name
    self.host = kwargs.get("host", "http://localhost:11434")
    self.client = Client(host=self.host)
    self.options = {
    }
    
    
  def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
    try:
      messages = []
      if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
        
      messages.append({'role': 'user', 'content': prompt})
      
      response = self.client.chat(
        model=self.model_name,
        messages=messages,
        options=self.options
      )
      
      # Ollama tokens = prompt_eval (input) + eval (output)
      total_tokens = getattr(response, "prompt_eval_count", 0) + getattr(response, 'eval_count', 0)
      
      return LLMResponse(
        content=response.message.content,
        model=self.model_name,
        usage_tokens=total_tokens if total_tokens > 0 else None
      )
    except Exception as e:
      return LLMResponse(
        content=f"Error {str(e)}",
        model=self.model_name
      )
    
    
# fast test
# if __name__ == "__main__":
#   client = OllamaClient("gemma3")
#   print(client.generate("why is the sky blue?"))