import requests

import config


def embed(texts):
    """텍스트 리스트 → 임베딩 벡터 리스트"""
    r = requests.post(
        f"{config.OLLAMA_URL}/api/embed",
        json={"model": config.EMBED_MODEL, "input": texts},
        timeout=600,
    )
    r.raise_for_status()
    return r.json()["embeddings"]


def chat(messages, think=False, json_mode=False, temperature=0.3):
    body = {
        "model": config.CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "think": think,
        "options": {"num_ctx": 8192, "temperature": temperature},
    }
    if json_mode:
        body["format"] = "json"
    r = requests.post(f"{config.OLLAMA_URL}/api/chat", json=body, timeout=600)
    r.raise_for_status()
    return r.json()["message"]["content"]
