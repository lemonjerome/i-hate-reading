from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-base-en-v1.5")

def embed_text(texts):
    if isinstance(texts, str):
        texts = [texts]
    return model.encode(texts, normalize_embeddinngs=True,).tolist()