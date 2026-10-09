import json

import httpx

from .. import config

def _headers(api_key: str):
    return {"Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"}

def _endpoint(base_url: str) -> str:
    """统一拼成 /chat/completions 完整地址。"""
    base = (base_url or config.ARK_ENDPOINT).rstrip("/")
    if not base.endswith("/chat/completions"):
        base = base + "/chat/completions"
    return base

async def chat(messages, api_key: str, model: str,
               temperature: float = 0.7, max_tokens: int = 2048,
               base_url: str = ""):
    """普通文本对话，返回 (文本, usage dict)。"""
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens, "stream": False}
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(_endpoint(base_url), json=payload, headers=_headers(api_key))
        resp.raise_for_status()
        data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return content, data.get("usage", {})

async def chat_vision(messages, api_key: str, vision_model: str,
                      temperature: float = 0.7, max_tokens: int = 2048,
                      base_url: str = ""):
    """多模态识图：messages 中 user content 为 [{type:text},{type:image_url}]。"""
    payload = {"model": vision_model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens, "stream": False}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(_endpoint(base_url), json=payload, headers=_headers(api_key))
        resp.raise_for_status()
        data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return content, data.get("usage", {})

async def chat_stream(messages, api_key: str, model: str,
                      temperature: float = 0.7, max_tokens: int = 2048,
                      base_url: str = ""):
    """流式对话 async generator：yield (delta_text, usage_or_none)。"""
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens, "stream": True,
               "stream_options": {"include_usage": True}}
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", _endpoint(base_url), json=payload,
                                 headers=_headers(api_key)) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                usage = chunk.get("usage")
                choices = chunk.get("choices") or []
                delta = ""
                if choices:
                    delta = (choices[0].get("delta") or {}).get("content") or ""
                yield delta, usage
