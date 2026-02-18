import os
import logging
import torch
from sentence_transformers import CrossEncoder
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-base")
ENABLE_RERANK = os.getenv("ENABLE_RERANK", "1") not in ("0", "false", "False")

def _get_device() -> str:
    """
    Auto-detect the best available compute device.
    - NVIDIA GPU          → 'cuda'
    - Apple Silicon MPS   → 'mps' (if supported by model)
    - Fallback            → 'cpu'
    """
    if torch.cuda.is_available():
        logger.info(f"Reranker using CUDA: {torch.cuda.get_device_name(0)}")
        return "cuda"
    
    # CrossEncoder MPS support can be unstable, test before enabling
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        try:
            # Quick test to verify MPS works with CrossEncoder
            test_tensor = torch.tensor([1.0], device="mps")
            _ = test_tensor + 1
            logger.info("Reranker using Apple Silicon MPS (Metal)")
            return "mps"
        except Exception:
            logger.info("MPS available but unstable for CrossEncoder, falling back to CPU")
            return "cpu"

    logger.info("Reranker using CPU")
    return "cpu"

DEVICE = _get_device()

_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANK_MODEL, device=DEVICE)
    return _reranker


def rerank(
    query: str,
    hits: List[Dict[str, Any]],
    top_n: int = 8,
) -> List[Dict[str, Any]]:
    """Rerank hits using cross-encoder. Falls back to original order if disabled."""
    if not ENABLE_RERANK or not hits:
        return hits[:top_n]

    reranker = _get_reranker()

    pairs = [(query, h.get("text", "")[:512]) for h in hits]

    scores = reranker.predict(
        pairs,
        show_progress_bar=False,
    )

    for h, s in zip(hits, scores):
        h["rerank_score"] = float(s)

    ranked = sorted(hits, key=lambda x: x.get("rerank_score", 0), reverse=True)
    return ranked[:top_n]