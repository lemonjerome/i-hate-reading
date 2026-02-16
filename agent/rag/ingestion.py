from .chunking import chunk_document
from .embeddings import embed_text
from .vector_store import insert_chunks, create_collection

import uuid

def ingest_document(text, source_name):
    doc_id = str(uuid.uuid4())

    chunks = chunk_document(text, source_name)

    texts = [c["text"] for c in chunks]

    embeddings = embed_text(texts)

    create_collection(len(embeddings[0]))

    metadata = {
        "source": source_name,
        "doc_id": doc_id
    }

    insert_chunks(chunks, embeddings, metadata)

    return {"chunks_added": len(chunks), "doc_id": doc_id}