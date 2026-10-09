import httpx, json
r = httpx.post(
    "https://api.deepseek.com/chat/completions",
    headers={"Authorization": "Bearer sk-e39a5ee6c7834083ad626d6079f939d7"},
    json={
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "用一句话回答：你好"}],
        "max_tokens": 50,
    },
    timeout=60,
)
print("STATUS", r.status_code)
print(r.text[:800])
