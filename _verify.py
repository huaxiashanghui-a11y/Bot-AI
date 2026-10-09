import httpx
BASE = "http://127.0.0.1:8000"

# 1. 登录
tok = httpx.post(f"{BASE}/api/admin/login",
                 json={"username":"admin","password":"admin123"}).json()["access_token"]
h = {"Authorization": f"Bearer {tok}"}
print("1. 登录 ✅ JWT:", tok[:20], "...")

# 2. 数据大盘
s = httpx.get(f"{BASE}/api/dashboard/summary", headers=h).json()
print("2. 数据大盘 ✅", s)

# 3. Bot列表
b = httpx.get(f"{BASE}/api/bot/list", headers=h).json()
print("3. Bot列表 ✅ 共", b["total"], "条 ->", b["items"][0]["bot_name"], b["items"][0]["ark_model_id"])

# 4. TG用户列表
u = httpx.get(f"{BASE}/api/user/list", headers=h).json()
print("4. TG用户 ✅ 共", u.get("total"), "条")

# 5. 对话记录
c = httpx.get(f"{BASE}/api/chat/list", headers=h).json()
print("5. 对话记录 ✅ 共", c.get("total"), "条")

# 6. 操作日志
l = httpx.get(f"{BASE}/api/log/list", headers=h).json()
print("6. 操作日志 ✅ 共", l.get("total"), "条")

# 7. 管理员列表
a = httpx.get(f"{BASE}/api/admin/list", headers=h).json()
print("7. 管理员 ✅ 共", len(a) if isinstance(a,list) else a)

# 8. 系统配置
sc = httpx.get(f"{BASE}/api/system/config", headers=h).json()
print("8. 系统配置 ✅", sc)

# 9. Token报表
t = httpx.get(f"{BASE}/api/stat/list", headers=h).json()
print("9. Token报表 ✅", t)

# 10. 进程状态
p = httpx.get(f"{BASE}/api/bot/process/status", headers=h).json()
print("10. Bot进程 ✅ 运行中:", p)
