from .vector_store import client, COLLECTION
from .embeddings import embed_text
from qdrant_client.http.exceptions import UnexpectedResponse

def retrieve(query, top_k=20):
    query_embedding = embed_text(query)[0]

    try:
        results = client.query_points(
            collection_name=COLLECTION,
            query=query_embedding,
            limit=top_k
        )

        return [point.payload for point in results.points]
    except UnexpectedResponse as e:
        if "doesn't exist" in str(e) or "404" in str(e):
            return {"error": "Collection is empty. Please ingest documents first."}
        raise

