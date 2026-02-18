from .vector_store import client, COLLECTION
from .embeddings import embed_text
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Filter, FieldCondition, MatchAny

def retrieve(query, top_k=20, filter_sources=None):
    query_embedding = embed_text(query)[0]

    query_filter = None
    if filter_sources and len(filter_sources) > 0:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="source",
                    match=MatchAny(any=filter_sources)
                )
            ]
        )

    try:
        results = client.query_points(
            collection_name=COLLECTION,
            query=query_embedding,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
            query_filter=query_filter
        )

        hits = []

        for point in results.points:
            hits.append(
                {
                    "id": str(point.id),
                    "score": float(point.score) if point.score is not None else None,
                    **(point.payload or {}),
                }
            )

        return hits
    except UnexpectedResponse as e:
        if "doesn't exist" in str(e) or "404" in str(e):
            return {"error": "Collection is empty. Please ingest documents first."}
        raise

