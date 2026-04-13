# LLMs Module

Module `llms/` cung cap mot abstraction nho gon de goi nhieu nha cung cap LLM qua cung 1 interface.

## 1) Muc tieu

- Dung 1 ham `get_llm()` de tao client theo provider.
- Chuan hoa output theo `LLMResponse`.
- De mo rong them provider moi bang decorator `@register_llm("...")`.

## 2) Cau truc thu muc

```text
llms/
|- __init__.py
|- base.py
|- factory.py
|- types.py
'- clients/
   |- __init__.py
   |- gemini_client.py
   |- ollama_client.py
   |- proxypal_client.py
   '- router9_client.py
```

## 3) Providers hien co

- `proxypal`: OpenAI-compatible endpoint (mac dinh `http://localhost:8317/v1`)
- `9router`: OpenAI-compatible endpoint (mac dinh `http://localhost:20128/v1`)
- `gemini`: Google GenAI SDK
- `ollama`: Ollama local server (mac dinh `http://localhost:11434`)

Tat ca clients duoc auto-register khi import package `llms` (qua `llms/clients/__init__.py`).

## 4) API chinh

### Tao client

```python
from llms import get_llm

llm = get_llm("proxypal", model_name="gpt-5")
```

### Generate

```python
resp = llm.generate("why is the sky blue?")
print(resp.content)
print(resp.model)
print(resp.usage_tokens)
```

### Co system prompt

```python
resp = llm.generate(
    prompt="Tom tat doan van sau",
    system_prompt="Ban la tro ly ky thuat, tra loi ngan gon va chinh xac."
)
```

## 5) Bien moi truong

### Proxypal

- `PROXYPAL_KEY` (optional, fallback: `proxypal-local`)
- `PROXYPAL_BASE_URL` (optional, fallback: `http://localhost:8317/v1`)

### 9router

- `ROUTER9_API_KEY` (required)
- `ROUTER9_BASE_URL` (optional, fallback: `http://localhost:20128/v1`)

### Gemini

- `GOOGLE_API_KEY` (required)
- `DEFAULT_MODEL` (optional, dung khi khong truyen `model_name`)

### Ollama

- Khong bat buoc env var; host co the override qua `host=...`

## 6) Provider-specific examples

```python
from llms import get_llm

# Proxypal
pp = get_llm("proxypal", model_name="gpt-5")

# 9router
r9 = get_llm("9router", model_name="gpt-5")

# Gemini
gm = get_llm("gemini", model_name="gemini-2.5-flash")

# Ollama
ol = get_llm("ollama", model_name="gemma3", host="http://localhost:11434")
```

## 7) Cac type du lieu

- `Message(role, content)`
- `LLMResponse(content, model, usage_tokens=None)`
- `APIKeyEntry(...)` (metadata cho quan ly key)

## 8) Cach mo rong provider moi

1. Tao file moi trong `llms/clients/`, ke thua `BaseLLM`.
2. Gan decorator `@register_llm("ten_provider")`.
3. Implement `generate(prompt, system_prompt=None)`.
4. Tra ve `LLMResponse`.
5. Import client moi trong `llms/clients/__init__.py` de auto-register.

Mau toi thieu:

```python
from typing import Optional
from llms.base import BaseLLM
from llms.factory import register_llm
from llms.types import LLMResponse

@register_llm("my_provider")
class MyProviderClient(BaseLLM):
    def __init__(self, model_name: Optional[str] = None, **kwargs):
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        return LLMResponse(content="...", model=self.model_name)
```

## 9) Luu y van hanh

- `get_llm()` se bao loi neu provider khong ton tai trong registry.
- Cac client hien tai bat exception va tra thong diep loi trong `LLMResponse.content`.
- Rieng `GeminiClient` se raise `ValueError` ngay luc init neu thieu `GOOGLE_API_KEY`.

## 10) Noi dang su dung module nay

- `extractv2/extractv2.py`
- `demo_phase1.py`
