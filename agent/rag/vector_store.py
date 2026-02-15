from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

client = QdrantClient(url="http://qdrant:6333")

COLLECTION = "notebook_docs"

def create_collection(vector_size):
    collections = client.get_collectopns().collections
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

    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        points.append(
            PointStruct(
                id=i,
                vector=emb,
                payload={
                    "text": chunk,
                    **metadata
                }
            )
        )
    
    client.upsert(collection_name=COLLECTION, points=points)