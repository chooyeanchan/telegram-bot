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


def chat(messages, think=False):
    r = requests.post(
        f"{config.OLLAMA_URL}/api/chat",
        json={
            "model": config.CHAT_MODEL,
            "messages": messages,
            "stream": False,
            "think": think,
            "options": {"num_ctx": 8192, "temperature": 0.3},
        },
        timeout=600,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]
