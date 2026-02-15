from .chunking import chunk_document
from .embeddings import embed_text
from .vector_store import insert_chunks, create_collection

def ingest_document(text, source_name):
    chunks = chunk_document(text, source_name)

    embeddings = embed_text(chunks)

    create_collection(len(embeddings[0]))

    metadata = {
        "source": source_name
    }

    insert_chunks(chunks, embeddings, metadata)

    return {"chunks_added": len(chunks)}