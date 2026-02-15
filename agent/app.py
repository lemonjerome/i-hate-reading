from fastapi import FastAPI
import requests

app = FastAPI()

OLLAMA_URL = "http://ollama:11434/api/generate"

@app.get("/")
def root():
    return {"status": "notebook-agent running"}

@app.get("/test-llm")
def test_llm():
    response = requests.post(
        OLLAMA_URL,
        json = {
            "model": "qwen3:8b",
            "prompt": "Say hello from Qwen",
            "stream": False
        }
    )

    return response.json()

@app.get("/test-stream")
def test_stream():
    response = requests.post(
        OLLAMA_URL,
        json = {
            "model": "qwen3:8b",
            "prompt": "Say hello from Qwen",
            "stream": True
        },
        stream=True
    )

    return response.text