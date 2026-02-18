import os
import platform
import logging
import torch
from sentence_transformers import SentenceTransformer
from typing import List

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")

def _get_device() -> str:
    """
    Auto-detect the best available compute device.
    - macOS Apple Silicon → 'mps' (Metal Performance Shaders)
    - NVIDIA GPU          → 'cuda'
    - Fallback            → 'cpu'
    """
    # Check for NVIDIA CUDA GPU
    if torch.cuda.is_available():
        device = "cuda"
        logger.info(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
        return device
    
    # Check for Apple Silicon MPS
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        logger.info("Using Apple Silicon MPS (Metal) device")
        return device

    logger.info("No GPU detected, using CPU")
    return "cpu"

DEVICE = _get_device()
logger.info(f"Embedding device: {DEVICE}")

_model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)


def preload():
    """Ensure embedding model is loaded (already loaded at import time)."""
    logger.info(f"Embedding model ready: {EMBEDDING_MODEL} on {DEVICE}")


def embed_text(text: str | List[str]) -> List[List[float]]:
    """Embed a string or list of strings. Returns list of vectors."""
    if isinstance(text, str):
        text = [text]
    
    embeddings = _model.encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=False,
        device=DEVICE,
    )
    return embeddings.tolist()