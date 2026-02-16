import os
import json
import requests
from typing import Any, Optional

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

def generate_text_stream(prompt: str, model: Optional[str] = None, temperature: float = 0.2):
    url = f"{OLLAMA_HOST}/api/generate"

    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "temperature": temperature
    }

    with requests.post(url, json=payload, stream=True, timeout=180) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            obj = json.loads(line)
            chunk = obj.get("response", "")
            if chunk:
                yield chunk
            if obj.get("done"):
                break

def generate_text( prompt: str, model: Optional[str] = None, temperature: float = 0.2,) -> str:
    return "".join(generate_text_stream(prompt, model=model, temperature=temperature))


def generate_json(prompt: str, model: Optional[str] = None, temperature: float = 0.0) -> Any:
    url  = f"{OLLAMA_HOST}/api/generate"

    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    r = requests.post(url, json=payload, timeout=180)
    r.raise_for_status()

    txt = (r.json().get("response") or "").strip()

    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end != -1 and end  > start:
            return json.loads(txt[start : end + 1])
        raise