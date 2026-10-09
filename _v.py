import httpx
BASE = "http://127.0.0.1:8000"
tok = httpx.post(f"{BASE}/api/admin/login", json={"username":"admin","password":"admin123"}).json()["access_token"]
h = {"Authorization": f"Bearer {tok}"}
print("1. login ok")
s = httpx.get(f"{BASE}/api/dashboard/summary", headers=h).json(); print("2. dashboard:", s)
b = httpx.get(f"{BASE}/api/bot/list", headers=h).json(); print("3. bot:", b["items"][0]["bot_name"], b["items"][0]["ark_model_id"])
u = httpx.get(f"{BASE}/api/user/list", headers=h).json(); print("4. users total:", u.get("total"))
c = httpx.get(f"{BASE}/api/chat/list", headers=h).json(); print("5. chats total:", c.get("total"))
l = httpx.get(f"{BASE}/api/log/list", headers=h).json(); print("6. logs total:", l.get("total"))
p = httpx.get(f"{BASE}/api/bot/process/status", headers=h).json(); print("7. process:", p)
