from .vector_store import client, COLLECTION
from .embeddings import embed_text
def retrieve(query, top_k=20):
    query_embedding = embed_text(query)[0]

    results = client.search(
        collection_name=COLLECTION,
        query_vector=query_embedding,
        limit=top_k
    )

    return [r.payload for r in results]

