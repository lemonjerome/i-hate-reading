from fastapi import FastAPI
import requests
from qdrant_client import QdrantClient
from rag.ingestion import ingest_document
from rag.retrieval import retrieve

app = FastAPI()

OLLAMA_URL = "http://ollama:11434/api/generate"

client = QdrantClient(url="http://qdrant:6333")

@app.get("/")
def root():
    return {"status": "notebook-agent running"}

# @app.get("/test-llm")
# def test_llm():
#     response = requests.post(
#         OLLAMA_URL,
#         json = {
#             "model": "qwen3:8b",
#             "prompt": "Say hello from Qwen",
#             "stream": False
#         }
#     )

#     return response.json()

# @app.get("/test-stream")
# def test_stream():
#     response = requests.post(
#         OLLAMA_URL,
#         json = {
#             "model": "qwen3:8b",
#             "prompt": "Say hello from Qwen",
#             "stream": True
#         },
#         stream=True
#     )

#     return response.text

# @app.get("/test-qdrant")
# def test_qdrant():
#     return {"collections": client.get_collections()}

@app.post("/ingest")
def ingest(data: dict):
    return ingest_document(data["text"], data["source"])

@app.post("/retrieve")
def retrieve_endpoint(query: str):
    return retrieve(query)