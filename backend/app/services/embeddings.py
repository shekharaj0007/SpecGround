"""Local hashed embeddings — no OpenAI key required.

Anthropic does not offer embeddings. Spec lookup still works because
retrieval is hybrid: these vectors + keyword overlap + exact clause match.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.config import settings

_TOKEN = re.compile(r"[a-z0-9.§]+")


def _hash_embed(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    tokens = _TOKEN.findall((text or "").lower().replace("\x00", "")[:12000])
    grams = list(tokens)
    grams.extend(f"{a}_{b}" for a, b in zip(tokens, tokens[1:]))
    for gram in grams:
        digest = hashlib.md5(gram.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def embedding_backend() -> str:
    """Embedder in use.

    A missing OPENAI_API_KEY selects this hasher. The build does not download
    a model and does not call the embeddings API, so retrieval stays offline.
    """
    return "local-hash"


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    del batch_size
    if not (settings.openai_api_key or "").strip():
        return [_hash_embed(t, settings.embedding_dim) for t in texts]
    # A key does not switch vector spaces: cosine search assumes one embedder.
    return [_hash_embed(t, settings.embedding_dim) for t in texts]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
