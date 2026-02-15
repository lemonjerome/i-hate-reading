from .vector_store import client, COLLECTION
from .embeddings import embed_text

def retrieve(query, top_k=20):
    query_embedding = embed_text(query)[0]

    results = client.query_points(
        collection_name=COLLECTION,
        query=query_embedding,
        limit=top_k
    )

    return [point.payload for point in results.points]

