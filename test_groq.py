import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

resp = httpx.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
    json={
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": "say hi"}],
    },
)
print(resp.status_code)
print(resp.text)