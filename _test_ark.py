import httpx
key = "ark-d9b44e6f-9917-42c4-b087-8f99b10fca4b-ef242"
for model in ["doubao-pro-4k", "doubao-pro-32k", "doubao-1.5-pro-32k", "doubao-vision-pro-32k"]:
    try:
        r = httpx.post(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 20},
            timeout=30,
        )
        if r.status_code == 200:
            print(model, "-> OK:", r.json()["choices"][0]["message"]["content"][:30])
        else:
            print(model, "->", r.status_code, r.text[:160])
    except Exception as e:
        print(model, "-> ERR", repr(e))
