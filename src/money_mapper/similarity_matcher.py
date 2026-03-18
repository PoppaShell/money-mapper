"""Similarity matching for merchant categorization using sentence transformers.

This module provides similarity-based merchant matching as Stage 3b of the ML pipeline.
Uses pre-computed sentence transformer embeddings for high-accuracy categorization.
"""

from typing import Any

import numpy as np


def load_merchant_embeddings(vectors_file: str) -> tuple[dict[str, Any], np.ndarray]:
    """
    Load pre-computed merchant embeddings and metadata.

    Args:
        vectors_file: Path to public_vectors.npy

    Returns:
        Tuple of (merchants_dict, embeddings_array)
    """
    try:
        data = np.load(vectors_file, allow_pickle=True).item()
        return data.get("merchants", {}), data.get("embeddings", np.array([]))
    except Exception:
        return {}, np.array([])


def embed_text(text: str, model: Any) -> np.ndarray:
    """
    Generate embedding for text using sentence-transformers.

    Args:
        text: Text to embed
        model: SentenceTransformer model

    Returns:
        Embedding array
    """
    try:
        embedding = model.encode(text, convert_to_numpy=True)
        return np.asarray(embedding)
    except Exception:
        return np.array([])


def calculate_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embeddings.

    Args:
        embedding1: First embedding
        embedding2: Second embedding

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if len(embedding1) == 0 or len(embedding2) == 0:
        return 0.0

    try:
        from sklearn.metrics.pairwise import cosine_similarity

        similarity = cosine_similarity([embedding1], [embedding2])[0][0]
        return float(similarity)
    except Exception:
        return 0.0


def find_similar_merchant(
    merchant_name: str,
    known_merchants: dict[str, Any],
    embeddings: np.ndarray,
    threshold: float = 0.85,
    model: Any = None,
    debug: bool = False,
) -> dict[str, Any] | None:
    """
    Find similar merchant in known database using embeddings.

    Args:
        merchant_name: Merchant name to search for
        known_merchants: Dict of {merchant_id: merchant_info}
        embeddings: Pre-computed embeddings array
        threshold: Similarity threshold (default 0.85)
        model: SentenceTransformer model
        debug: Enable debug output

    Returns:
        Best match dict with category/subcategory, or None if below threshold
    """
    if model is None or len(embeddings) == 0 or len(known_merchants) == 0:
        return None

    # Embed search merchant
    query_embedding = embed_text(merchant_name, model)
    if len(query_embedding) == 0:
        return None

    # Find best match
    best_score = 0.0
    best_match = None

    for idx, (merchant_id, merchant_info) in enumerate(known_merchants.items()):
        if idx >= len(embeddings):
            break

        score = calculate_similarity(query_embedding, embeddings[idx])
        if score > best_score:
            best_score = score
            best_match = merchant_info

    if best_score >= threshold:
        if debug:
            print(f"    Similarity match: {best_score:.3f}")
        return best_match

    return None
