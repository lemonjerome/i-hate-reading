import os
import json

from pydantic import BaseModel
from qdrant_client import QdrantClient
from typing import List

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from rag.ingestion import ingest_document
from rag.retrieval import retrieve
from rag.pipeline import answer_question_stream

app = FastAPI()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://qdrant:6333")

OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"
client = QdrantClient(url=QDRANT_HOST)

app.mount("/static", StaticFiles(directory="static"), name="static")

class AskRequest(BaseModel):
    question: str
    chat_history: List[dict] = []
    selected_source: List[str] = []


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/upload")
async def upload_document(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        try:
            content = await file.read()
            text_content = content.decode('utf-8')

            result = ingest_document(text_content, file.filename)
            results.append({
                "filename": file.filename,
                "status": "success",
                "result": result
            })
        except Exception as e:
            results.append({
                results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e)
            })
            })
    
    return {"resuts": results}

@app.get("/documents")
def list_documents():
    try:
        scroll_result = client.scroll(
            collection_name="notebook_docs",
            limit=10000,
            with_payload=True,
            with_vectors=False
        )

        sources = set()

        for point in scroll_result[0]:
            if point.payload and "source" in point.payload:
                sources.add(point.payload["source"])

        return {"documents": sorted(list(sources))}
    
    except Exception as e:
        return {"documents": []}
    
@app.delete("/clear-chat")
def clear_chat():
    return {"status": "chat cleared"}

@app.delete("/clear-all")
def clear_all():
    try:
        client.delete_collection(collection_name="notebook_docs")
        client.create_collection(
            collection_name="notebook_docs",
            vectors_config={"size": 768, "distance": "Cosine"}
        )
        return {"status": "all data cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post("/app")
def ask(req: AskRequest):
    def ndjson_iter():
        for msg in answer_question_stream(
            req.question,
            chat_history=req.chat_history,
            selected_sources=req.selected_sources
        ):
            yield json.dumps(msg, ensure_ascii=False) + "\n"

    return StreamingResponse(
        ndjson_iter(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

