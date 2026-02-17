import os
from typing import List, Dict, Any, Optional

from sentence_transformers import CrossEncoder

_RERANKER: Optional[CrossEncoder] = None

def _get_reranker() -> CrossEncoder:
    global _RERANKER
    if _RERANKER is None:
        model_name = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-base")
        _RERANKER = CrossEncoder(model_name)
    return _RERANKER

def rerank(question: str, hits: List[Dict[str, Any]], top_n:int = 12) -> List[Dict[str, Any]]:
    if not hits:
        return []
    
    reranker = _get_reranker()

    pairs = [[question, h.get("text", "")] for h in hits]

    if not hits:
        return []
    
    reranker = _get_reranker()
    pairs = [[question, h.get("text", "")] for h in hits]
    scores = reranker.predict(pairs)

    out = []
    for h, s in zip(hits, scores):
        hh = dict(h)
        hh["rerank_score"] = float(s)
        out.append(hh)

    out.sort(key=lambda x: x.get("rerank_score", float("-inf")), reverse=True)

    return out[:top_n]