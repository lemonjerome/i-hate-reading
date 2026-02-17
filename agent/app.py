import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import requests
from qdrant_client import QdrantClient

from rag.ingestion import ingest_document
from rag.retrieval import retrieve
from rag.pipeline import answer_question_stream

app = FastAPI()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://qdrant:6333")

OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"
client = QdrantClient(url=QDRANT_HOST)

class AskRequest(BaseModel):
    question: str

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

@app.get("/test-qdrant")
def test_qdrant():
    return {"collections": client.get_collections()}

@app.post("/ingest")
def ingest_endpoint(data: dict):
    return ingest_document(data["text"], data["source"])

@app.post("/retrieve")
def retrieve_endpoint(query: str):
    return retrieve(query)

@app.delete("/clear")
def clear_collection():
    try:
        client.delete_collection(collection_name="notebook_docs")
        return {"status": "collection deleted"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post("/ask")
def ask(req: AskRequest):
    def ndjson_iter():
        for msg in answer_question_stream(req.question):
            yield json.dumps(msg, ensure_ascii=False) + "\n"

    return StreamingResponse(
        ndjson_iter(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        },
    )

