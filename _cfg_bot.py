import httpx, json

BASE = "http://127.0.0.1:8000"
# 登录
login = httpx.post(f"{BASE}/api/admin/login",
                   json={"username": "admin", "password": "admin123"}).json()
tok = login["access_token"]
h = {"Authorization": f"Bearer {tok}"}

body = {
    "bot_name": "豆包助手",
    "tg_bot_token": "",            # 留空保留原Token
    "ark_api_key": "sk-e39a5ee6c7834083ad626d6079f939d7",
    "ark_model_id": "deepseek-chat",
    "vision_model_id": "",         # DeepSeek无视觉模型，先留空
    "base_url": "https://api.deepseek.com",
    "system_prompt": "你是一个乐于助人的Telegram智能助手，回答简洁友好。",
    "temperature": 0.7,
    "max_tokens": 1024,
    "stream_enable": True,         # 流式打字效果
    "bot_switch": True,
    "user_max_context_len": 10,
    "description": "对接DeepSeek",
}
r = httpx.put(f"{BASE}/api/bot/update/1", headers=h, json=body)
print("UPDATE", r.status_code, r.text)

# 查看进程状态
r2 = httpx.get(f"{BASE}/api/bot/process/status", headers=h)
print("PROCESS", r2.status_code, r2.text)
