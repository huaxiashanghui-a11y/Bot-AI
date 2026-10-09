import httpx
tg = "8945497286:AAHh9rULdb8zgRBUGq5zn4FhDHU_7kJY7Js"
r = httpx.get(f"https://api.telegram.org/bot{tg}/getMe", timeout=20)
print("TG getMe:", r.status_code, r.text[:300])
