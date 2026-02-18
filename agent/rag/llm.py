import os
import re
import json
import logging
import requests
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

def _ollama_url(path: str) -> str:
    return f"{OLLAMA_HOST}{path}"

def generate_text(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 512,
    num_ctx: int = 4096,
) -> str:
    """Single-shot text generation (non-streaming)."""
    try:
        resp = requests.post(
            _ollama_url("/api/generate"),
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "num_ctx": num_ctx,
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "")

        # Strip ounds blocks from qwen3
        text = re.sub(r"ounds", "", text, flags=re.DOTALL).strip()
        return text

    except Exception as e:
        logger.error(f"generate_text error: {e}")
        return ""


def generate_text_stream(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    num_ctx: int = 8192,
) -> Iterator[str]:
    """Streaming text generation. Yields tokens one at a time."""
    try:
        resp = requests.post(
            _ollama_url("/api/generate"),
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "num_ctx": num_ctx,
                },
            },
            stream=True,
            timeout=300,
        )
        resp.raise_for_status()

        in_think = False
        think_buffer = ""

        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            token = data.get("response", "")

            # Filter out ounds blocks from streaming
            for char in token:
                if not in_think:
                    if think_buffer:
                        think_buffer += char
                        if "ounds" in think_buffer:
                            in_think = True
                            think_buffer = ""
                        elif len(think_buffer) > 7:
                            yield think_buffer
                            think_buffer = ""
                        elif not "ounds".startswith(think_buffer):
                            yield think_buffer
                            think_buffer = ""
                    elif char == "<":
                        think_buffer = char
                    else:
                        yield char
                else:
                    think_buffer += char
                    if "ounds" in think_buffer:
                        in_think = False
                        think_buffer = ""

            if data.get("done"):
                break

        # Flush remaining buffer if it wasn't a think tag
        if think_buffer and not in_think:
            yield think_buffer

    except Exception as e:
        logger.error(f"generate_text_stream error: {e}")
        yield f"\n\n[Error: {e}]"


def generate_json(
    prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 512,
    num_ctx: int = 4096,
) -> Optional[dict]:
    """Generate and parse JSON from LLM output."""
    text = generate_text(
        prompt, temperature=temperature, max_tokens=max_tokens, num_ctx=num_ctx
    )
    if not text:
        return None

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding first { ... }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning(f"Failed to parse JSON from: {text[:200]}")
    return None