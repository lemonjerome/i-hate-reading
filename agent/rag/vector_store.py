from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

import os
import uuid

QDRANT_URL = os.getenv("QDRANT_HOST", "http://qdrant:6333")

client = QdrantClient(url=QDRANT_URL)

COLLECTION = "notebook_docs"

def create_collection(vector_size):
    collections = client.get_collections().collections
    if COLLECTION not in [c.name for c in collections]:
        client.create_collection(
            collection_name = COLLECTION,
            vectors_config = VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )

def insert_chunks(chunks, embeddings, metadata):
    points = []

    for (chunk, emb) in zip(chunks, embeddings):
        payload = {
            "text": chunk["text"],
            "chunk_index": chunk.get("chunk_index"),
            **metadata,
        }

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload=payload
            )
        )
    
    client.upsert(collection_name=COLLECTION, points=points)