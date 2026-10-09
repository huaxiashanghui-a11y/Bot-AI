import httpx
key = "ark-d9b44e6f-9917-42c4-b087-8f99b10fca4b-ef242"
r = httpx.get("https://ark.cn-beijing.volces.com/api/v3/models",
              headers={"Authorization": f"Bearer {key}"}, timeout=30)
data = r.json().get("data", [])
print("total models:", len(data))
print("=== non-shutdown ===")
for m in data:
    st = m.get("status", "")
    if st and st != "Shutdown":
        print(m["id"], "|", st, "|", m.get("modalities", ""))
